"""Empirical Adversarial Stress Suite for Backend & Security Architecture.

Stress-tests:
1. FastMCP 2.0 Gateway: RBAC enforcement (401/403), telemetry persistence, domain tool execution.
2. Secure Pastoral RAG: Multi-tenant RLS isolation between Sede A and Sede B, alpha score fusion.
3. Embedded DuckDB OLAP: Sub-50ms query benchmarks under 10,000+ records, multi-year math, zero-division safety on empty state.
"""

from __future__ import annotations

import datetime as dt
import time
import uuid

import duckdb
import pytest

from backend import models
from backend.core.pgvector_compat import generate_text_embedding
from backend.models_agents import ToolExecutionLog
from backend.models_knowledge_base import KnowledgeBaseArticle
from backend.models_sermones import Sermon
from backend.models_wiki import WikiPage
from backend.services.duckdb_engine import DuckDBAnalyticsService
from backend.services.rag_service import PastoralRAGService
from tests.conftest import TestingSessionLocal, auth_headers, seed_admin, seed_user_with_role


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def adversarial_env(db_session, client, monkeypatch):
    import backend.core.database as core_db
    import backend.mcp_crm as m_crm
    import backend.mcp_cms as m_cms
    import backend.mcp_academy as m_acad
    import backend.mcp_agenda as m_ag
    import backend.mcp_evangelism as m_ev
    import backend.mcp_governance as m_gov
    import backend.api.mcp_gateway as m_gw

    monkeypatch.setattr(core_db, "SessionLocal", TestingSessionLocal)
    for m in (m_crm, m_cms, m_acad, m_ag, m_ev, m_gov, m_gw):
        if hasattr(m, "SessionLocal"):
            monkeypatch.setattr(m, "SessionLocal", TestingSessionLocal)

    # 1. Create Sede Bogotá and Sede Cali
    sede_bogota = models.Sede(
        id=uuid.uuid4(),
        nombre="Sede Bogotá Central",
        ciudad="Bogotá",
        es_activa=True,
    )
    sede_cali = models.Sede(
        id=uuid.uuid4(),
        nombre="Sede Cali Norte",
        ciudad="Cali",
        es_activa=True,
    )
    db_session.add_all([sede_bogota, sede_cali])
    db_session.commit()

    # 2. Users:
    # Admin (Global)
    admin_user, admin_persona, _ = seed_admin(db_session, email="adv-admin@ccf.test")
    admin_hdrs = auth_headers(client, email="adv-admin@ccf.test", password="testpass123")

    # Member Sede Bogotá (No mcp:execute permission)
    member_bogota, member_persona_bogota, _ = seed_user_with_role(
        db_session,
        role_name="miembro",
        email="member-bogota@ccf.test",
        sede_id=sede_bogota.id,
        permisos={},
    )
    member_bogota_hdrs = auth_headers(client, email="member-bogota@ccf.test", password="testpass123")

    # Member Sede Cali (No mcp:execute permission)
    member_cali, member_persona_cali, _ = seed_user_with_role(
        db_session,
        role_name="miembro",
        email="member-cali@ccf.test",
        sede_id=sede_cali.id,
        permisos={},
    )
    member_cali_hdrs = auth_headers(client, email="member-cali@ccf.test", password="testpass123")

    # Pastor Sede Bogotá (Has mcp:execute + crm/rag access)
    pastor_bogota, pastor_persona_bogota, _ = seed_user_with_role(
        db_session,
        role_name="pastor",
        email="pastor-bogota@ccf.test",
        sede_id=sede_bogota.id,
        permisos={"mcp:execute": "allow", "crm:read": "allow", "crm:write": "allow"},
    )
    pastor_bogota_hdrs = auth_headers(client, email="pastor-bogota@ccf.test", password="testpass123")

    # Pastor Sede Cali (Has mcp:execute + crm/rag access)
    pastor_cali, pastor_persona_cali, _ = seed_user_with_role(
        db_session,
        role_name="pastor",
        email="pastor-cali@ccf.test",
        sede_id=sede_cali.id,
        permisos={"mcp:execute": "allow", "crm:read": "allow", "crm:write": "allow"},
    )
    pastor_cali_hdrs = auth_headers(client, email="pastor-cali@ccf.test", password="testpass123")

    # Site for CMS
    site = models.CmsSite(
        id=uuid.uuid4(),
        site_key="ccf-adv",
        name="CCF Adversarial",
        is_active=True,
        sede_id=sede_bogota.id,
    )
    db_session.add(site)
    db_session.commit()

    return {
        "client": client,
        "db": db_session,
        "sede_bogota": sede_bogota,
        "sede_cali": sede_cali,
        "admin": admin_user,
        "admin_persona": admin_persona,
        "admin_headers": admin_hdrs,
        "member_bogota": member_bogota,
        "member_bogota_headers": member_bogota_hdrs,
        "member_cali": member_cali,
        "member_cali_headers": member_cali_hdrs,
        "pastor_bogota": pastor_bogota,
        "pastor_bogota_headers": pastor_bogota_hdrs,
        "pastor_cali": pastor_cali,
        "pastor_cali_headers": pastor_cali_hdrs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. FASTMCP 2.0 GATEWAY & RBAC ADVERSARIAL TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestAdversarialFastMCPGateway:
    def test_unauthenticated_call_rejected_with_401(self, adversarial_env):
        client = adversarial_env["client"]
        res = client.post(
            "/api/mcp/crm/tools/call",
            json={"name": "list_crm_events", "arguments": {}},
        )
        assert res.status_code == 401

    def test_call_without_mcp_execute_rejected_with_403(self, adversarial_env):
        client = adversarial_env["client"]
        # Member from Bogotá lacks mcp:execute
        res = client.post(
            "/api/mcp/crm/tools/call",
            headers=adversarial_env["member_bogota_headers"],
            json={"name": "list_crm_events", "arguments": {}},
        )
        assert res.status_code == 403
        assert "mcp:execute" in res.json()["detail"]

        # Listing tools also requires mcp:execute
        res_list = client.get(
            "/api/mcp/tools",
            headers=adversarial_env["member_cali_headers"],
        )
        assert res_list.status_code == 403
        assert "mcp:execute" in res_list.json()["detail"]

    def test_authorized_call_persists_telemetry_and_latency(self, adversarial_env):
        client = adversarial_env["client"]
        db = adversarial_env["db"]
        req_id = f"adv-telemetry-{uuid.uuid4().hex[:8]}"

        res = client.post(
            "/api/mcp/crm/tools/call",
            headers={
                **adversarial_env["pastor_bogota_headers"],
                "X-Request-ID": req_id,
                "X-Sede-ID": str(adversarial_env["sede_bogota"].id),
            },
            json={
                "name": "list_crm_events",
                "arguments": {"limit": 3},
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["server"] == "crm"
        assert data["tool"] == "list_crm_events"
        assert data["request_id"] == req_id
        assert data["latency_ms"] >= 0

        # Query tool_execution_logs to verify strict telemetry tracking
        telemetry = (
            db.query(ToolExecutionLog)
            .filter(ToolExecutionLog.request_id == req_id)
            .first()
        )
        assert telemetry is not None
        assert telemetry.tool_name == "list_crm_events"
        assert telemetry.status == "success"
        assert telemetry.sede_id == adversarial_env["sede_bogota"].id
        assert telemetry.execution_time_ms >= 0

    def test_nonexistent_server_and_tool_returns_404(self, adversarial_env):
        client = adversarial_env["client"]
        # Non-existent server
        res_server = client.post(
            "/api/mcp/nonexistent_server/tools/call",
            headers=adversarial_env["admin_headers"],
            json={"name": "any_tool", "arguments": {}},
        )
        assert res_server.status_code == 404

        # Non-existent tool in valid server
        res_tool = client.post(
            "/api/mcp/crm/tools/call",
            headers=adversarial_env["admin_headers"],
            json={"name": "completely_bogus_tool_name_xyz", "arguments": {}},
        )
        assert res_tool.status_code == 404

    def test_universal_router_resolves_across_domain_servers(self, adversarial_env):
        client = adversarial_env["client"]

        # Call CRM tool via universal router
        res_crm = client.post(
            "/api/mcp/tools/call",
            headers=adversarial_env["admin_headers"],
            json={"name": "list_crm_events", "arguments": {"limit": 1}},
        )
        assert res_crm.status_code == 200
        assert res_crm.json()["server"] == "crm"

        # Call CMS tool via universal router
        res_cms = client.post(
            "/api/mcp/tools/call",
            headers=adversarial_env["admin_headers"],
            json={"name": "list_cms_posts", "arguments": {"limit": 1}},
        )
        assert res_cms.status_code == 200
        assert res_cms.json()["server"] == "cms"

        # Call Governance tool via universal router
        res_gov = client.post(
            "/api/mcp/tools/call",
            headers=adversarial_env["admin_headers"],
            json={"name": "get_active_policies", "arguments": {}},
        )
        assert res_gov.status_code == 200
        assert res_gov.json()["server"] == "governance"


# ─────────────────────────────────────────────────────────────────────────────
# 2. PASTORAL RAG MULTI-TENANT ISOLATION & HYBRID SEARCH ADVERSARIAL TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestAdversarialPastoralRAG:
    def test_multi_tenant_rls_isolation_between_sedes(self, adversarial_env):
        """Mathematically verifies that User in Sede A CANNOT retrieve private documents from Sede B."""
        db = adversarial_env["db"]
        sede_a = adversarial_env["sede_bogota"].id
        sede_b = adversarial_env["sede_cali"].id

        # 1. Seed private documents for Sede Bogotá
        sermon_a = Sermon(
            id=uuid.uuid4(),
            title="Sermon Exclusivo Bogotá: Avivamiento Andino",
            preacher="Pastor Bogotá",
            content="Este mensaje es solo para la congregación de Bogotá Central sobre avivamiento andino.",
            summary="Avivamiento Bogotá",
            sede_id=sede_a,
            is_published=True,
            is_active=True,
            embedding=generate_text_embedding("Sermon Exclusivo Bogotá: Avivamiento Andino"),
        )
        wiki_a = WikiPage(
            id=uuid.uuid4(),
            page_key="bogota-directorio-interno",
            title="Directorio Confidencial Bogotá",
            content="Información de contacto interno líderes Bogotá.",
            sede_id=sede_a,
            embedding=generate_text_embedding("Directorio Confidencial Bogotá"),
        )
        art_a = KnowledgeBaseArticle(
            id=uuid.uuid4(),
            title="Guía Operativa Sede Bogotá",
            content="Protocolos de apertura y cierre de la sede Bogotá.",
            sede_id=sede_a,
            is_active=True,
            embedding=generate_text_embedding("Guía Operativa Sede Bogotá"),
        )

        # 2. Seed private documents for Sede Cali
        sermon_b = Sermon(
            id=uuid.uuid4(),
            title="Sermon Exclusivo Cali: Rios de Gracia Valle",
            preacher="Pastor Cali",
            content="Este mensaje es exclusivo para la sede Cali sobre ríos de bendición en el Valle.",
            summary="Bendición Cali",
            sede_id=sede_b,
            is_published=True,
            is_active=True,
            embedding=generate_text_embedding("Sermon Exclusivo Cali: Rios de Gracia Valle"),
        )
        wiki_b = WikiPage(
            id=uuid.uuid4(),
            page_key="cali-directorio-interno",
            title="Directorio Confidencial Cali",
            content="Información de contacto interno líderes Cali.",
            sede_id=sede_b,
            embedding=generate_text_embedding("Directorio Confidencial Cali"),
        )
        art_b = KnowledgeBaseArticle(
            id=uuid.uuid4(),
            title="Guía Operativa Sede Cali",
            content="Protocolos de apertura y cierre de la sede Cali.",
            sede_id=sede_b,
            is_active=True,
            embedding=generate_text_embedding("Guía Operativa Sede Cali"),
        )

        # 3. Seed global document (sede_id=None)
        art_global = KnowledgeBaseArticle(
            id=uuid.uuid4(),
            title="Doctrina General de Fe CCF",
            content="Declaración de fe y teología común para todas las sedes de la iglesia CCF.",
            sede_id=None,
            is_active=True,
            embedding=generate_text_embedding("Doctrina General de Fe CCF"),
        )

        db.add_all([sermon_a, wiki_a, art_a, sermon_b, wiki_b, art_b, art_global])
        db.commit()

        # Instantiate RAG Services for Pastor Bogotá and Pastor Cali
        rag_service_bogota = PastoralRAGService(db=db, user_sede_id=sede_a, user_role="pastor")
        rag_service_cali = PastoralRAGService(db=db, user_sede_id=sede_b, user_role="pastor")

        # Query A: User Bogotá searches for "Cali" or "Valle"
        results_bogota = rag_service_bogota.search(query="Cali Rios de Gracia Valle Directorio", limit=10)
        bogota_result_ids = {r.id for r in results_bogota}

        # MUST NOT contain any Sede B items
        assert sermon_b.id not in bogota_result_ids, "LEAK DETECTED: Bogotá user retrieved Cali private sermon!"
        assert wiki_b.id not in bogota_result_ids, "LEAK DETECTED: Bogotá user retrieved Cali private wiki page!"
        assert art_b.id not in bogota_result_ids, "LEAK DETECTED: Bogotá user retrieved Cali private article!"

        # Query B: User Cali searches for "Bogotá" or "Andino"
        results_cali = rag_service_cali.search(query="Bogotá Avivamiento Andino Guía Operativa", limit=10)
        cali_result_ids = {r.id for r in results_cali}

        # MUST NOT contain any Sede A items
        assert sermon_a.id not in cali_result_ids, "LEAK DETECTED: Cali user retrieved Bogotá private sermon!"
        assert wiki_a.id not in cali_result_ids, "LEAK DETECTED: Cali user retrieved Bogotá private wiki page!"
        assert art_a.id not in cali_result_ids, "LEAK DETECTED: Cali user retrieved Bogotá private article!"

        # Global document must be retrievable by both
        res_bogota_global = rag_service_bogota.search(query="Doctrina General de Fe", limit=5)
        res_cali_global = rag_service_cali.search(query="Doctrina General de Fe", limit=5)
        assert any(r.id == art_global.id for r in res_bogota_global)
        assert any(r.id == art_global.id for r in res_cali_global)

    def test_hybrid_search_alpha_fusion_and_scoring(self, adversarial_env):
        """Verifies score fusion behavior across pure FTS (alpha=0.0), pure vector (alpha=1.0), and hybrid (0.5)."""
        db = adversarial_env["db"]
        rag_service = PastoralRAGService(db=db, user_sede_id=None, user_role="admin")

        art = KnowledgeBaseArticle(
            id=uuid.uuid4(),
            title="Mayordomía Cristiana y Finanzas Bíblicas",
            content="Principios de generosidad, administración responsable de recursos y ofrendas santas.",
            summary="Finanzas y mayordomía",
            sede_id=None,
            is_active=True,
            embedding=generate_text_embedding("Mayordomía Cristiana y Finanzas Bíblicas"),
        )
        db.add(art)
        db.commit()

        # 1. Pure FTS (alpha = 0.0)
        results_fts = rag_service.search(query="Mayordomía Cristiana", limit=5, alpha=0.0)
        assert len(results_fts) > 0
        assert results_fts[0].id == art.id
        assert results_fts[0].metadata["fts_score"] > 0.8

        # 2. Pure Vector (alpha = 1.0)
        results_vec = rag_service.search(query="Administración de dinero y recursos de la iglesia", limit=5, alpha=1.0)
        assert len(results_vec) > 0
        assert results_vec[0].metadata["vec_score"] > 0.5

        # 3. Hybrid (alpha = 0.5)
        results_hybrid = rag_service.search(query="Mayordomía Cristiana", limit=5, alpha=0.5)
        assert len(results_hybrid) > 0
        fused = results_hybrid[0].score
        fts = results_hybrid[0].metadata["fts_score"]
        vec = results_hybrid[0].metadata["vec_score"]
        expected_fused = round(0.5 * vec + 0.5 * fts, 4)
        assert abs(fused - expected_fused) < 0.01

    def test_extreme_and_adversarial_queries(self, adversarial_env):
        """Verifies safety against empty, giant, and SQL injection strings."""
        db = adversarial_env["db"]
        rag_service = PastoralRAGService(db=db, user_sede_id=None, user_role="admin")

        # Empty & whitespace query
        assert rag_service.search(query="", limit=10) == []
        assert rag_service.search(query="    \n\t   ", limit=10) == []

        # SQL Injection string
        sqli_results = rag_service.search(query="' OR 1=1; DROP TABLE sermones; --", limit=10)
        assert isinstance(sqli_results, list)

        # Huge query (10,000 chars)
        huge_query = "bendición gracia fe amor " * 2000
        huge_results = rag_service.search(query=huge_query, limit=10)
        assert isinstance(huge_results, list)


# ─────────────────────────────────────────────────────────────────────────────
# 3. EMBEDDED DUCKDB OLAP ENGINE STRESS & PERFORMANCE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestAdversarialDuckDBOLAP:
    def test_empty_dataset_zero_division_safety(self, adversarial_env):
        """Verifies OLAP engine produces clean 0.0 results on empty timeframes/empty tables without crashing."""
        olap = DuckDBAnalyticsService()
        empty_session = TestingSessionLocal()
        try:
            # Growth metrics on an out-of-range future window (0 records)
            growth = olap.get_church_growth_metrics(start_date="2099-01-01", end_date="2099-12-31", db_session=empty_session)
            assert growth["source"] == "duckdb/in-memory-olap"
            assert growth["summary"]["total_members"] == 0
            assert growth["summary"]["retention_rate_pct"] == 0.0
            assert growth["summary"]["overall_growth_rate_pct"] == 0.0
            assert growth["trends"] == []
            assert growth["by_sede"] == []

            # Attendance trends on empty time window
            attendance = olap.get_attendance_trends(start_date="2099-01-01", end_date="2099-12-31", db_session=empty_session)
            assert attendance["summary"]["total_attendances"] == 0
            assert attendance["summary"]["avg_attendance_per_service"] == 0.0
            assert attendance["by_age_group"] == []
            assert attendance["trends"] == []

            # Financial summary on empty year window
            fin = olap.get_financial_summary(start_year=2099, end_year=2099, db_session=empty_session)
            assert fin["kpis"]["total_income"] == 0.0
            assert fin["kpis"]["total_expenses"] == 0.0
            assert fin["kpis"]["operating_margin_pct"] == 0.0
            assert fin["multi_year_trend"] == []
            assert fin["income_by_category"] == []
        finally:
            empty_session.close()

    def test_multi_year_financial_aggregations_accuracy(self, adversarial_env):
        """Verifies multi-year trend KPIs, YoY growth, operating margin, and category CTE calculations."""
        db = adversarial_env["db"]
        sede_id = adversarial_env["sede_bogota"].id
        employee_id = adversarial_env["admin_persona"].id

        # Seed multi-year donations
        # 2023: 10,000,000
        # 2024: 15,000,000 (50% YoY growth)
        # 2025: 18,000,000 (20% YoY growth)
        d1 = models.Donation(
            id=uuid.uuid4(),
            sede_id=sede_id,
            amount=10000000.0,
            donation_type="Diezmo",
            status="completed",
            donation_date=dt.date(2023, 6, 1),
        )
        d2 = models.Donation(
            id=uuid.uuid4(),
            sede_id=sede_id,
            amount=15000000.0,
            donation_type="Diezmo",
            status="completed",
            donation_date=dt.date(2024, 6, 1),
        )
        d3 = models.Donation(
            id=uuid.uuid4(),
            sede_id=sede_id,
            amount=18000000.0,
            donation_type="Ofrenda",
            status="completed",
            donation_date=dt.date(2025, 6, 1),
        )

        # Seed multi-year expense reports with employee_id, report_number, and descriptions
        r1 = models.ExpenseReport(id=uuid.uuid4(), sede_id=sede_id, employee_id=employee_id, report_number="EXP-2023-01", status="approved")
        r2 = models.ExpenseReport(id=uuid.uuid4(), sede_id=sede_id, employee_id=employee_id, report_number="EXP-2024-01", status="approved")
        r3 = models.ExpenseReport(id=uuid.uuid4(), sede_id=sede_id, employee_id=employee_id, report_number="EXP-2025-01", status="approved")

        i1 = models.ExpenseItem(id=uuid.uuid4(), expense_report_id=r1.id, description="Servicios operativos 2023", amount=4000000.0, category="Operaciones", expense_date=dt.date(2023, 7, 1))
        i2 = models.ExpenseItem(id=uuid.uuid4(), expense_report_id=r2.id, description="Viaje misionero 2024", amount=6000000.0, category="Misiones", expense_date=dt.date(2024, 7, 1))
        i3 = models.ExpenseItem(id=uuid.uuid4(), expense_report_id=r3.id, description="Mantenimiento sede 2025", amount=7200000.0, category="Operaciones", expense_date=dt.date(2025, 7, 1))

        db.add_all([d1, d2, d3, r1, r2, r3, i1, i2, i3])
        db.commit()

        olap = DuckDBAnalyticsService()
        fin = olap.get_financial_summary(db_session=db)

        # Total Income = 43,000,000
        # Total Expenses = 17,200,000
        # Net Balance = 25,800,000
        assert fin["kpis"]["total_income"] == 43000000.0
        assert fin["kpis"]["total_expenses"] == 17200000.0
        assert fin["kpis"]["net_balance"] == 25800000.0
        assert fin["kpis"]["operating_margin_pct"] == 60.0

        # Multi-year trend items
        trend = fin["multi_year_trend"]
        assert len(trend) == 3
        assert trend[0]["year"] == 2023
        assert trend[0]["total_income"] == 10000000.0
        assert trend[1]["year"] == 2024
        assert trend[1]["total_income"] == 15000000.0
        assert trend[1]["yoy_growth_pct"] == 50.0
        assert trend[2]["year"] == 2025
        assert trend[2]["total_income"] == 18000000.0
        assert trend[2]["yoy_growth_pct"] == 20.0

    def test_query_execution_speed_benchmark_under_50ms(self, monkeypatch):
        """Stress tests DuckDB OLAP latency under 10,000+ records to empirically prove < 50ms query time."""
        olap = DuckDBAnalyticsService()

        # Connect directly to an in-memory DuckDB database and populate 10,000 records
        con = duckdb.connect(":memory:")
        olap._init_empty_tables(con)

        # 1. Insert 10,000 personas
        con.execute("BEGIN TRANSACTION;")
        con.execute("""
            INSERT INTO personas (id, sede_id, first_name, last_name, church_role, is_baptized, estado_vital, birthday, created_at)
            SELECT
                'persona-' || i,
                'sede-' || (i % 5),
                'Name' || i,
                'LastName' || i,
                CASE WHEN i % 10 = 0 THEN 'Lider' ELSE 'Miembro' END,
                (i % 2 = 0),
                'ACTIVO',
                DATE '1990-01-01' + INTERVAL (i % 10000) DAY,
                TIMESTAMP '2020-01-01 00:00:00' + INTERVAL (i * 30) MINUTE
            FROM range(10000) t(i);
        """)

        # 2. Insert 10,000 donations
        con.execute("""
            INSERT INTO donations (id, persona_id, amount, currency, sede_id, donation_type, status, donation_date, created_at)
            SELECT
                'donation-' || i,
                'persona-' || i,
                100000.0 + (i % 50000),
                'COP',
                'sede-' || (i % 5),
                CASE WHEN i % 3 = 0 THEN 'Diezmo' WHEN i % 3 = 1 THEN 'Ofrenda' ELSE 'Misiones' END,
                'completed',
                DATE '2022-01-01' + INTERVAL (i % 1000) DAY,
                TIMESTAMP '2022-01-01 00:00:00' + INTERVAL (i % 1000) DAY
            FROM range(10000) t(i);
        """)

        # 3. Insert 10,000 event attendances
        con.execute("""
            INSERT INTO crm_events (id, sede_id, name, event_type, event_date, created_at)
            SELECT
                'event-' || i,
                'sede-' || (i % 5),
                'Servicio ' || i,
                CASE WHEN i % 2 = 0 THEN 'DOMINICAL' ELSE 'JOVENES' END,
                TIMESTAMP '2022-01-01 00:00:00' + INTERVAL (i * 7) DAY,
                TIMESTAMP '2022-01-01 00:00:00' + INTERVAL (i * 7) DAY
            FROM range(500) t(i);
        """)
        con.execute("""
            INSERT INTO event_attendances (id, event_id, persona_id, session_date)
            SELECT
                'att-' || i,
                'event-' || (i % 500),
                'persona-' || (i % 10000),
                DATE '2022-01-01' + INTERVAL (i % 1000) DAY
            FROM range(10000) t(i);
        """)

        # 4. Insert 10,000 expense items
        con.execute("""
            INSERT INTO expense_reports (id, sede_id, employee_id, report_number, total_amount, currency, status, created_at)
            SELECT
                'report-' || i,
                'sede-' || (i % 5),
                'persona-' || i,
                'EXP-' || i,
                500000.0,
                'COP',
                'approved',
                TIMESTAMP '2022-01-01 00:00:00' + INTERVAL (i % 1000) DAY
            FROM range(1000) t(i);
        """)
        con.execute("""
            INSERT INTO expense_items (id, expense_report_id, expense_date, category, description, amount, currency, created_at)
            SELECT
                'item-' || i,
                'report-' || (i % 1000),
                DATE '2022-01-01' + INTERVAL (i % 1000) DAY,
                CASE WHEN i % 2 = 0 THEN 'Operations' ELSE 'Misiones' END,
                'Item ' || i,
                50000.0,
                'COP',
                TIMESTAMP '2022-01-01 00:00:00' + INTERVAL (i % 1000) DAY
            FROM range(10000) t(i);
        """)
        con.execute("COMMIT;")

        # Mock get_connection to return a connection cursor to the in-memory benchmark database
        monkeypatch.setattr(olap, "get_connection", lambda db_session=None: con.cursor())

        try:
            # Warmup
            olap.get_church_growth_metrics()
            olap.get_attendance_trends()
            olap.get_financial_summary()

            # Benchmark 1: Church Growth Metrics (over 10,000 personas)
            growth_times = []
            for _ in range(10):
                growth = olap.get_church_growth_metrics()
                growth_times.append(growth["execution_time_ms"])

            # Benchmark 2: Attendance Trends (over 10,000 attendances)
            att_times = []
            for _ in range(10):
                att = olap.get_attendance_trends()
                att_times.append(att["execution_time_ms"])

            # Benchmark 3: Financial Summary (over 10,000 donations + 10,000 expenses)
            fin_times = []
            for _ in range(10):
                fin = olap.get_financial_summary()
                fin_times.append(fin["execution_time_ms"])

            avg_growth = sum(growth_times) / len(growth_times)
            avg_att = sum(att_times) / len(att_times)
            avg_fin = sum(fin_times) / len(fin_times)

            print(f"\n[EMPIRICAL BENCHMARK — 10,000+ RECORDS]")
            print(f"Church Growth Query: avg = {avg_growth:.2f}ms (Target: <50ms)")
            print(f"Attendance Trends Query: avg = {avg_att:.2f}ms (Target: <50ms)")
            print(f"Financial Summary Query: avg = {avg_fin:.2f}ms (Target: <50ms)")

            # STRICT ASSERTIONS: Average sub-50ms query execution time target!
            assert avg_growth < 50.0, f"Growth query exceeded 50ms target: {avg_growth:.2f}ms"
            assert avg_att < 50.0, f"Attendance query exceeded 50ms target: {avg_att:.2f}ms"
            assert avg_fin < 50.0, f"Financial query exceeded 50ms target: {avg_fin:.2f}ms"

        finally:
            con.close()
