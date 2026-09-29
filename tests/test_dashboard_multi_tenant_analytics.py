"""Dashboard multi-tenant (Axioma 3) + DuckDB safe fallback.

Cubre TKT-CMS-BACKEND-ANALYTICS-04:
1. ``get_finance_dashboard`` / ``get_agenda_dashboard`` /
   ``get_admin_dashboard`` scoped por ``sede_id`` (resuelto del actor,
   nunca del cliente) y respetando soft deletes (``deleted_at IS NULL``).
2. ``event_sink.persist_event()`` y ``queries.py`` nunca lanzan
   excepciones fatales sin duckdb o con el warehouse roto: warning +
   fallback en memoria / payloads vacíos, sin tumbar peticiones.
3. ``GET /api/dashboard/overview`` agrega los KPIs de los módulos
   activos en una sola llamada, todo bajo Axioma 3.

Nota de entorno: ``tests/conftest.py`` fija ``sys.modules["duckdb"] =
None`` para simular instalaciones sin duckdb; la clase de fallback se
aprovecha de eso y además prueba el camino real del warehouse cargando
el módulo duckdb auténtico por su file loader.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend import models
from backend.analytics import event_sink, queries
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin
from tests.conftest import seed_user_with_role as _seed_user


def _load_real_duckdb():
    """Carga el módulo duckdb real pese al stub ``sys.modules[...]=None``."""
    saved = sys.modules.pop("duckdb", None)
    try:
        spec = importlib.util.find_spec("duckdb")
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:  # pragma: no cover - entorno sin duckdb real
        return None
    finally:
        sys.modules["duckdb"] = saved


REAL_DUCKDB = _load_real_duckdb()


# ═══════════════════════════════════════════════════════════════════
# Helpers de seed
# ═══════════════════════════════════════════════════════════════════


def _seed_two_sedes(db_session):
    """Admin en Sede A + Sede B; retorna (sede_a, sede_b, persona, admin)."""
    admin, persona, sede_a = _seed_admin(db_session, email="dash@test.com")
    sede_b = models.Sede(id=uuid.uuid4(), nombre="Sede B", ciudad="Cali", es_activa=True)
    db_session.add(sede_b)
    db_session.commit()
    return sede_a, sede_b, persona, admin


def _auth(client):
    return _auth_headers(client, email="dash@test.com", password="testpass123")


def _donation(db_session, sede_id, amount, *, deleted=False, donor=None):
    from backend.models_crm import Donation

    d = Donation(
        id=uuid.uuid4(),
        sede_id=sede_id,
        amount=amount,
        donation_type="Diezmo",
        donor_name=donor,
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )
    db_session.add(d)
    return d


def _evento(db_session, sede_id, organizer_id, titulo, *, deleted=False, days_ahead=2):
    from backend.models_agenda import EventoAgenda

    now = datetime.now(timezone.utc)
    ev = EventoAgenda(
        id=uuid.uuid4(),
        sede_id=sede_id,
        titulo=titulo,
        fecha_inicio=now + timedelta(days=days_ahead),
        fecha_fin=now + timedelta(days=days_ahead, hours=1),
        organizador_persona_id=organizer_id,
        deleted_at=now if deleted else None,
    )
    db_session.add(ev)
    return ev


# ═══════════════════════════════════════════════════════════════════
# 1. DuckDB safe fallback — persist_event / queries nunca lanzan
# ═══════════════════════════════════════════════════════════════════


class TestDuckDBSafeFallback:
    @pytest.fixture(autouse=True)
    def _clean_memory_sink(self):
        event_sink._MEMORY_EVENTS.clear()
        yield
        event_sink._MEMORY_EVENTS.clear()

    def test_persist_event_without_duckdb_does_not_raise(self):
        """Sin duckdb, persist_event degrada a memoria sin excepciones."""
        event_sink.persist_event("EnrollmentCreated", {"course_id": 1})
        events = event_sink.fetch_recent_events()
        assert len(events) == 1
        assert events[0][1] == "EnrollmentCreated"
        assert json.loads(events[0][2]) == {"course_id": 1}

    def test_persist_event_survives_broken_warehouse(self, monkeypatch):
        """duckdb.connect explotando ⇒ warning + memoria, nunca raise."""
        class _BrokenDuck:
            @staticmethod
            def connect(*_a, **_kw):
                raise RuntimeError("warehouse file corrupted")

        monkeypatch.setattr(event_sink, "duckdb", _BrokenDuck)
        event_sink.persist_event("AssessmentSubmitted", {"course_id": 2, "passed": True})
        assert len(event_sink.fetch_recent_events()) == 1

    def test_persist_event_survives_insert_failure(self, monkeypatch):
        """Fallo en el INSERT ⇒ el evento queda en el fallback en memoria."""
        class _BrokenConn:
            def execute(self, *a, **kw):
                raise RuntimeError("disk full")

            def close(self):
                pass

        monkeypatch.setattr(event_sink, "_connect", lambda: _BrokenConn())
        event_sink.persist_event("CertificateIssued", {"course_id": 3})
        assert len(event_sink.fetch_recent_events()) == 1

    def test_memory_sink_has_hard_cap(self, monkeypatch):
        """El fallback en memoria no crece sin límite."""
        monkeypatch.setattr(event_sink, "_MEMORY_MAX_EVENTS", 5)
        for i in range(8):
            event_sink.persist_event("Tick", {"i": i})
        assert len(event_sink.fetch_recent_events()) == 5

    def test_summary_memory_fallback(self):
        event_sink.persist_event("EnrollmentCreated", {"course_id": 1})
        event_sink.persist_event("EnrollmentCreated", {"course_id": 2})
        event_sink.persist_event("CertificateIssued", {"course_id": 1})
        summary = queries.get_event_summary(days=30)
        assert summary["total_events"] == 3
        names = {row["event_name"] for row in summary["by_event"]}
        assert names == {"EnrollmentCreated", "CertificateIssued"}
        top = summary["by_event"][0]
        assert top == {"event_name": "EnrollmentCreated", "count": 2}

    def test_summary_respects_days_window(self):
        event_sink.persist_event("Old", {})
        # Retro-traer el timestamp del único evento para simular antigüedad.
        old_ts = datetime.now(timezone.utc) - timedelta(days=40)
        with event_sink._MEMORY_LOCK:
            event_sink._MEMORY_EVENTS[0] = (old_ts, event_sink._MEMORY_EVENTS[0][1], event_sink._MEMORY_EVENTS[0][2])
        summary = queries.get_event_summary(days=7)
        assert summary["total_events"] == 0
        assert summary["by_event"] == []

    def test_course_performance_memory_fallback(self):
        event_sink.persist_event("EnrollmentCreated", {"course_id": 1})
        event_sink.persist_event("EnrollmentCreated", {"course_id": 1})
        event_sink.persist_event("CertificateIssued", {"course_id": 1})
        event_sink.persist_event("AssessmentSubmitted", {"course_id": 1, "passed": True})
        event_sink.persist_event("AssessmentSubmitted", {"course_id": 1, "passed": False})
        stats = queries.get_course_performance(limit=10)
        assert len(stats) == 1
        row = stats[0]
        assert row["course_id"] == 1
        assert row["enrollments"] == 2
        assert row["certificates"] == 1
        assert row["approvals"] == 1

    def test_course_performance_ignores_non_integer_course_ids(self):
        event_sink.persist_event("EnrollmentCreated", {"course_id": "no-soy-int"})
        assert queries.get_course_performance() == []

    def test_raw_events_memory_fallback(self):
        event_sink.persist_event("EnrollmentCreated", {"course_id": 7})
        raw = queries.list_raw_events(limit=5)
        assert len(raw) == 1
        assert raw[0]["event_name"] == "EnrollmentCreated"
        assert raw[0]["payload"] == {"course_id": 7}

    def test_real_warehouse_roundtrip(self, monkeypatch, tmp_path):
        """Camino feliz con duckdb real: persistir y leer del warehouse."""
        if REAL_DUCKDB is None:  # pragma: no cover - sin duckdb instalado
            pytest.skip("duckdb real no disponible")
        monkeypatch.setattr(event_sink, "duckdb", REAL_DUCKDB)
        monkeypatch.setattr(event_sink, "WAREHOUSE_PATH", tmp_path / "wh.duckdb")
        monkeypatch.setattr(event_sink, "_RESOLVED_WAREHOUSE_PATH", None)
        event_sink.persist_event("EnrollmentCreated", {"course_id": 1})
        event_sink.persist_event("CertificateIssued", {"course_id": 1})
        summary = queries.get_event_summary(days=30)
        assert summary["total_events"] == 2
        assert event_sink.is_available() is True

    def test_is_available_false_without_duckdb(self, monkeypatch):
        monkeypatch.setattr(event_sink, "duckdb", None)
        assert event_sink.is_available() is False


# ═══════════════════════════════════════════════════════════════════
# 2. Endpoint unificado GET /api/dashboard/overview (Axioma 3)
# ═══════════════════════════════════════════════════════════════════


class TestOverviewEndpoint:
    def test_overview_requires_auth(self, client, db_session):
        resp = client.get("/api/dashboard/overview")
        assert resp.status_code in (401, 403)

    def test_overview_scoped_by_actor_sede(self, client, db_session):
        sede_a, sede_b, persona, _admin = _seed_two_sedes(db_session)
        _donation(db_session, sede_a.id, 100, donor="A1")
        _donation(db_session, sede_b.id, 999, donor="B1")
        _evento(db_session, sede_a.id, persona.id, "Culto A")
        _evento(db_session, sede_b.id, persona.id, "Culto B")
        db_session.commit()

        resp = client.get("/api/dashboard/overview", headers=_auth(client))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["sede_id"] == str(sede_a.id)
        assert body["errors"] == {}
        assert set(body["modules"].keys()) == {"crm", "academy", "evangelism", "finance", "agenda", "projects"}
        assert datetime.fromisoformat(body["generated_at"]) is not None

        # KPI de finanzas refleja SOLO la sede del actor.
        finance_cards = {c["title"]: c["value"] for c in body["modules"]["finance"]["cards"]}
        assert finance_cards["Total Donaciones"] == "$100"

        # KPI de agenda refleja SOLO la sede del actor.
        agenda_titles = {e["titulo"] for e in body["modules"]["agenda"]["eventos_proximos"]}
        assert "Culto A" in agenda_titles
        assert "Culto B" not in agenda_titles

    def test_overview_excludes_soft_deleted_rows(self, client, db_session):
        sede_a, _sede_b, persona, _admin = _seed_two_sedes(db_session)
        _donation(db_session, sede_a.id, 100)
        _donation(db_session, sede_a.id, 500, deleted=True)
        _evento(db_session, sede_a.id, persona.id, "Culto vivo")
        _evento(db_session, sede_a.id, persona.id, "Culto borrado", deleted=True)
        db_session.commit()

        resp = client.get("/api/dashboard/overview", headers=_auth(client))
        assert resp.status_code == 200
        body = resp.json()
        finance_cards = {c["title"]: c["value"] for c in body["modules"]["finance"]["cards"]}
        assert finance_cards["Total Donaciones"] == "$100"
        assert finance_cards["Transacciones"] == "1"
        agenda_cards = {c["title"]: c["value"] for c in body["modules"]["agenda"]["cards"]}
        assert agenda_cards["Eventos"] == "1"

    def test_overview_never_accepts_client_sede(self, client, db_session):
        """Axioma 3: la sede SIEMPRE viene del actor, no de query params."""
        sede_a, sede_b, persona, _admin = _seed_two_sedes(db_session)
        _donation(db_session, sede_a.id, 100)
        _donation(db_session, sede_b.id, 999)
        db_session.commit()

        resp = client.get(
            f"/api/dashboard/overview?sede_id={sede_b.id}",
            headers=_auth(client),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["sede_id"] == str(sede_a.id)
        finance_cards = {c["title"]: c["value"] for c in body["modules"]["finance"]["cards"]}
        assert finance_cards["Total Donaciones"] == "$100"


# ═══════════════════════════════════════════════════════════════════
# 3. Dashboards por módulo — scope y soft deletes
# ═══════════════════════════════════════════════════════════════════


class TestModuleDashboardScoping:
    def test_finance_module_scoped_and_soft_delete_aware(self, client, db_session):
        sede_a, sede_b, _persona, _admin = _seed_two_sedes(db_session)
        _donation(db_session, sede_a.id, 250, donor="A1")
        _donation(db_session, sede_a.id, 400, donor="A-borrada", deleted=True)
        _donation(db_session, sede_b.id, 999, donor="B1")
        db_session.commit()

        resp = client.get("/api/dashboard/finance", headers=_auth(client))
        assert resp.status_code == 200
        body = resp.json()
        cards = {c["title"]: c["value"] for c in body["cards"]}
        assert cards["Total Donaciones"] == "$250"
        assert cards["Transacciones"] == "1"
        donors = {d["donor"] for d in body["latest_donations"]}
        assert "A1" in donors
        assert "A-borrada" not in donors
        assert "B1" not in donors

    def test_agenda_module_scoped(self, client, db_session):
        sede_a, sede_b, persona, _admin = _seed_two_sedes(db_session)
        _evento(db_session, sede_a.id, persona.id, "Culto A")
        _evento(db_session, sede_b.id, persona.id, "Culto B")
        db_session.commit()

        resp = client.get("/api/dashboard/agenda", headers=_auth(client))
        assert resp.status_code == 200
        body = resp.json()
        cards = {c["title"]: c["value"] for c in body["cards"]}
        assert cards["Eventos"] == "1"
        titles = {e["titulo"] for e in body["eventos_proximos"]}
        assert titles == {"Culto A"}

    def test_admin_dashboard_role_distribution_works(self, client, db_session):
        """La distribución de roles usa RolPlataforma (Auth v3), no Usuario.role."""
        _seed_two_sedes(db_session)
        resp = client.get("/api/dashboard/admin", headers=_auth(client))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        labels = {p["label"] for p in body["usuarios_por_rol"]}
        assert "ADMIN" in labels

    def test_admin_dashboard_forbidden_for_non_admin(self, client, db_session):
        _seed_two_sedes(db_session)
        _seed_user(
            db_session,
            role_name="persona",
            email="plain@dash.com",
            permisos={"dashboard:view": "allow"},
        )
        headers = _auth_headers(client, email="plain@dash.com", password="testpass123")
        resp = client.get("/api/dashboard/admin", headers=headers)
        assert resp.status_code == 403

    def test_unknown_module_returns_404(self, client, db_session):
        _seed_two_sedes(db_session)
        resp = client.get("/api/dashboard/no-existe", headers=_auth(client))
        assert resp.status_code == 404
