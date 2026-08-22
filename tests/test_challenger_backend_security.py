"""Adversarial Challenger Stress Suite: Backend & Security Architecture.

Empirical verification of:
1. FastMCP 2.0 Gateway:
   - Unauthorized access (no token -> 401/403, token lacking mcp:execute -> 403)
   - Malformed payloads, empty tool names, invalid tool parameters (400)
   - Non-existent servers (404) and non-existent tools (404)
   - Telemetry logging in tool_execution_logs (latency, status, arguments, request_id)
   - Zero-trust context propagation (X-Sede-ID, X-Persona-ID, X-Request-ID)

2. Pastoral RAG (pgvector / lexical hybrid search):
   - Multi-tenant isolation: User in Sede A cannot retrieve embeddings/articles/sermons from Sede B
   - Global articles (sede_id=None) visible to all tenants
   - Empty query (HTTP 422 via Pydantic contract) and whitespace-only query (HTTP 200 with empty list [])
   - Hybrid score boundaries (alpha=0.0 pure FTS, alpha=1.0 pure vector, clamped out-of-bounds alpha)
   - Limit boundary testing

3. DuckDB OLAP Engine:
   - Sub-50ms query execution speed verification across repeated iterations
   - Empty dataset safety (zeroed metrics, no crashes/NaNs)
   - Multi-year financial statements, growth trends, and attendance aggregations
   - Date range boundary filtering

4. DAG Workflow Engine:
   - Cyclic graph payloads (simple cycles, nested cycles)
   - Self-referential edges (A -> A)
   - Deeply nested acyclic graphs (100+ sequential and diamond nodes)
   - Runtime cycle detection in automation_engine preventing infinite loops
"""

from __future__ import annotations

import datetime as dt
import time
import uuid
from typing import Any, Dict, List
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from backend import models
from backend.models import Sede
from backend.models_agents import ToolExecutionLog
from backend.models_auth import RolPlataforma, Usuario
from backend.models_crm import Persona
from backend.models_knowledge_base import KnowledgeBaseArticle
from backend.models_sermones import Sermon
from backend.models_wiki import WikiPage
from backend.services.duckdb_engine import DuckDBAnalyticsService
from backend.services.rag_service import PastoralRAGService
from tests.conftest import TestingSessionLocal, auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin
from tests.conftest import seed_user_with_role as _seed_user_with_role


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures & Setup
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_mcp_session_local(monkeypatch):
    """Align SessionLocal across backend modules with test engine."""
    import backend.core.database
    import backend.mcp_academy
    import backend.mcp_agenda
    import backend.mcp_auth
    import backend.mcp_cms
    import backend.mcp_crm
    import backend.mcp_evangelism
    import backend.mcp_governance

    monkeypatch.setattr(backend.core.database, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_auth, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_agenda, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_crm, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_cms, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_academy, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_evangelism, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_governance, "SessionLocal", TestingSessionLocal)


@pytest.fixture
def test_setup(client, db_session):
    """Seed base sedes and users for adversarial security tests."""
    # Sedes
    sede_a = Sede(
        id=uuid.uuid4(),
        nombre="Sede A — Norte",
        ciudad="Bogota",
        es_activa=True,
        created_at=dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc),
    )
    sede_b = Sede(
        id=uuid.uuid4(),
        nombre="Sede B — Sur",
        ciudad="Medellin",
        es_activa=True,
        created_at=dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc),
    )
    db_session.add_all([sede_a, sede_b])
    db_session.flush()

    # Admin User (has full permissions including mcp:execute)
    admin_user, admin_p, _ = _seed_admin(db_session, email="admin_challenger@test.com")
    admin_h = _auth_headers(client, email="admin_challenger@test.com", password="testpass123")

    # Member in Sede A (NO mcp:execute, scoped to Sede A)
    user_a, p_a, _ = _seed_user_with_role(
        db_session,
        role_name="miembro_a",
        email="member_a_challenger@test.com",
        password="testpass123",
        sede_id=sede_a.id,
        permisos={"crm:read": "allow"},  # Missing mcp:execute
    )
    user_a_h = _auth_headers(client, email="member_a_challenger@test.com", password="testpass123")

    # Member in Sede B (NO mcp:execute, scoped to Sede B)
    user_b, p_b, _ = _seed_user_with_role(
        db_session,
        role_name="miembro_b",
        email="member_b_challenger@test.com",
        password="testpass123",
        sede_id=sede_b.id,
        permisos={"crm:read": "allow"},
    )
    user_b_h = _auth_headers(client, email="member_b_challenger@test.com", password="testpass123")

    # Operator in Sede A with mcp:execute & spiritual_life:read
    operator_mcp, p_op, _ = _seed_user_with_role(
        db_session,
        role_name="operador_mcp",
        email="operator_mcp@test.com",
        password="testpass123",
        sede_id=sede_a.id,
        permisos={
            "mcp:execute": "allow",
            "crm:read": "allow",
            "agenda:read": "allow",
            "spiritual_life:read": "allow",
        },
    )
    operator_h = _auth_headers(client, email="operator_mcp@test.com", password="testpass123")

    return {
        "c": client,
        "db": db_session,
        "sede_a": sede_a,
        "sede_b": sede_b,
        "admin": admin_user,
        "admin_h": admin_h,
        "user_a": user_a,
        "user_a_h": user_a_h,
        "user_b": user_b,
        "user_b_h": user_b_h,
        "operator": operator_mcp,
        "operator_h": operator_h,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. FastMCP Gateway Stress Suite
# ─────────────────────────────────────────────────────────────────────────────

class TestFastMcpGatewayAdversarial:
    def test_mcp_unauthenticated_calls_rejected(self, test_setup):
        c = test_setup["c"]
        # GET tools without auth -> 401/403
        res = c.get("/api/mcp/tools")
        assert res.status_code in (401, 403), f"Expected 401/403, got {res.status_code}"

        # GET server tools without auth -> 401/403
        res = c.get("/api/mcp/crm/tools")
        assert res.status_code in (401, 403)

        # POST tool call without auth -> 401/403
        res = c.post(
            "/api/mcp/crm/tools/call",
            json={"name": "list_calendar_events", "arguments": {}},
        )
        assert res.status_code in (401, 403)

    def test_mcp_forbidden_without_mcp_execute_permission(self, test_setup):
        c, h_user_a = test_setup["c"], test_setup["user_a_h"]

        # List all tools without mcp:execute -> HTTP 403
        res = c.get("/api/mcp/tools", headers=h_user_a)
        assert res.status_code == 403, f"Expected 403 for user lacking mcp:execute, got {res.status_code}"
        assert "mcp:execute" in res.json().get("detail", "")

        # List server tools without mcp:execute -> HTTP 403
        res = c.get("/api/mcp/crm/tools/list", headers=h_user_a)
        assert res.status_code == 403
        assert "mcp:execute" in res.json().get("detail", "")

        # Call tool without mcp:execute -> HTTP 403
        res = c.post(
            "/api/mcp/agenda/tools/call",
            headers=h_user_a,
            json={"name": "list_calendar_events", "arguments": {}},
        )
        assert res.status_code == 403
        assert "mcp:execute" in res.json().get("detail", "")

    def test_mcp_non_existent_server_404(self, test_setup):
        c, h_op = test_setup["c"], test_setup["operator_h"]

        res = c.get("/api/mcp/non_existent_domain_server/tools", headers=h_op)
        assert res.status_code == 404
        assert "not found" in res.json().get("detail", "").lower()

        res_call = c.post(
            "/api/mcp/non_existent_domain_server/tools/call",
            headers=h_op,
            json={"name": "any_tool", "arguments": {}},
        )
        assert res_call.status_code == 404

    def test_mcp_non_existent_tool_404(self, test_setup):
        c, h_op = test_setup["c"], test_setup["operator_h"]

        res = c.post(
            "/api/mcp/crm/tools/call",
            headers=h_op,
            json={"name": "ghost_nonexistent_tool_xyz_999", "arguments": {}},
        )
        assert res.status_code == 404
        assert "not found in mcp server" in res.json().get("detail", "").lower()

    def test_mcp_missing_or_malformed_tool_payload(self, test_setup):
        c, h_op = test_setup["c"], test_setup["operator_h"]

        # Missing tool name
        res = c.post("/api/mcp/crm/tools/call", headers=h_op, json={"arguments": {"key": "val"}})
        assert res.status_code == 400
        assert "name" in res.json().get("detail", "").lower()

        # Empty tool name
        res = c.post("/api/mcp/crm/tools/call", headers=h_op, json={"name": "", "arguments": {}})
        assert res.status_code == 400

    def test_mcp_authorized_call_and_telemetry_recorded(self, test_setup):
        c, db, h_op, op_user = test_setup["c"], test_setup["db"], test_setup["operator_h"], test_setup["operator"]

        # 1. Verify server list discovery
        res_servers = c.get("/api/mcp/servers")
        assert res_servers.status_code == 200
        servers = res_servers.json()["servers"]
        assert "crm" in servers
        assert "agenda" in servers
        assert "governance" in servers

        # 2. Execute call with unique request ID and custom headers
        custom_req_id = f"test-corr-req-{uuid.uuid4()}"
        res = c.post(
            "/api/mcp/agenda/tools/call",
            headers={
                **h_op,
                "X-Request-ID": custom_req_id,
                "X-Sede-ID": str(test_setup["sede_a"].id),
            },
            json={
                "name": "list_calendar_events",
                "arguments": {"limit": 5},
            },
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["success"] is True
        assert data["server"] == "agenda"
        assert data["tool"] == "list_calendar_events"
        assert data["latency_ms"] >= 0
        assert data["request_id"] == custom_req_id

        # 3. Verify telemetry in tool_execution_logs
        log = db.query(ToolExecutionLog).filter(ToolExecutionLog.request_id == custom_req_id).first()
        assert log is not None, "Tool execution log must be persisted in tool_execution_logs"
        assert log.tool_name == "list_calendar_events"
        assert log.status == "success"
        assert log.persona_id == op_user.id or log.persona_id == op_user.persona_id
        assert log.execution_time_ms >= 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pastoral RAG Stress Suite
# ─────────────────────────────────────────────────────────────────────────────

class TestPastoralRAGAdversarial:
    def test_rag_empty_and_whitespace_query_safety(self, test_setup):
        c, h_user_a = test_setup["c"], test_setup["user_a_h"]

        # Empty string violates min_length=1 in PastoralSearchRequest -> 422 Unprocessable Entity
        res_empty = c.post("/api/rag/pastoral/search", headers=h_user_a, json={"query": "", "limit": 10})
        assert res_empty.status_code == 422, f"Expected 422 for empty query, got {res_empty.status_code}"

        # Whitespace-only string satisfies min_length=1, handled safely by RAG service -> 200 with []
        res_ws = c.post("/api/rag/pastoral/search", headers=h_user_a, json={"query": "    \t\n  ", "limit": 10})
        assert res_ws.status_code == 200
        assert res_ws.json() == []

        # Direct service unit test with empty query returns []
        service = PastoralRAGService(db=test_setup["db"])
        assert service.search("") == []
        assert service.search("   ") == []

    def test_rag_multi_tenant_isolation_between_sedes(self, test_setup):
        """CRITICAL SECURITY TEST:

        Verify that User from Sede A NEVER retrieves documents exclusive to Sede B,
        and User from Sede B NEVER retrieves documents exclusive to Sede A.
        """
        db = test_setup["db"]
        s_a = test_setup["sede_a"]
        s_b = test_setup["sede_b"]

        # 1. Seed exclusive article in Sede A
        art_a = KnowledgeBaseArticle(
            id=uuid.uuid4(),
            sede_id=s_a.id,
            title="Protocolo Confidencial Pastoral Sede Norte",
            content="Instrucciones secretas y consejeria pastoral solo para ministros de Sede A Norte.",
            summary="Protocolo privado sede A",
            category="Pastoral",
            source_module="pastoral_a",
            is_active=True,
        )

        # 2. Seed exclusive article in Sede B
        art_b = KnowledgeBaseArticle(
            id=uuid.uuid4(),
            sede_id=s_b.id,
            title="Presupuesto Confidencial Sede Sur Medellín",
            content="Detalles financieros y estrategias de expansión exclusivas de Sede B Sur.",
            summary="Estrategia privada sede B",
            category="Finanzas",
            source_module="pastoral_b",
            is_active=True,
        )

        # 3. Seed exclusive sermon in Sede B
        sermon_b = Sermon(
            id=uuid.uuid4(),
            sede_id=s_b.id,
            title="Sermón Exclusivo de Liderazgo Medellín",
            preacher="Pastor Sede B",
            content="Mensaje y revelación ministerial dedicada a la congregación de Sede B.",
            summary="Sermón local Sede B",
            category="Liderazgo",
            is_published=True,
            is_active=True,
        )

        # 4. Seed Global article (sede_id=None) visible to all
        art_global = KnowledgeBaseArticle(
            id=uuid.uuid4(),
            sede_id=None,
            title="Doctrina General de la Iglesia CCF",
            content="Fundamentos doctrinales, fe en Jesucristo y visión global de la iglesia.",
            summary="Doctrina global",
            category="Doctrina",
            source_module="doctrina_global",
            is_active=True,
        )

        db.add_all([art_a, art_b, sermon_b, art_global])
        db.commit()

        # Query as User from Sede A searching for Sede B keywords
        service_user_a = PastoralRAGService(db=db, user_sede_id=s_a.id, user_role="miembro")
        results_a_looking_for_b = service_user_a.search(query="Presupuesto Confidencial Medellín", limit=10)
        
        # Sede A user must NOT receive Sede B items
        ids_returned_a = {str(r.id) for r in results_a_looking_for_b}
        assert str(art_b.id) not in ids_returned_a, "SECURITY VIOLATION: Sede A user retrieved Sede B article!"
        assert str(sermon_b.id) not in ids_returned_a, "SECURITY VIOLATION: Sede A user retrieved Sede B sermon!"

        # Query as User from Sede B searching for Sede A keywords
        service_user_b = PastoralRAGService(db=db, user_sede_id=s_b.id, user_role="miembro")
        results_b_looking_for_a = service_user_b.search(query="Protocolo Confidencial Pastoral Sede Norte", limit=10)
        ids_returned_b = {str(r.id) for r in results_b_looking_for_a}
        assert str(art_a.id) not in ids_returned_b, "SECURITY VIOLATION: Sede B user retrieved Sede A article!"

        # Both users CAN retrieve the Global document
        res_global_a = service_user_a.search(query="Doctrina General Jesucristo", limit=10)
        res_global_b = service_user_b.search(query="Doctrina General Jesucristo", limit=10)
        assert any(str(r.id) == str(art_global.id) for r in res_global_a), "Global doc must be visible to Sede A"
        assert any(str(r.id) == str(art_global.id) for r in res_global_b), "Global doc must be visible to Sede B"

    def test_rag_alpha_score_boundaries_and_clamping(self, test_setup):
        db = test_setup["db"]
        s_a = test_setup["sede_a"]

        doc = KnowledgeBaseArticle(
            id=uuid.uuid4(),
            sede_id=s_a.id,
            title="Oración y Ayuno en la Vida Cristiana",
            content="La importancia del ayuno bíblico y la comunión continua en oración matutina.",
            summary="Guía de ayuno",
            category="Espiritual",
            is_active=True,
        )
        db.add(doc)
        db.commit()

        service = PastoralRAGService(db=db, user_sede_id=s_a.id, user_role="miembro")

        # Alpha = 0.0 (Pure Lexical / FTS)
        res_fts = service.search(query="Oración y Ayuno", alpha=0.0, limit=5)
        assert len(res_fts) >= 1
        assert res_fts[0].score > 0.0
        assert res_fts[0].metadata.get("fts_score") is not None

        # Alpha = 1.0 (Pure Semantic Vector)
        res_vec = service.search(query="Oración y Ayuno", alpha=1.0, limit=5)
        assert len(res_vec) >= 1
        assert res_vec[0].score > 0.0
        assert res_vec[0].metadata.get("vec_score") is not None

        # Out-of-bounds alpha clamping (-1.0 -> 0.0, 5.0 -> 1.0)
        res_clamped_low = service.search(query="Oración y Ayuno", alpha=-1.0, limit=5)
        assert len(res_clamped_low) >= 1
        res_clamped_high = service.search(query="Oración y Ayuno", alpha=5.0, limit=5)
        assert len(res_clamped_high) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. DuckDB OLAP Stress Suite
# ─────────────────────────────────────────────────────────────────────────────

class TestDuckDBOlapAdversarial:
    def test_duckdb_empty_dataset_safety(self, db_session):
        """Verify queries against an empty database return valid zeroed structures without errors."""
        service = DuckDBAnalyticsService()

        # Growth on empty DB (passing clean db_session)
        growth = service.get_church_growth_metrics(db_session=db_session)
        assert growth["source"] == "duckdb/in-memory-olap"
        assert growth["execution_time_ms"] < 50.0
        assert growth["summary"]["total_members"] == 0
        assert growth["trends"] == []
        assert growth["by_sede"] == []

        # Attendance trends on empty DB
        att = service.get_attendance_trends(db_session=db_session)
        assert att["source"] == "duckdb/in-memory-olap"
        assert att["execution_time_ms"] < 50.0
        assert att["summary"]["total_attendances"] == 0
        assert att["by_age_group"] == []

        # Financial summary on empty DB
        fin = service.get_financial_summary(db_session=db_session)
        assert fin["source"] == "duckdb/in-memory-olap"
        assert fin["execution_time_ms"] < 50.0
        assert fin["kpis"]["total_income"] == 0.0
        assert fin["kpis"]["total_expenses"] == 0.0
        assert fin["multi_year_trend"] == []

    def test_duckdb_sub_50ms_performance_stress(self, test_setup):
        """Stress-test 20 consecutive OLAP queries verifying average internal execution time stays sub-50ms."""
        db = test_setup["db"]
        service = DuckDBAnalyticsService()

        engine_latencies = []
        for i in range(20):
            res = service.get_church_growth_metrics(db_session=db)
            exec_time = res["execution_time_ms"]
            engine_latencies.append(exec_time)

        avg_latency = sum(engine_latencies) / len(engine_latencies)
        max_latency = max(engine_latencies)
        # Average must be sub-50ms (the true SLA). A single spike from OS scheduler
        # jitter is acceptable; what matters is the sustained average performance.
        assert avg_latency < 50.0, f"Average DuckDB latency {avg_latency:.2f}ms exceeds 50ms target"
        # No single query should exceed 200ms (guards against catastrophic slowdowns).
        assert max_latency < 200.0, f"Peak DuckDB latency {max_latency:.2f}ms exceeds 200ms ceiling"

    def test_duckdb_multi_year_aggregations_and_date_filtering(self, test_setup):
        db = test_setup["db"]
        s_a = test_setup["sede_a"]
        service = DuckDBAnalyticsService()

        # Seed multi-year donations
        p1 = Persona(
            id=uuid.uuid4(),
            sede_id=s_a.id,
            first_name="Carlos",
            last_name="Prueba",
            email="carlos_olap@test.com",
            church_role="Lider",
            is_baptized=True,
            estado_vital="ACTIVO",
            birthday=dt.date(1985, 4, 12),
            created_at=dt.datetime(2022, 5, 10, tzinfo=dt.timezone.utc),
        )
        db.add(p1)
        db.flush()

        d2023 = models.Donation(
            id=uuid.uuid4(),
            persona_id=p1.id,
            sede_id=s_a.id,
            amount=1000000.0,
            currency="COP",
            donation_type="Diezmo",
            status="completed",
            donation_date=dt.date(2023, 6, 1),
            created_at=dt.datetime(2023, 6, 1, tzinfo=dt.timezone.utc),
        )
        d2024 = models.Donation(
            id=uuid.uuid4(),
            persona_id=p1.id,
            sede_id=s_a.id,
            amount=2000000.0,
            currency="COP",
            donation_type="Diezmo",
            status="completed",
            donation_date=dt.date(2024, 6, 1),
            created_at=dt.datetime(2024, 6, 1, tzinfo=dt.timezone.utc),
        )
        d2025 = models.Donation(
            id=uuid.uuid4(),
            persona_id=p1.id,
            sede_id=s_a.id,
            amount=3000000.0,
            currency="COP",
            donation_type="Ofrenda",
            status="completed",
            donation_date=dt.date(2025, 6, 1),
            created_at=dt.datetime(2025, 6, 1, tzinfo=dt.timezone.utc),
        )
        db.add_all([d2023, d2024, d2025])
        db.commit()

        # Query all years
        fin_all = service.get_financial_summary(db_session=db)
        assert fin_all["kpis"]["total_income"] == 6000000.0
        years = [row["year"] for row in fin_all["multi_year_trend"]]
        assert 2023 in years and 2024 in years and 2025 in years

        # Filter by year range: 2024 to 2024
        fin_2024 = service.get_financial_summary(start_year=2024, end_year=2024, db_session=db)
        assert fin_2024["kpis"]["total_income"] == 2000000.0
        assert len(fin_2024["multi_year_trend"]) == 1
        assert fin_2024["multi_year_trend"][0]["year"] == 2024


# ─────────────────────────────────────────────────────────────────────────────
# 4. DAG Workflow Engine Stress Suite
# ─────────────────────────────────────────────────────────────────────────────

class TestDagWorkflowEngineAdversarial:
    def test_dag_simple_cycle_detection(self, test_setup):
        c, h_admin = test_setup["c"], test_setup["admin_h"]

        # Cycle: N1 -> N2 -> N3 -> N1
        payload = {
            "flow_data": {
                "nodes": [{"id": "N1"}, {"id": "N2"}, {"id": "N3"}],
                "edges": [
                    {"source": "N1", "target": "N2"},
                    {"source": "N2", "target": "N3"},
                    {"source": "N3", "target": "N1"},
                ],
            }
        }

        # check-cycles endpoint
        res = c.post("/api/crm/automations/flows/check-cycles", headers=h_admin, json=payload)
        assert res.status_code == 200, res.text
        data = res.json()
        assert len(data["cycles"]) >= 1, "Must detect at least 1 cycle in N1->N2->N3->N1"

        # validate-graph endpoint
        res_val = c.post("/api/crm/automations/validate-graph", headers=h_admin, json=payload)
        assert res_val.status_code == 200
        assert res_val.json()["valid"] is False
        assert "cycle detected" in res_val.json()["error"].lower()

    def test_dag_self_referential_edge(self, test_setup):
        c, h_admin = test_setup["c"], test_setup["admin_h"]

        # Self-loop: N1 -> N1
        payload = {
            "node_id": "N1",
            "flow_data": {
                "nodes": [{"id": "N1"}, {"id": "N2"}],
                "edges": [
                    {"source": "N1", "target": "N1"},
                    {"source": "N1", "target": "N2"},
                ],
            },
        }

        res = c.post("/api/crm/automations/flows/validate-node", headers=h_admin, json=payload)
        assert res.status_code == 200
        assert res.json()["valid"] is False
        assert "self-reference" in res.json()["error"].lower()

    def test_dag_deeply_nested_acyclic_graph_100_nodes(self, test_setup):
        """Stress-test a deeply nested 100-node linear DAG + multi-parent branches."""
        c, h_admin = test_setup["c"], test_setup["admin_h"]

        num_nodes = 100
        nodes = [{"id": f"node_{i}"} for i in range(num_nodes)]
        edges = [{"source": f"node_{i}", "target": f"node_{i+1}"} for i in range(num_nodes - 1)]

        # Add cross-level shortcut edges maintaining acyclicity (e.g. node_0 -> node_50, node_10 -> node_80)
        edges.append({"source": "node_0", "target": "node_50"})
        edges.append({"source": "node_10", "target": "node_80"})
        edges.append({"source": "node_25", "target": "node_75"})

        payload = {"flow_data": {"nodes": nodes, "edges": edges}}

        t0 = time.perf_counter()
        res = c.post("/api/crm/automations/flows/check-cycles", headers=h_admin, json=payload)
        t_ms = (time.perf_counter() - t0) * 1000.0

        assert res.status_code == 200
        assert len(res.json()["cycles"]) == 0, "100-node DAG must have 0 cycles"
        assert t_ms < 50.0, f"100-node cycle detection took {t_ms:.2f}ms (>50ms)"

        res_val = c.post("/api/crm/automations/validate-graph", headers=h_admin, json=payload)
        assert res_val.status_code == 200
        assert res_val.json()["valid"] is True

    def test_dag_runtime_cycle_handling_in_automation_engine(self, test_setup):
        """Verify automation_engine runtime DFS detects cycles and marks action as failed."""
        db = test_setup["db"]
        from backend.models_crm import CrmAutomation, CrmAutomationEdge, PendingCrmAction
        from backend.models_shared import _utcnow
        from backend.services.automation_engine import engine

        # Create cyclic DB automations: Auto1 -> Auto2 -> Auto1
        a1 = CrmAutomation(
            id=uuid.uuid4(),
            name="Cyclic Auto 1",
            trigger_event="stage_change",
            action_type="send_email",
            delay_minutes=0,
        )
        a2 = CrmAutomation(
            id=uuid.uuid4(),
            name="Cyclic Auto 2",
            trigger_event="stage_change",
            action_type="send_email",
            delay_minutes=0,
        )
        db.add_all([a1, a2])
        db.flush()

        e1 = CrmAutomationEdge(
            id=uuid.uuid4(),
            source_id=a1.id,
            target_id=a2.id,
            condition_type="always",
        )
        e2 = CrmAutomationEdge(
            id=uuid.uuid4(),
            source_id=a2.id,
            target_id=a1.id,
            condition_type="always",
        )
        db.add_all([e1, e2])
        db.flush()

        # Queue a pending action for a1
        persona_test = Persona(
            id=uuid.uuid4(),
            first_name="Target",
            last_name="Cycle",
            email="cycle_target@test.com",
            estado_vital="ACTIVO",
        )
        db.add(persona_test)
        db.flush()

        action = PendingCrmAction(
            id=uuid.uuid4(),
            automation_id=a1.id,
            target_persona_id=persona_test.id,
            execute_at=_utcnow() - dt.timedelta(minutes=5),
            status="pending",
        )
        db.add(action)
        db.commit()

        # Run one check pass of CRM pending actions
        engine._process_crm_pending_actions(db)

        # Refresh action and verify it was failed due to cycle
        db.refresh(action)
        assert action.status == "failed", f"Expected status 'failed' due to cycle, got '{action.status}'"
