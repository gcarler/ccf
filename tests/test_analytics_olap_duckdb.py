"""Tests for M3: Embedded DuckDB OLAP Engine for BI and Dashboards.

Covers:
- DuckDBAnalyticsService unit tests (growth, attendance, financial summary).
- Sub-50ms execution performance validation.
- SQLite / in-memory ingestion fallback.
- REST API endpoints:
  * GET /api/analytics/olap/growth
  * GET /api/analytics/olap/attendance-trends
  * GET /api/analytics/olap/financial-summary
- Sede multi-tenant isolation and role permission enforcement (401/403/200).
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest

from backend import models
from backend.services.duckdb_engine import DuckDBAnalyticsService
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def olap_client(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="olap_admin@test.com")
    headers = _auth_headers(client, email="olap_admin@test.com", password="testpass123")
    return {"c": client, "h": headers, "admin": admin}


@pytest.fixture
def populated_olap_data(db_session):
    """Seed multi-sede, multi-year relational data for OLAP queries."""
    # Sedes
    s1 = models.Sede(
        id=uuid.uuid4(),
        nombre="Sede Central",
        ciudad="Bogotá",
        es_activa=True,
        created_at=dt.datetime(2022, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc),
    )
    s2 = models.Sede(
        id=uuid.uuid4(),
        nombre="Sede Poblado",
        ciudad="Medellín",
        es_activa=True,
        created_at=dt.datetime(2023, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc),
    )
    db_session.add_all([s1, s2])
    db_session.flush()

    # Personas
    # Sede 1
    p1 = models.Persona(
        id=uuid.uuid4(),
        sede_id=s1.id,
        first_name="Carlos",
        last_name="Gomez",
        email="carlos@test.com",
        phone="3001234567",
        church_role="Lider",
        is_baptized=True,
        estado_vital="ACTIVO",
        birthday=dt.date(1990, 5, 15),  # 34 -> Jóvenes / Adultos
        created_at=dt.datetime(2023, 1, 15, 10, 0, 0, tzinfo=dt.timezone.utc),
    )
    p2 = models.Persona(
        id=uuid.uuid4(),
        sede_id=s1.id,
        first_name="Ana",
        last_name="Ruiz",
        email="ana@test.com",
        phone="3007654321",
        church_role="Miembro",
        is_baptized=True,
        estado_vital="ACTIVO",
        birthday=dt.date(2015, 3, 10),  # Niños
        created_at=dt.datetime(2023, 3, 20, 10, 0, 0, tzinfo=dt.timezone.utc),
    )
    p3 = models.Persona(
        id=uuid.uuid4(),
        sede_id=s1.id,
        first_name="David",
        last_name="Castro",
        email="david@test.com",
        church_role="Servidor",
        is_baptized=False,
        estado_vital="ACTIVO",
        birthday=dt.date(1955, 8, 25),  # 60+ Adultos Mayores
        created_at=dt.datetime(2024, 2, 10, 10, 0, 0, tzinfo=dt.timezone.utc),
    )

    # Sede 2
    p4 = models.Persona(
        id=uuid.uuid4(),
        sede_id=s2.id,
        first_name="Elena",
        last_name="Morales",
        email="elena@test.com",
        church_role="Miembro",
        is_baptized=True,
        estado_vital="ACTIVO",
        birthday=dt.date(2011, 11, 2),  # Adolescentes (15 in 2026)
        created_at=dt.datetime(2023, 6, 1, 10, 0, 0, tzinfo=dt.timezone.utc),
    )
    p5 = models.Persona(
        id=uuid.uuid4(),
        sede_id=s2.id,
        first_name="Lucas",
        last_name="Vargas",
        email="lucas@test.com",
        church_role="Nuevo",
        is_baptized=False,
        estado_vital="INACTIVO",
        birthday=dt.date(1978, 1, 30),  # Adultos
        created_at=dt.datetime(2024, 5, 12, 10, 0, 0, tzinfo=dt.timezone.utc),
    )

    db_session.add_all([p1, p2, p3, p4, p5])
    db_session.flush()

    # Events & Attendances
    e1 = models.CrmEvent(
        id=uuid.uuid4(),
        sede_id=s1.id,
        name="Servicio Dominical Central",
        event_type="DOMINICAL",
        event_date=dt.datetime(2023, 3, 26, 10, 0, 0, tzinfo=dt.timezone.utc),
        status="SCHEDULED",
    )
    e2 = models.CrmEvent(
        id=uuid.uuid4(),
        sede_id=s1.id,
        name="Noche de Oracion",
        event_type="ORACION",
        event_date=dt.datetime(2023, 4, 5, 19, 0, 0, tzinfo=dt.timezone.utc),
        status="SCHEDULED",
    )
    e3 = models.CrmEvent(
        id=uuid.uuid4(),
        sede_id=s2.id,
        name="Servicio Jovenes Medellín",
        event_type="JOVENES",
        event_date=dt.datetime(2024, 6, 15, 18, 0, 0, tzinfo=dt.timezone.utc),
        status="SCHEDULED",
    )
    db_session.add_all([e1, e2, e3])
    db_session.flush()

    att1 = models.EventAttendance(id=uuid.uuid4(), event_id=e1.id, persona_id=p1.id, session_date=dt.date(2023, 3, 26))
    att2 = models.EventAttendance(id=uuid.uuid4(), event_id=e1.id, persona_id=p2.id, session_date=dt.date(2023, 3, 26))
    att3 = models.EventAttendance(id=uuid.uuid4(), event_id=e1.id, persona_id=p3.id, session_date=dt.date(2023, 3, 26))
    att4 = models.EventAttendance(id=uuid.uuid4(), event_id=e2.id, persona_id=p1.id, session_date=dt.date(2023, 4, 5))
    att5 = models.EventAttendance(id=uuid.uuid4(), event_id=e3.id, persona_id=p4.id, session_date=dt.date(2024, 6, 15))
    db_session.add_all([att1, att2, att3, att4, att5])

    # Donations (Multi-year income)
    d1 = models.Donation(
        id=uuid.uuid4(),
        persona_id=p1.id,
        sede_id=s1.id,
        amount=1000000.0,
        currency="COP",
        donation_type="Diezmo",
        status="completed",
        donation_date=dt.date(2023, 3, 1),
        created_at=dt.datetime(2023, 3, 1, 12, 0, 0, tzinfo=dt.timezone.utc),
    )
    d2 = models.Donation(
        id=uuid.uuid4(),
        persona_id=p2.id,
        sede_id=s1.id,
        amount=300000.0,
        currency="COP",
        donation_type="Ofrenda",
        status="completed",
        donation_date=dt.date(2023, 6, 15),
        created_at=dt.datetime(2023, 6, 15, 12, 0, 0, tzinfo=dt.timezone.utc),
    )
    d3 = models.Donation(
        id=uuid.uuid4(),
        persona_id=p1.id,
        sede_id=s1.id,
        amount=1500000.0,
        currency="COP",
        donation_type="Diezmo",
        status="completed",
        donation_date=dt.date(2024, 2, 20),
        created_at=dt.datetime(2024, 2, 20, 12, 0, 0, tzinfo=dt.timezone.utc),
    )
    d4 = models.Donation(
        id=uuid.uuid4(),
        persona_id=p4.id,
        sede_id=s2.id,
        amount=800000.0,
        currency="COP",
        donation_type="Pro-Templo",
        status="completed",
        donation_date=dt.date(2024, 7, 10),
        created_at=dt.datetime(2024, 7, 10, 12, 0, 0, tzinfo=dt.timezone.utc),
    )
    d5 = models.Donation(
        id=uuid.uuid4(),
        persona_id=p3.id,
        sede_id=s1.id,
        amount=2000000.0,
        currency="COP",
        donation_type="Diezmo",
        status="completed",
        donation_date=dt.date(2025, 1, 15),
        created_at=dt.datetime(2025, 1, 15, 12, 0, 0, tzinfo=dt.timezone.utc),
    )
    db_session.add_all([d1, d2, d3, d4, d5])

    # Expenses (Multi-year)
    r1 = models.ExpenseReport(
        id=uuid.uuid4(),
        sede_id=s1.id,
        employee_id=p1.id,
        report_number="EXP-2023-01",
        total_amount=500000.0,
        currency="COP",
        status="approved",
        created_at=dt.datetime(2023, 4, 1, 10, 0, 0, tzinfo=dt.timezone.utc),
    )
    r2 = models.ExpenseReport(
        id=uuid.uuid4(),
        sede_id=s1.id,
        employee_id=p1.id,
        report_number="EXP-2024-01",
        total_amount=700000.0,
        currency="COP",
        status="approved",
        created_at=dt.datetime(2024, 3, 1, 10, 0, 0, tzinfo=dt.timezone.utc),
    )
    r3 = models.ExpenseReport(
        id=uuid.uuid4(),
        sede_id=s2.id,
        employee_id=p4.id,
        report_number="EXP-2024-02",
        total_amount=400000.0,
        currency="COP",
        status="approved",
        created_at=dt.datetime(2024, 8, 1, 10, 0, 0, tzinfo=dt.timezone.utc),
    )
    db_session.add_all([r1, r2, r3])
    db_session.flush()

    ei1 = models.ExpenseItem(
        id=uuid.uuid4(),
        expense_report_id=r1.id,
        expense_date=dt.date(2023, 3, 20),
        category="Operations",
        description="Suministros y papeleria",
        amount=500000.0,
        created_at=dt.datetime(2023, 3, 20, 10, 0, 0, tzinfo=dt.timezone.utc),
    )
    ei2 = models.ExpenseItem(
        id=uuid.uuid4(),
        expense_report_id=r2.id,
        expense_date=dt.date(2024, 2, 28),
        category="Facilities",
        description="Mantenimiento de sonido",
        amount=700000.0,
        created_at=dt.datetime(2024, 2, 28, 10, 0, 0, tzinfo=dt.timezone.utc),
    )
    ei3 = models.ExpenseItem(
        id=uuid.uuid4(),
        expense_report_id=r3.id,
        expense_date=dt.date(2024, 7, 25),
        category="Ministry",
        description="Materiales para jovenes",
        amount=400000.0,
        created_at=dt.datetime(2024, 7, 25, 10, 0, 0, tzinfo=dt.timezone.utc),
    )
    db_session.add_all([ei1, ei2, ei3])
    db_session.commit()

    return {"s1": s1, "s2": s2, "p1": p1, "p4": p4}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Direct DuckDB Engine Service Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDuckDBEngineService:
    def test_empty_database_analytics_graceful(self, db_session):
        service = DuckDBAnalyticsService()
        
        growth = service.get_church_growth_metrics(db_session=db_session)
        assert growth["source"] == "duckdb/in-memory-olap"
        assert growth["execution_time_ms"] < 50.0
        assert growth["summary"]["total_members"] == 0
        assert growth["trends"] == []

        att = service.get_attendance_trends(db_session=db_session)
        assert att["source"] == "duckdb/in-memory-olap"
        assert att["execution_time_ms"] < 50.0
        assert att["summary"]["total_attendances"] == 0
        assert att["by_age_group"] == []

        fin = service.get_financial_summary(db_session=db_session)
        assert fin["source"] == "duckdb/in-memory-olap"
        assert fin["execution_time_ms"] < 50.0
        assert fin["kpis"]["total_income"] == 0.0

    def test_growth_metrics_calculation(self, db_session, populated_olap_data):
        service = DuckDBAnalyticsService()
        s1 = populated_olap_data["s1"]

        # All sedes
        res_all = service.get_church_growth_metrics(db_session=db_session)
        assert res_all["source"] == "duckdb/in-memory-olap"
        assert res_all["execution_time_ms"] < 50.0  # Sub-50ms constraint
        assert res_all["summary"]["total_members"] == 5
        assert res_all["summary"]["active_members"] == 4
        assert res_all["summary"]["baptized_members"] == 3
        assert res_all["summary"]["retention_rate_pct"] == 80.0
        assert len(res_all["by_sede"]) == 2

        # Filtered by single sede s1
        res_s1 = service.get_church_growth_metrics(sede_id=str(s1.id), db_session=db_session)
        assert res_s1["summary"]["total_members"] == 3
        assert res_s1["summary"]["active_members"] == 3
        assert res_s1["summary"]["retention_rate_pct"] == 100.0

    def test_attendance_trends_calculation(self, db_session, populated_olap_data):
        service = DuckDBAnalyticsService()

        att = service.get_attendance_trends(db_session=db_session)
        assert att["source"] == "duckdb/in-memory-olap"
        assert att["execution_time_ms"] < 50.0  # Sub-50ms constraint
        assert att["summary"]["total_attendances"] == 5
        assert att["summary"]["unique_attendees"] == 4
        assert att["summary"]["total_services"] == 3
        assert att["summary"]["peak_attendance"] == 3
        assert att["summary"]["peak_event_name"] == "Servicio Dominical Central"

        # Check age group breakdown
        age_groups = {row["age_group"]: row["count"] for row in att["by_age_group"]}
        assert "0-12 (Niños)" in age_groups
        assert "13-17 (Adolescentes)" in age_groups
        assert "60+ (Adultos Mayores)" in age_groups

        # Check service type breakdown
        service_types = {row["event_type"]: row["total_attendance"] for row in att["by_service_type"]}
        assert service_types.get("DOMINICAL") == 3
        assert service_types.get("ORACION") == 1
        assert service_types.get("JOVENES") == 1

    def test_financial_summary_calculation(self, db_session, populated_olap_data):
        service = DuckDBAnalyticsService()

        fin = service.get_financial_summary(db_session=db_session)
        assert fin["source"] == "duckdb/in-memory-olap"
        assert fin["execution_time_ms"] < 50.0  # Sub-50ms constraint

        # Total income: 1.0M + 0.3M + 1.5M + 0.8M + 2.0M = 5.6M
        assert fin["kpis"]["total_income"] == 5600000.0
        # Total expenses: 0.5M + 0.7M + 0.4M = 1.6M
        assert fin["kpis"]["total_expenses"] == 1600000.0
        assert fin["kpis"]["net_balance"] == 4000000.0
        assert fin["kpis"]["operating_margin_pct"] == round((4000000.0 / 5600000.0) * 100, 2)
        assert fin["kpis"]["total_donations_count"] == 5

        # Check multi-year trend contains years 2023, 2024, 2025
        years = [row["year"] for row in fin["multi_year_trend"]]
        assert 2023 in years
        assert 2024 in years
        assert 2025 in years

        # Check categories breakdown
        inc_cats = {row["donation_type"]: row["amount"] for row in fin["income_by_category"]}
        assert inc_cats.get("Diezmo") == 4500000.0
        assert inc_cats.get("Ofrenda") == 300000.0
        assert inc_cats.get("Pro-Templo") == 800000.0

        exp_cats = {row["category"]: row["amount"] for row in fin["expenses_by_category"]}
        assert exp_cats.get("Operations") == 500000.0
        assert exp_cats.get("Facilities") == 700000.0
        assert exp_cats.get("Ministry") == 400000.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. REST API Endpoints Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOlapRestApi:
    def test_unauthenticated_requests_rejected(self, client):
        res_growth = client.get("/api/analytics/olap/growth")
        assert res_growth.status_code in (401, 403)

        res_att = client.get("/api/analytics/olap/attendance-trends")
        assert res_att.status_code in (401, 403)

        res_fin = client.get("/api/analytics/olap/financial-summary")
        assert res_fin.status_code in (401, 403)

    def test_get_growth_endpoint(self, olap_client, populated_olap_data):
        c, h = olap_client["c"], olap_client["h"]

        res = c.get("/api/analytics/olap/growth?group_by=month", headers=h)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["source"] == "duckdb/in-memory-olap"
        # HTTP endpoint threshold: 200ms (includes TestClient + middleware overhead).
        # DuckDB engine 50ms SLA is enforced in TestDuckDBEngineService.
        assert data["execution_time_ms"] < 200.0
        assert data["summary"]["total_members"] >= 5
        assert isinstance(data["trends"], list)
        assert isinstance(data["by_sede"], list)

    def test_get_attendance_trends_endpoint(self, olap_client, populated_olap_data):
        c, h = olap_client["c"], olap_client["h"]

        res = c.get("/api/analytics/olap/attendance-trends", headers=h)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["source"] == "duckdb/in-memory-olap"
        assert data["execution_time_ms"] < 200.0  # HTTP endpoint threshold (TestClient overhead)
        assert data["summary"]["total_attendances"] >= 5
        assert len(data["by_age_group"]) >= 1
        assert len(data["by_service_type"]) >= 1

    def test_get_financial_summary_endpoint(self, olap_client, populated_olap_data):
        c, h = olap_client["c"], olap_client["h"]

        res = c.get("/api/analytics/olap/financial-summary?start_year=2023&end_year=2025", headers=h)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["source"] == "duckdb/in-memory-olap"
        assert data["execution_time_ms"] < 200.0  # HTTP endpoint threshold (TestClient overhead)
        assert data["kpis"]["total_income"] >= 5600000.0
        assert data["kpis"]["total_expenses"] >= 1600000.0
        assert len(data["multi_year_trend"]) >= 2
        assert len(data["income_by_category"]) >= 2
        assert len(data["expenses_by_category"]) >= 2

    def test_sede_filtering_query_params(self, olap_client, populated_olap_data):
        c, h = olap_client["c"], olap_client["h"]
        s1 = populated_olap_data["s1"]

        res = c.get(f"/api/analytics/olap/growth?sede_id={s1.id}", headers=h)
        assert res.status_code == 200
        data = res.json()
        assert data["filters"]["sede_id"] == str(s1.id)
        assert data["summary"]["total_members"] == 3
