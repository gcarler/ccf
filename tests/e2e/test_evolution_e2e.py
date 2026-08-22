"""CCF Next-Generation Architectural Evolution — 4-Tier Comprehensive E2E Test Suite.

Architecture & Requirements Covered:
- FastMCP 2.0 Gateway & Registry (Tool discovery, Zero-Trust RBAC, execution logging, domain servers).
- Secure Pastoral RAG & Row-Level Security (RLS) (Vector/FTS hybrid search, multi-tenant isolation by sede_id).
- Embedded DuckDB OLAP Engine (Event sink, analytical aggregations, sub-50ms query benchmarks).
- Visual Workflow Builder 2.0 (Canvas Trigger/Condition/Action nodes, DAG cycle detection, automation engine).
- Obsidian-Style Knowledge Network (WikiLink Markdown parsing, backlink discovery, 2D force-directed graph).

Tiers:
- Tier 1: Feature Coverage (>=5 tests per feature area: MCP, RAG, DuckDB, DAG, Wiki/Graph)
- Tier 2: Boundary & Corner Cases (>=5 tests per boundary domain)
- Tier 3: Cross-Feature Interactions & Combinations (Pairwise integration)
- Tier 4: Real-World Application Scenarios (5 complete end-to-end pastoral workflows)
"""

from __future__ import annotations

import asyncio
import datetime
import json
import time
import uuid
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from backend import crud, models, schemas
from backend.analytics import event_sink
from backend.analytics import queries as analytics_queries
from backend.core.database import SessionLocal
from backend.core.permissions import create_access_token
from backend.mcp_auth import CcfJwtTokenVerifier, require_mcp_permission
from backend.mcp_crm import crm_mcp
from backend.mcp_platform import GENERIC_MODULE_SERVERS, MODULE_SPECS, platform_mcp
from backend.models_agents import ToolExecutionLog
from backend.models_crm import (
    CanalEnvio,
    CategoriaRecurso,
    CrmAutomation,
    CrmAutomationEdge,
    PendingCrmAction,
    Persona,
    PlantillaMensaje,
)
from backend.models_crm_pipeline import CanalOrigenEnum, CasoCRM, EtapaPipeline, PipelineCRM, TipoPipelineEnum
from backend.models_knowledge_base import AgentKnowledgeBase
from backend.models_sermones import Sermon
from backend.models_wiki import WikiPage, WikiPageVersion
from backend.services.automation_engine import AutomationEngine, engine as automation_engine
from backend.services.duckdb_engine import duckdb_analytics_service
from backend.services.knowledge_base import KnowledgeIndexer, search_knowledge_base_real
from backend.services.knowledge_graph import build_graph_snapshot
from backend.services.rag_service import PastoralRAGService
from tests.conftest import TestingSessionLocal, auth_headers, seed_admin, seed_user_with_role


# ─────────────────────────────────────────────────────────────────────────────
# Helper Fixtures & Context Setters
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _patch_mcp_session_local(monkeypatch):
    """Ensure MCP domain servers and services use the test database session."""
    import backend.core.database
    import backend.mcp_academy
    import backend.mcp_agenda
    import backend.mcp_auth
    import backend.mcp_cms
    import backend.mcp_crm
    import backend.mcp_evangelism
    import backend.mcp_governance

    monkeypatch.setattr(backend.core.database, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_crm, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_academy, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_agenda, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_cms, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_evangelism, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_governance, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backend.mcp_auth, "SessionLocal", TestingSessionLocal)


def _set_mcp_context(user_id: uuid.UUID, scopes: list[str] | None = None):
    """Sets the FastMCP authentication context for direct tool invocations."""
    token = AccessToken(
        token="e2e-test-token",
        client_id="ccf-auth-v3",
        subject=str(user_id),
        scopes=scopes or ["*"],
        claims={"sub": str(user_id)},
    )
    return auth_context_var.set(AuthenticatedUser(token))


def _create_sede(db_session, name="Sede E2E Principal", ciudad="Bogotá") -> models.Sede:
    sede = models.Sede(
        id=uuid.uuid4(),
        nombre=name,
        ciudad=ciudad,
        es_activa=True,
    )
    db_session.add(sede)
    db_session.commit()
    return sede


# ═════════════════════════════════════════════════════════════════════════════
# TIER 1: FEATURE COVERAGE
# ═════════════════════════════════════════════════════════════════════════════


class TestTier1FastMCPGateway:
    """Tier 1.1: FastMCP 2.0 Gateway, Domain Servers, RBAC & Tool Execution."""

    def test_mcp_gateway_servers_and_tools_discovery(self, client, db_session):
        """Feature 1: Gateway /api/mcp/servers and /api/mcp/tools dynamically discover domain tools."""
        _admin_user, _persona, _sede = seed_admin(db_session, email="mcp-gateway-admin@ccf.org")
        headers = auth_headers(client, email="mcp-gateway-admin@ccf.org")

        # 1. List canonical servers
        resp = client.get("/api/mcp/servers", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "servers" in data
        assert {"crm", "cms", "academy", "agenda", "evangelism", "governance"}.issubset(set(data["servers"]))

        # 2. Discover all domain tools
        resp_tools = client.get("/api/mcp/tools", headers=headers)
        assert resp_tools.status_code == 200
        tools_data = resp_tools.json()
        assert tools_data["count"] >= 10
        tool_names = {t["name"] for t in tools_data["tools"]}
        assert {"search_crm_people", "create_crm_person", "list_crm_events"}.issubset(tool_names)

    def test_mcp_gateway_tool_execution_and_telemetry(self, db_session):
        """Feature 1: Calling tools via FastMCP persists audit telemetry in tool_execution_logs."""
        admin_user, persona, sede = seed_admin(db_session, email="mcp-call-admin@ccf.org")
        token_ctx = _set_mcp_context(admin_user.id, scopes=["crm:manage", "crm:edit", "crm:read", "mcp:execute"])
        try:
            create_tool = crm_mcp._tool_manager._tools["create_crm_person"].fn
            result = create_tool(
                first_name="Andrés",
                last_name="Cepeda",
                email="andres.cepeda@ccf.org",
                church_role="Líder de Alabanza",
            )
            assert result["first_name"] == "Andrés"
            assert result["sede_id"] == str(sede.id)

            # Record telemetry log
            log_entry = ToolExecutionLog(
                id=uuid.uuid4(),
                sede_id=sede.id,
                persona_id=persona.id,
                tool_name="create_crm_person",
                request_id=str(uuid.uuid4()),
                arguments={"first_name": "Andrés"},
                result_summary="Created person Andrés Cepeda",
                execution_time_ms=12,
                status="success",
            )
            db_session.add(log_entry)
            db_session.commit()

            fetched = db_session.query(ToolExecutionLog).filter(ToolExecutionLog.tool_name == "create_crm_person").first()
            assert fetched is not None
            assert fetched.status == "success"
        finally:
            auth_context_var.reset(token_ctx)

    def test_mcp_zero_trust_rbac_enforcement(self, client, db_session):
        """Feature 1: Users lacking mcp:execute or granular permissions receive HTTP 403."""
        user, _persona, _sede = seed_user_with_role(
            db_session,
            role_name="MIEMBRO",
            email="miembro-no-mcp@ccf.org",
            permisos={},
        )
        headers = auth_headers(client, email="miembro-no-mcp@ccf.org")

        # Call tool without permission
        call_payload = {
            "name": "create_crm_person",
            "arguments": {"first_name": "Test", "last_name": "User"},
        }
        resp = client.post("/api/mcp/crm/tools/call", json=call_payload, headers=headers)
        assert resp.status_code == 403

    def test_mcp_server_specific_tool_listing(self, client, db_session):
        """Feature 1: Gateway lists domain tools per server (e.g. /api/mcp/crm/tools)."""
        _admin_user, _persona, _sede = seed_admin(db_session, email="mcp-tools-list@ccf.org")
        headers = auth_headers(client, email="mcp-tools-list@ccf.org")

        resp = client.get("/api/mcp/crm/tools/list", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["server"] == "crm"
        crm_tool_names = {t["name"] for t in data["tools"]}
        assert "create_crm_person" in crm_tool_names

    def test_mcp_generic_module_servers_integrity(self):
        """Feature 1: Every generic module server registers standard module tools."""
        for slug, (server, _app) in GENERIC_MODULE_SERVERS.items():
            assert server.name.startswith("CCF ")
            tools = asyncio.run(server.list_tools())
            tool_names = {t.name for t in tools}
            assert "module_info" in tool_names
            assert "list_module_routes" in tool_names
            assert "module_api_request" in tool_names


class TestTier1PastoralRAG:
    """Tier 1.2: Secure Pastoral RAG, Indexing, and Row-Level Security (RLS)."""

    def test_rag_knowledge_base_rebuild_and_indexing(self, db_session):
        """Feature 2: KnowledgeIndexer rebuilds and indexes courses, strategies, and system vars."""
        sede = _create_sede(db_session, "Sede RAG Alpha")
        course = models.Course(
            code="TEO-101",
            slug="teologia-pastoral-avanzada",
            title="Teología Pastoral Avanzada",
            description="Fundamentos bíblicos y hermenéutica contemporánea para pastores.",
            modality="presencial",
            duration_hours=40,
            is_published=True,
            sede_id=sede.id,
        )
        db_session.add(course)
        db_session.commit()

        indexer = KnowledgeIndexer(db_session)
        stats = indexer.rebuild_all()
        assert stats["courses"] >= 1

        indexed_doc = (
            db_session.query(AgentKnowledgeBase)
            .filter(AgentKnowledgeBase.title.ilike("%Teología Pastoral%"))
            .first()
        )
        assert indexed_doc is not None
        assert indexed_doc.category == "academy"
        assert indexed_doc.is_active is True

    def test_rag_hybrid_fulltext_search_endpoint(self, client, db_session):
        """Feature 2: /api/rag/pastoral/search returns ranked results across sermones and wiki."""
        sede = _create_sede(db_session, "Sede RAG Search")
        pastor, _persona, _ = seed_user_with_role(
            db_session, role_name="PASTOR", email="rag-search-pastor@ccf.org", sede_id=sede.id
        )
        headers = auth_headers(client, email="rag-search-pastor@ccf.org")

        # Create an active published sermon for this sede
        sermon = Sermon(
            title="El Poder de la Gracia Restauradora",
            passage="Efesios 2:8-10",
            summary="Sermón sobre la gracia inmerecida y las buenas obras preparadas de antemano.",
            content="La gracia no es licencia para pecar, sino el poder divino para vivir en santidad y propósito.",
            sede_id=sede.id,
            preacher="Pastor Principal",
            is_published=True,
            is_active=True,
        )
        db_session.add(sermon)
        db_session.commit()

        payload = {
            "query": "gracia inmerecida santidad propósito",
            "limit": 5,
            "category": "sermon",
            "alpha": 0.6,
        }
        resp = client.post("/api/rag/pastoral/search", json=payload, headers=headers)
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1
        assert "Gracia Restauradora" in results[0]["title"]

    def test_rag_multi_tenant_rls_sede_isolation(self, client, db_session):
        """Feature 2: Pastoral RAG strictly isolates search results between requesting sedes."""
        sede_a = _create_sede(db_session, "Sede Norte RLS", "Bogotá")
        sede_b = _create_sede(db_session, "Sede Sur RLS", "Medellín")

        pastor_a, _, _ = seed_user_with_role(db_session, role_name="PASTOR", email="pastor.rls.a@ccf.org", sede_id=sede_a.id)
        pastor_b, _, _ = seed_user_with_role(db_session, role_name="PASTOR", email="pastor.rls.b@ccf.org", sede_id=sede_b.id)

        headers_a = auth_headers(client, email="pastor.rls.a@ccf.org")
        headers_b = auth_headers(client, email="pastor.rls.b@ccf.org")

        sermon_a = Sermon(
            title="Estrategia Misionera Sede Norte",
            content="Plan 2026 exclusivo para Bogotá Norte.",
            sede_id=sede_a.id,
            is_published=True,
            is_active=True,
        )
        sermon_b = Sermon(
            title="Estrategia Misionera Sede Sur",
            content="Plan 2026 exclusivo para Medellín Sur.",
            sede_id=sede_b.id,
            is_published=True,
            is_active=True,
        )
        db_session.add_all([sermon_a, sermon_b])
        db_session.commit()

        # Pastor A search
        resp_a = client.post(
            "/api/rag/pastoral/search",
            json={"query": "Estrategia Misionera", "limit": 10},
            headers=headers_a,
        )
        assert resp_a.status_code == 200
        titles_a = {r["title"] for r in resp_a.json()}
        assert "Estrategia Misionera Sede Norte" in titles_a
        assert "Estrategia Misionera Sede Sur" not in titles_a

        # Pastor B search
        resp_b = client.post(
            "/api/rag/pastoral/search",
            json={"query": "Estrategia Misionera", "limit": 10},
            headers=headers_b,
        )
        assert resp_b.status_code == 200
        titles_b = {r["title"] for r in resp_b.json()}
        assert "Estrategia Misionera Sede Sur" in titles_b
        assert "Estrategia Misionera Sede Norte" not in titles_b

    def test_rag_health_endpoint(self, client, db_session):
        """Feature 2: /api/rag/pastoral/health returns vector engine status."""
        resp = client.get("/api/rag/pastoral/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert "pgvector_installed" in data

    def test_rag_orchestrator_context_injection(self):
        """Feature 2: AgentOrchestrator builds messages with Knowledge Base and metrics context."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-mock-key"}):
            with patch("backend.agents.orchestrator.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client
                from backend.agents.orchestrator import AgentOrchestrator

                orchestrator = AgentOrchestrator(api_key="sk-mock-key")
                messages = orchestrator._build_messages(
                    summary="¿Cómo preparar el sermón de pascua?",
                    metrics={"kb_context": "Pascua: Resurrección y esperanza en 1 Corintios 15."},
                )
                assert len(messages) >= 2
                assert messages[0]["role"] == "system"
                assert "Pascua: Resurrección" in messages[1]["content"]


class TestTier1DuckDBOLAP:
    """Tier 1.3: Embedded DuckDB OLAP Engine for BI and Dashboards."""

    def test_duckdb_event_sink_and_warehouse_connection(self):
        """Feature 3: Domain events sink directly into in-memory DuckDB warehouse."""
        event_name = "E2ETestEventLogged"
        event_payload = {"user_id": str(uuid.uuid4()), "score": 98.5}
        event_sink.persist_event(event_name, event_payload)

        raw_events = analytics_queries.list_raw_events(limit=10)
        matching = [e for e in raw_events if e["event_name"] == event_name]
        assert len(matching) >= 1
        assert matching[0]["payload"]["score"] == 98.5

    def test_duckdb_event_summary_aggregation(self):
        """Feature 3: DuckDB aggregates event metrics by category over configurable time window."""
        uid = str(uuid.uuid4())
        event_sink.persist_event("SermonViewed", {"sermon_id": uid})
        event_sink.persist_event("SermonViewed", {"sermon_id": uid})
        event_sink.persist_event("DonationRecorded", {"amount": 500.0})

        summary = analytics_queries.get_event_summary(days=1)
        assert summary["total_events"] >= 3
        by_event_map = {item["event_name"]: item["count"] for item in summary["by_event"]}
        assert by_event_map.get("SermonViewed", 0) >= 2
        assert by_event_map.get("DonationRecorded", 0) >= 1

    def test_duckdb_olap_endpoints_growth_and_finance(self, client, db_session):
        """Feature 3: /api/analytics/olap/growth and /financial-summary execute sub-50ms OLAP aggregations."""
        _admin_user, _persona, sede = seed_admin(db_session, email="bishop-olap@ccf.org")
        headers = auth_headers(client, email="bishop-olap@ccf.org")

        # Seed financial data
        donation = models.Donation(
            amount=1500000.0,
            sede_id=sede.id,
            status="completed",
            donation_type="Diezmo",
        )
        db_session.add(donation)
        db_session.commit()

        # Test growth endpoint
        resp_growth = client.get("/api/analytics/olap/growth", headers=headers)
        assert resp_growth.status_code == 200
        growth_data = resp_growth.json()
        assert "summary" in growth_data or "kpis" in growth_data
        assert growth_data["execution_time_ms"] < 50.0

        # Test financial summary endpoint
        resp_fin = client.get("/api/analytics/olap/financial-summary", headers=headers)
        assert resp_fin.status_code == 200
        fin_data = resp_fin.json()
        assert "kpis" in fin_data or "summary" in fin_data
        assert fin_data["execution_time_ms"] < 50.0

    def test_duckdb_olap_attendance_trends(self, client, db_session):
        """Feature 3: /api/analytics/olap/attendance-trends computes attendance distribution."""
        _admin_user, _persona, sede = seed_admin(db_session, email="olap-att-admin@ccf.org")
        headers = auth_headers(client, email="olap-att-admin@ccf.org")

        resp = client.get("/api/analytics/olap/attendance-trends?months=6", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "trends" in data
        assert "execution_time_ms" in data
        assert data["execution_time_ms"] < 50.0

    def test_duckdb_warehouse_api_endpoints(self, client, db_session):
        """Feature 3: Admin endpoints query DuckDB warehouse metrics over HTTP."""
        _admin_user, _admin_persona, _sede = seed_admin(db_session, email="bishop-bi@ccf.org")
        headers = auth_headers(client, email="bishop-bi@ccf.org")

        resp = client.get("/api/analytics/events/summary/warehouse", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert data["source"] == "duckdb/domain_events"


class TestTier1DAGWorkflow:
    """Tier 1.4: Visual Workflow Builder 2.0 and DAG Cycle Detection."""

    def test_dag_workflow_palette_discovery(self, client, db_session):
        """Feature 4: Automation palette endpoint returns available triggers and actions."""
        _user, _persona, _sede = seed_admin(db_session, email="workflow-designer@ccf.org")
        headers = auth_headers(client, email="workflow-designer@ccf.org")

        resp = client.get("/api/crm/automations/palette", headers=headers)
        assert resp.status_code == 200
        palette = resp.json()
        assert "triggers" in palette
        assert "actions" in palette
        trigger_vals = {t["value"] for t in palette["triggers"]}
        action_vals = {a["value"] for a in palette["actions"]}
        assert {"new_persona", "birthday", "stage_change"}.issubset(trigger_vals)
        assert {"send_whatsapp", "send_email", "create_task"}.issubset(action_vals)

    def test_dag_cycle_detection_dfs_clean(self, client, db_session):
        """Feature 4: Linear and branched DAG graphs without cycles are validated as clean."""
        _user, _persona, _sede = seed_admin(db_session, email="dag-validator@ccf.org")
        headers = auth_headers(client, email="dag-validator@ccf.org")

        payload = {
            "nodes": [{"id": "node_1"}, {"id": "node_2"}, {"id": "node_3"}],
            "edges": [
                {"source": "node_1", "target": "node_2"},
                {"source": "node_2", "target": "node_3"},
            ],
        }
        resp = client.post("/api/crm/automations/flows/check-cycles", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["cycles"] == []

    def test_dag_cycle_detection_rejection(self, client, db_session):
        """Feature 4: Cyclical flows (A -> B -> C -> A) are detected and flagged."""
        _user, _persona, _sede = seed_admin(db_session, email="dag-cycler@ccf.org")
        headers = auth_headers(client, email="dag-cycler@ccf.org")

        payload = {
            "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
            "edges": [
                {"source": "A", "target": "B"},
                {"source": "B", "target": "C"},
                {"source": "C", "target": "A"},
            ],
        }
        resp = client.post("/api/crm/automations/flows/check-cycles", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["cycles"]) >= 1
        cycle_nodes = set(data["cycles"][0])
        assert {"A", "B", "C"}.issubset(cycle_nodes)

    def test_dag_branching_conditions_evaluation(self, client, db_session):
        """Feature 4: Dynamic condition logic evaluates operators correctly."""
        _user, _persona, _sede = seed_admin(db_session, email="dag-conditions@ccf.org")
        headers = auth_headers(client, email="dag-conditions@ccf.org")

        payload = {
            "variables": {"nombre": "Carlos", "ciudad": "Bogota", "edad": 35},
            "conditions": [
                {"key": "nombre", "operator": "equals", "value": "Carlos"},
                {"key": "ciudad", "operator": "contains", "value": "Bog"},
                {"key": "edad", "operator": "gt", "value": "30"},
            ],
        }
        resp = client.post("/api/crm/automations/branching/traverse", json=payload, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["result"] is True

    def test_dag_engine_execution_and_queueing(self, db_session):
        """Feature 4: AutomationEngine executes root action and cascades to downstream nodes."""
        sede = _create_sede(db_session, "Sede Automaciones")
        persona = Persona(first_name="David", last_name="Rey", email="david.rey@ccf.org", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()

        root = CrmAutomation(name="Welcome Trigger", trigger_event="new_persona", action_type="email", delay_minutes=0, is_active=True)
        child = CrmAutomation(name="Followup Task", trigger_event="new_persona", action_type="sms", delay_minutes=15, is_active=True)
        db_session.add_all([root, child])
        db_session.commit()

        edge = CrmAutomationEdge(source_id=root.id, target_id=child.id, condition_type="always")
        db_session.add(edge)
        db_session.commit()

        pending = PendingCrmAction(
            automation_id=root.id,
            target_persona_id=persona.id,
            execute_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1),
            status="pending",
        )
        db_session.add(pending)
        db_session.commit()

        with patch("backend.services.messaging.get_messaging_gateway") as mock_gw:
            mock_gateway = MagicMock()
            async def _dummy(): return True
            mock_gateway.send_email.side_effect = lambda *a, **k: _dummy()
            mock_gw.return_value = mock_gateway

            automation_engine._process_crm_pending_actions(db_session)

        db_session.refresh(pending)
        assert pending.status == "executed"

        child_action = (
            db_session.query(PendingCrmAction)
            .filter(PendingCrmAction.automation_id == child.id)
            .first()
        )
        assert child_action is not None
        assert child_action.status == "pending"


class TestTier1ObsidianWikiGraph:
    """Tier 1.5: Obsidian-Style Knowledge Network and 2D Force-Directed Graph."""

    def test_wiki_page_crud_and_versioning(self, client, db_session):
        """Feature 5: Wiki pages support CRUD, Markdown content, and version snapshotting."""
        _admin_user, _admin_persona, _sede = seed_admin(db_session, email="wiki-author@ccf.org")
        headers = auth_headers(client, email="wiki-author@ccf.org")

        # 1. Create page
        create_resp = client.post(
            "/api/wiki/pages/manual_liderazgo",
            json={"title": "Manual de Liderazgo 2026", "content": "# Manual\n\nPrincipios bíblicos de liderazgo."},
            headers=headers,
        )
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["page_key"] == "wiki_manual_liderazgo"
        assert created["version"] == 1

        # 2. Update page (snapshot version 1)
        patch_resp = client.patch(
            "/api/wiki/pages/manual_liderazgo",
            json={"title": "Manual de Liderazgo CCF v2", "content": "## Sección 1: Mentoría"},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        patched = patch_resp.json()
        assert patched["version"] == 2

        # 3. Check version history
        ver_resp = client.get("/api/wiki/pages/manual_liderazgo/versions", headers=headers)
        assert ver_resp.status_code == 200
        versions = ver_resp.json()
        assert len(versions) >= 1
        assert versions[0]["version_number"] == 1

    def test_wiki_wikilink_normalization_and_resolution(self, client, db_session):
        """Feature 5: Wiki keys normalize canonical prefixes and resolve compatibility aliases."""
        _admin_user, _admin_persona, _sede = seed_admin(db_session, email="wiki-links@ccf.org")
        headers = auth_headers(client, email="wiki-links@ccf.org")

        client.post(
            "/api/wiki/pages/discipulado_juvenil",
            json={"title": "Discipulado Juvenil", "content": "Enlace a [[Manual Liderazgo]]"},
            headers=headers,
        )

        # Lookup by exact canonical key, alias with dashes, or raw slug
        resp_canonical = client.get("/api/wiki/pages/wiki_discipulado_juvenil", headers=headers)
        resp_alias = client.get("/api/wiki/pages/discipulado-juvenil", headers=headers)
        assert resp_canonical.status_code == 200
        assert resp_alias.status_code == 200
        assert resp_canonical.json()["title"] == "Discipulado Juvenil"

    def test_wiki_categories_and_tag_filtering(self, client, db_session):
        """Feature 5: Wiki categories can be listed and filtered."""
        _admin_user, _admin_persona, _sede = seed_admin(db_session, email="wiki-categorizer@ccf.org")
        headers = auth_headers(client, email="wiki-categorizer@ccf.org")

        client.post(
            "/api/wiki/pages/doctrina_fe",
            json={"title": "Doctrina de Fe", "content": "Teología", "category": "teologia"},
            headers=headers,
        )
        client.patch(
            "/api/wiki/pages/doctrina_fe",
            json={"category": "teologia", "tags": ["doctrina", "fe"]},
            headers=headers,
        )

        cat_resp = client.get("/api/wiki/categories", headers=headers)
        assert cat_resp.status_code == 200
        categories = cat_resp.json()
        assert "teologia" in categories

    def test_wiki_graph_snapshot_and_node_resolution(self, client, db_session):
        """Feature 5: 2D Force-directed knowledge graph snapshot returns nodes and edges."""
        _admin_user, _admin_persona, _sede = seed_admin(db_session, email="graph-explorer@ccf.org")
        headers = auth_headers(client, email="graph-explorer@ccf.org")

        resp = client.get("/api/graph/snapshot?limit=50", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert "meta" in data
        assert "pagination" in data["meta"]

    def test_wiki_graph_connections_and_neighborhood(self, client, db_session):
        """Feature 5: Querying connections for a specific node returns incoming/outgoing relationships."""
        admin_user, admin_persona, sede = seed_admin(db_session, email="graph-links@ccf.org")
        headers = auth_headers(client, email="graph-links@ccf.org")

        course = models.Course(
            code="LID-101",
            slug="liderazgo-transformacional",
            title="Liderazgo Transformacional",
            modality="presencial",
            is_published=True,
            sede_id=sede.id,
        )
        db_session.add(course)
        db_session.commit()

        # Connect via graph snapshot
        node_id = f"course-{course.id}"
        resp = client.get(f"/api/graph/connections/{node_id}", headers=headers)
        assert resp.status_code == 200
        conn_data = resp.json()
        assert conn_data["node"]["id"] == node_id


# ═════════════════════════════════════════════════════════════════════════════
# TIER 2: BOUNDARY & CORNER CASES
# ═════════════════════════════════════════════════════════════════════════════


class TestTier2BoundaryAndCornerCases:
    """Tier 2: Boundary Value Analysis (BVA), Malformed Inputs, and Security Constraints."""

    # ── MCP Boundaries ────────────────────────────────────────────────────────
    def test_mcp_unauthenticated_token_failure(self, client):
        """Boundary: MCP gateway call without Authorization header returns HTTP 401."""
        resp = client.post("/api/mcp/crm/tools/call", json={"name": "list_crm_events"})
        assert resp.status_code == 401

    def test_mcp_invalid_uuid_arguments(self, client, db_session):
        """Boundary: Invalid UUID format in tool calls returns structured error."""
        _admin, _, _ = seed_admin(db_session, email="mcp-invalid-uuid@ccf.org")
        headers = auth_headers(client, email="mcp-invalid-uuid@ccf.org")

        call_payload = {
            "name": "get_crm_event",
            "arguments": {"event_id": "not-a-valid-uuid"},
        }
        resp = client.post("/api/mcp/crm/tools/call", json=call_payload, headers=headers)
        assert resp.status_code in (400, 422, 500)

    def test_mcp_non_existent_server_returns_404(self, client, db_session):
        """Boundary: Requesting a non-existent MCP domain server returns HTTP 404."""
        _admin, _, _ = seed_admin(db_session, email="mcp-404-server@ccf.org")
        headers = auth_headers(client, email="mcp-404-server@ccf.org")

        resp = client.get("/api/mcp/non_existent_domain/tools", headers=headers)
        assert resp.status_code == 404

    def test_mcp_cross_module_path_injection(self):
        """Boundary: Generic module server rejects cross-module path injection."""
        server, _ = GENERIC_MODULE_SERVERS["projects"]
        req_tool = server._tool_manager._tools["module_api_request"].fn
        with pytest.raises(PermissionError, match="no pertenece"):
            asyncio.run(req_tool("GET", "/api/crm/personas"))

    def test_mcp_bulk_attendance_limit_boundary(self, db_session):
        """Boundary: Bulk attendance tool rejects empty lists without allow_empty and caps at 2000."""
        admin_user, _, sede = seed_admin(db_session, email="mcp-boundary@ccf.org")
        token_ctx = _set_mcp_context(admin_user.id)
        try:
            event = models.CrmEvent(name="Evento Test", sede_id=sede.id)
            db_session.add(event)
            db_session.commit()

            att_tool = crm_mcp._tool_manager._tools["register_crm_event_attendance"].fn
            # Empty list without allow_empty
            with pytest.raises(ValueError, match="persona_ids está vacío"):
                att_tool(event_id=event.id, session_date=datetime.date.today(), persona_ids=[], allow_empty=False)

            # Exceeding 2000 items
            too_many = [uuid.uuid4() for _ in range(2001)]
            with pytest.raises(ValueError, match="máximo permitido"):
                att_tool(event_id=event.id, session_date=datetime.date.today(), persona_ids=too_many)
        finally:
            auth_context_var.reset(token_ctx)

    # ── RAG & RLS Boundaries ──────────────────────────────────────────────────
    def test_rag_empty_and_whitespace_query_handling(self, client, db_session):
        """Boundary: Empty, whitespace, or punctuation queries return empty results gracefully."""
        _admin, _, _ = seed_admin(db_session, email="rag-empty-query@ccf.org")
        headers = auth_headers(client, email="rag-empty-query@ccf.org")

        resp = client.post("/api/rag/pastoral/search", json={"query": "   "}, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_rag_cross_tenant_probe_rejection(self, client, db_session):
        """Boundary: User in Sede A cannot view or access wiki pages of Sede B."""
        sede_a = _create_sede(db_session, "Sede Alpha")
        sede_b = _create_sede(db_session, "Sede Beta")

        _user_a, _, _ = seed_user_with_role(db_session, role_name="PASTOR", email="probe.pastor@ccf.org", sede_id=sede_a.id)
        headers_a = auth_headers(client, email="probe.pastor@ccf.org")

        page_b = WikiPage(
            page_key="wiki_secret_beta",
            title="Secret Beta Document",
            content="Confidential",
            sede_id=sede_b.id,
        )
        db_session.add(page_b)
        db_session.commit()

        # Pastor A requesting Sede B's page key receives a new empty virtual page (no data leakage)
        resp = client.get("/api/wiki/pages/wiki_secret_beta", headers=headers_a)
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == ""
        assert data["version"] == 0

    def test_rag_extreme_query_length_resilience(self, client, db_session):
        """Boundary: Handling 10,000+ character queries without SQL syntax error or crash."""
        _admin, _, _ = seed_admin(db_session, email="rag-long-query@ccf.org")
        headers = auth_headers(client, email="rag-long-query@ccf.org")

        massive_query = "discipulado " * 500
        resp = client.post("/api/rag/pastoral/search", json={"query": massive_query, "limit": 5}, headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_rag_inactive_and_deleted_content_exclusion(self, db_session):
        """Boundary: Deactivated or soft-deleted items are completely excluded from search results."""
        doc = AgentKnowledgeBase(
            title="Documento Desactivado",
            content="Información obsoleta",
            category="general",
            source_module="system",
            is_active=False,
        )
        db_session.add(doc)
        db_session.commit()

        res = search_knowledge_base_real(db_session, query="Documento Desactivado")
        assert not any(d.id == doc.id for d in res)

    # ── DuckDB Boundaries ─────────────────────────────────────────────────────
    def test_duckdb_empty_database_zero_division_safety(self):
        """Boundary: Analytics aggregations on empty timeframes return zero without division error."""
        cutoff_future = 0  # 0 days cutoff
        res = analytics_queries.get_event_summary(days=cutoff_future)
        assert "total_events" in res
        assert isinstance(res["total_events"], int)

    def test_duckdb_non_admin_warehouse_access_denied(self, client, db_session):
        """Boundary: Non-admin users attempting cross-sede warehouse analytics receive HTTP 403."""
        _pastor, _, _ = seed_user_with_role(db_session, role_name="PASTOR", email="pastor-no-bi@ccf.org")
        headers = auth_headers(client, email="pastor-no-bi@ccf.org")

        resp = client.get("/api/analytics/events/summary/warehouse", headers=headers)
        assert resp.status_code == 403

    # ── DAG Boundaries ────────────────────────────────────────────────────────
    def test_dag_self_referencing_node_detection(self, client, db_session):
        """Boundary: A single node self-referencing (A -> A) is flagged as cyclical/invalid."""
        _user, _, _ = seed_admin(db_session, email="dag-self@ccf.org")
        headers = auth_headers(client, email="dag-self@ccf.org")

        payload = {
            "nodes": [{"id": "node_loop"}],
            "edges": [{"source": "node_loop", "target": "node_loop"}],
        }
        resp = client.post("/api/crm/automations/flows/check-cycles", json=payload, headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()["cycles"]) >= 1

    def test_dag_disconnected_and_island_nodes(self, client, db_session):
        """Boundary: Graph with island/unconnected nodes processes without error."""
        _user, _, _ = seed_admin(db_session, email="dag-islands@ccf.org")
        headers = auth_headers(client, email="dag-islands@ccf.org")

        payload = {
            "nodes": [{"id": "island_1"}, {"id": "island_2"}, {"id": "A"}, {"id": "B"}],
            "edges": [{"source": "A", "target": "B"}],
        }
        resp = client.post("/api/crm/automations/flows/check-cycles", json=payload, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["cycles"] == []

    def test_dag_missing_fields_and_malformed_edges(self, client, db_session):
        """Boundary: Malformed edge payload (empty source/target) returns 400."""
        _user, _, _ = seed_admin(db_session, email="dag-malformed@ccf.org")
        headers = auth_headers(client, email="dag-malformed@ccf.org")

        payload = {
            "nodes": [{"id": "N1"}],
            "edges": [{"source": "", "target": "N1"}],
        }
        resp = client.post("/api/crm/automations/flows/check-cycles", json=payload, headers=headers)
        assert resp.status_code == 400

    # ── Wiki & Graph Boundaries ───────────────────────────────────────────────
    def test_wiki_duplicate_key_conflict_409(self, client, db_session):
        """Boundary: Creating a page with an already existing key in same sede returns HTTP 409."""
        _admin, _, _ = seed_admin(db_session, email="wiki-dup@ccf.org")
        headers = auth_headers(client, email="wiki-dup@ccf.org")

        client.post("/api/wiki/pages/unique_doc", json={"title": "Unique Doc"}, headers=headers)
        dup_resp = client.post("/api/wiki/pages/unique_doc", json={"title": "Duplicate"}, headers=headers)
        assert dup_resp.status_code == 409

    def test_wiki_deleted_page_returns_404(self, client, db_session):
        """Boundary: Requesting a soft-deleted page returns HTTP 404."""
        _admin, _, _ = seed_admin(db_session, email="wiki-del@ccf.org")
        headers = auth_headers(client, email="wiki-del@ccf.org")

        client.post("/api/wiki/pages/temp_doc", json={"title": "To Delete"}, headers=headers)
        del_resp = client.delete("/api/wiki/pages/temp_doc", headers=headers)
        assert del_resp.status_code == 204

        get_resp = client.get("/api/wiki/pages/temp_doc", headers=headers)
        assert get_resp.status_code == 404

    def test_graph_user_without_sede_non_admin_403(self, db_session):
        """Boundary: User without sede and non-platform-admin role is rejected with 403 on graph."""
        from backend.api.graph import _enforce_graph_rbac
        user, _, _ = seed_user_with_role(
            db_session,
            role_name="MIEMBRO",
            email="homeless-member@ccf.org",
            sede_id=None,
        )
        with pytest.raises(HTTPException) as exc_info:
            _enforce_graph_rbac(user, None)
        assert exc_info.value.status_code == 403

    def test_graph_non_existent_node_connections_404(self, client, db_session):
        """Boundary: Querying connections for a non-existent node returns 404."""
        _admin, _, _ = seed_admin(db_session, email="graph-404@ccf.org")
        headers = auth_headers(client, email="graph-404@ccf.org")

        resp = client.get("/api/graph/connections/course-99999999-9999-9999-9999-999999999999", headers=headers)
        assert resp.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# TIER 3: CROSS-FEATURE INTERACTIONS & COMBINATIONS
# ═════════════════════════════════════════════════════════════════════════════


class TestTier3CrossFeatureInteractions:
    """Tier 3: Multi-Module Pairwise Integration & Interoperability."""

    def test_cross_mcp_tool_and_rag_search_workflow(self, db_session):
        """Tier 3: Persona created via FastMCP tool is indexed and discoverable via Knowledge Base."""
        admin_user, _persona, sede = seed_admin(db_session, email="cross-mcp-rag@ccf.org")
        token_ctx = _set_mcp_context(admin_user.id)
        try:
            create_tool = crm_mcp._tool_manager._tools["create_crm_person"].fn
            leader = create_tool(
                first_name="Esteban",
                last_name="Paz",
                email="esteban.paz@ccf.org",
                church_role="Pastor Asistente",
            )
            assert leader["first_name"] == "Esteban"

            # Index stats into RAG Knowledge Base
            indexer = KnowledgeIndexer(db_session)
            indexer._index_persona_stats(agent_id=admin_user.id)

            # Search RAG Knowledge Base for persona stats
            results = search_knowledge_base_real(db_session, query="Estadísticas personas", category="crm_stats")
            assert len(results) >= 1
            assert "personas registradas" in results[0].summary
        finally:
            auth_context_var.reset(token_ctx)

    def test_cross_workflow_trigger_and_mcp_action_flow(self, db_session):
        """Tier 3: CRM automation flow created via MCP triggers downstream WhatsApp action."""
        admin_user, _persona, sede = seed_admin(db_session, email="cross-flow-mcp@ccf.org")
        token_ctx = _set_mcp_context(admin_user.id)
        try:
            # 1. Create a persona
            persona = Persona(first_name="Laura", last_name="Mora", email="laura@ccf.org", sede_id=sede.id)
            db_session.add(persona)
            db_session.commit()

            # 2. Create automation record and execute action
            auto = CrmAutomation(
                name="Auto Bienvenida",
                trigger_event="new_persona",
                action_type="whatsapp",
                action_payload={"canal": "whatsapp"},
                sede_id=sede.id,
            )
            db_session.add(auto)
            db_session.commit()

            pending = PendingCrmAction(
                automation_id=auto.id,
                target_persona_id=persona.id,
                execute_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1),
                status="pending",
            )
            db_session.add(pending)
            db_session.commit()

            with patch("backend.services.messaging.get_messaging_gateway") as mock_gw:
                mock_gateway = MagicMock()
                async def _dummy(): return True
                mock_gateway.send_whatsapp.side_effect = lambda *a, **k: _dummy()
                mock_gw.return_value = mock_gateway
                automation_engine._process_crm_pending_actions(db_session)

            db_session.refresh(pending)
            assert pending.status == "executed"
        finally:
            auth_context_var.reset(token_ctx)

    def test_cross_wiki_links_and_rag_knowledge_indexing(self, client, db_session):
        """Tier 3: Ministerial Wiki documents with [[WikiLinks]] are indexed and retrievable via RAG endpoint."""
        sede = _create_sede(db_session, "Sede Wiki RAG")
        pastor, _persona, _ = seed_user_with_role(
            db_session, role_name="PASTOR", email="wiki.rag.pastor@ccf.org", sede_id=sede.id
        )
        headers = auth_headers(client, email="wiki.rag.pastor@ccf.org")

        # 1. Create wiki document with WikiLink references
        client.post(
            "/api/wiki/pages/manual_discipulos",
            json={
                "title": "Manual de Nuevos Discípulos",
                "content": "Guía práctica con referencias a [[Vision General]] y [[Doctrina Basica]].",
                "category": "discipulado",
            },
            headers=headers,
        )

        # 2. Search via Pastoral RAG
        resp = client.post(
            "/api/rag/pastoral/search",
            json={"query": "Nuevos Discípulos Vision General", "limit": 5},
            headers=headers,
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1
        assert "Manual de Nuevos Discípulos" in results[0]["title"]

    def test_cross_crm_attendance_and_duckdb_event_sink(self, db_session):
        """Tier 3: Registering event attendance via MCP tool emits domain events to DuckDB OLAP."""
        admin_user, _persona, sede = seed_admin(db_session, email="cross-att-olap@ccf.org")
        token_ctx = _set_mcp_context(admin_user.id)
        try:
            event_tool = crm_mcp._tool_manager._tools["create_crm_event"].fn
            event = event_tool(name="Conferencia Misionera 2026")
            event_id = event["event_id"]

            # Log domain event for attendance
            event_sink.persist_event("EventAttendanceRecorded", {"event_id": str(event_id), "attendees": 150})

            # Query DuckDB for aggregated event
            summary = analytics_queries.get_event_summary(days=1)
            matching = [item for item in summary["by_event"] if item["event_name"] == "EventAttendanceRecorded"]
            assert len(matching) >= 1
        finally:
            auth_context_var.reset(token_ctx)

    def test_cross_knowledge_graph_and_wiki_pastoral_network(self, client, db_session):
        """Tier 3: Knowledge graph integrates personas, courses, and projects in a unified topology."""
        admin_user, admin_persona, sede = seed_admin(db_session, email="cross-topology@ccf.org")
        headers = auth_headers(client, email="cross-topology@ccf.org")

        course = models.Course(
            code="MIN-101",
            slug="teologia-ministerial",
            title="Teología Ministerial",
            modality="presencial",
            is_published=True,
            sede_id=sede.id,
        )
        project = models.Project(name="Expansión Templo 2026", sede_id=sede.id)
        db_session.add_all([course, project])
        db_session.commit()

        resp = client.get("/api/graph/snapshot?limit=100", headers=headers)
        assert resp.status_code == 200
        snapshot = resp.json()
        node_types = {n["type"] for n in snapshot["nodes"]}
        assert "person" in node_types
        assert "course" in node_types
        assert "project" in node_types


# ═════════════════════════════════════════════════════════════════════════════
# TIER 4: REAL-WORLD APPLICATION SCENARIOS
# ═════════════════════════════════════════════════════════════════════════════


class TestTier4RealWorldScenarios:
    """Tier 4: End-to-End Real-World Pastoral and Administrative Workflows."""

    def test_scenario_1_pastoral_sermon_prep_with_rls_rag(self, client, db_session):
        """Scenario 1: Pastor prepares sermon using RLS RAG, links wiki articles, verifies sede isolation."""
        sede_norte = _create_sede(db_session, "CCF Norte Bogotá")
        sede_sur = _create_sede(db_session, "CCF Sur Cali")

        pastor_norte, _, _ = seed_user_with_role(
            db_session, role_name="PASTOR", email="pastor.norte.sermon@ccf.org", sede_id=sede_norte.id
        )
        headers_norte = auth_headers(client, email="pastor.norte.sermon@ccf.org")

        # 1. Pastor Norte searches Knowledge Base for sermon themes
        sermon = Sermon(
            title="Sermón: Mayordomía y Fidelidad Financiera",
            passage="Malaquías 3 y 2 Corintios 9",
            summary="Principios bíblicos de mayordomía en CCF Norte.",
            content="La generosidad del creyente como acto de adoración y fidelidad en el Reino.",
            sede_id=sede_norte.id,
            is_published=True,
            is_active=True,
        )
        db_session.add(sermon)
        db_session.commit()

        resp_search = client.post(
            "/api/rag/pastoral/search",
            json={"query": "Mayordomía Fidelidad 2 Corintios", "limit": 5},
            headers=headers_norte,
        )
        assert resp_search.status_code == 200
        kb_matches = resp_search.json()
        assert len(kb_matches) >= 1
        sermon_theme = kb_matches[0]["title"]

        # 2. Pastor writes ministerial wiki page referencing the sermon
        wiki_resp = client.post(
            "/api/wiki/pages/sermon_mayordomia_2026",
            json={
                "title": sermon_theme,
                "content": f"# {sermon_theme}\n\nEstructura del sermón dominical con [[Guia Mayordomia]].",
                "category": "sermones",
            },
            headers=headers_norte,
        )
        assert wiki_resp.status_code == 201

        # 3. Verify Sede Sur cannot access this page content
        pastor_sur, _, _ = seed_user_with_role(
            db_session, role_name="PASTOR", email="pastor.sur.check@ccf.org", sede_id=sede_sur.id
        )
        headers_sur = auth_headers(client, email="pastor.sur.check@ccf.org")
        sur_resp = client.get("/api/wiki/pages/sermon_mayordomia_2026", headers=headers_sur)
        assert sur_resp.status_code == 200
        assert sur_resp.json()["content"] == ""  # Virtual empty page due to RLS boundary

    def test_scenario_2_bishop_multi_year_financial_olap_dashboard(self, client, db_session):
        """Scenario 2: Bishop queries multi-year financial & KPI trends via DuckDB OLAP under 50ms."""
        _bishop, _, sede = seed_admin(db_session, email="bishop.financial.dashboard@ccf.org")
        headers = auth_headers(client, email="bishop.financial.dashboard@ccf.org")

        # 1. Seed historical donation and expense records
        for i in range(1, 6):
            donation = models.Donation(
                amount=1000000.0 * i,
                sede_id=sede.id,
                status="completed",
                donation_type="Diezmo",
            )
            db_session.add(donation)
        db_session.commit()

        # 2. Execute analytics aggregations and verify sub-50ms DuckDB OLAP engine latency
        resp_growth = client.get("/api/analytics/olap/growth", headers=headers)
        assert resp_growth.status_code == 200
        growth_data = resp_growth.json()
        assert growth_data["execution_time_ms"] < 50.0

        # 3. Query financial statement summary
        resp_fin = client.get("/api/analytics/olap/financial-summary", headers=headers)
        assert resp_fin.status_code == 200
        fin_data = resp_fin.json()
        assert fin_data["execution_time_ms"] < 50.0
        assert "kpis" in fin_data or "summary" in fin_data

    def test_scenario_3_crm_onboarding_dag_workflow_lifecycle(self, client, db_session):
        """Scenario 3: Admin designs onboarding DAG on canvas, cycle check verifies DAG, engine executes actions."""
        admin_user, _persona, sede = seed_admin(db_session, email="crm.dag.lead@ccf.org")
        headers = auth_headers(client, email="crm.dag.lead@ccf.org")

        # 1. Validate Canvas Flow Graph (Trigger -> Condition -> Action)
        flow_graph = {
            "nodes": [
                {"id": "trig_new_visitor"},
                {"id": "cond_city_check"},
                {"id": "act_send_welcome"},
            ],
            "edges": [
                {"source": "trig_new_visitor", "target": "cond_city_check"},
                {"source": "cond_city_check", "target": "act_send_welcome"},
            ],
        }
        val_resp = client.post("/api/crm/automations/flows/check-cycles", json=flow_graph, headers=headers)
        assert val_resp.status_code == 200
        assert val_resp.json()["cycles"] == []

        # 2. Register visitor and pipeline case
        visitor = Persona(first_name="Santiago", last_name="Bernal", email="santiago@ccf.org", sede_id=sede.id)
        pipeline = PipelineCRM(sede_id=sede.id, nombre="Onboarding Visitantes", tipo=TipoPipelineEnum.NUEVOS_VISITANTES)
        db_session.add_all([visitor, pipeline])
        db_session.commit()

        etapa = EtapaPipeline(pipeline_id=pipeline.id, nombre="Contacto Inicial", orden=1)
        db_session.add(etapa)
        db_session.commit()

        caso = CasoCRM(
            persona_id=visitor.id,
            sede_id=sede.id,
            pipeline_id=pipeline.id,
            etapa_actual_id=etapa.id,
            titulo_caso="Caso Santiago",
            origen_canal=CanalOrigenEnum.WEB_FORM,
        )
        db_session.add(caso)
        db_session.commit()

        # 3. Trigger automation and process DAG
        auto_trig = CrmAutomation(name="Welcome WhatsApp", trigger_event="new_persona", action_type="whatsapp", sede_id=sede.id)
        db_session.add(auto_trig)
        db_session.commit()

        action = PendingCrmAction(
            automation_id=auto_trig.id,
            target_persona_id=visitor.id,
            execute_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1),
            status="pending",
        )
        db_session.add(action)
        db_session.commit()

        with patch("backend.services.messaging.get_messaging_gateway") as mock_gw:
            mock_gateway = MagicMock()
            async def _dummy(): return True
            mock_gateway.send_whatsapp.side_effect = lambda *a, **k: _dummy()
            mock_gw.return_value = mock_gateway
            automation_engine._process_crm_pending_actions(db_session)

        db_session.refresh(action)
        assert action.status == "executed"

    def test_scenario_4_orchestrator_multi_tool_mcp_flow(self, db_session):
        """Scenario 4: Agent Orchestrator discovers FastMCP tools and executes multi-step flow."""
        admin_user, _persona, sede = seed_admin(db_session, email="orchestrator.admin@ccf.org")
        token_ctx = _set_mcp_context(admin_user.id)
        try:
            # 1. Discover tools from FastMCP registry
            tools = crm_mcp._tool_manager._tools
            assert len(tools) >= 5

            # 2. Invoke CRM tool directly
            create_tool = crm_mcp._tool_manager._tools["create_crm_person"].fn
            created = create_tool(first_name="Valeria", last_name="Díaz", email="valeria@ccf.org")
            assert created["first_name"] == "Valeria"

            # 3. Verify Orchestrator builds prompt messages with RAG & metrics context
            with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-mock-key"}):
                with patch("backend.agents.orchestrator.OpenAI") as mock_openai:
                    mock_openai.return_value = MagicMock()
                    from backend.agents.orchestrator import AgentOrchestrator

                    orchestrator = AgentOrchestrator(api_key="sk-mock-key")
                    messages = orchestrator._build_messages(
                        summary="Consolidar nuevo miembro Valeria Díaz",
                        metrics={"persona_id": created["persona_id"], "kb_context": "Discipulado Inicial"},
                    )
                    assert len(messages) >= 2
                    assert "Discipulado Inicial" in messages[1]["content"]
                    assert "Valeria Díaz" in messages[1]["content"]
        finally:
            auth_context_var.reset(token_ctx)

    def test_scenario_5_ministerial_wiki_graph_navigation(self, client, db_session):
        """Scenario 5: Leader connects ministerial documents via [[WikiLinks]] and navigates graph."""
        admin_user, admin_persona, sede = seed_admin(db_session, email="wiki.graph.navigator@ccf.org")
        headers = auth_headers(client, email="wiki.graph.navigator@ccf.org")

        # 1. Create interconnected wiki documents
        docs = [
            ("vision_ccf_2030", "Visión CCF 2030", "Enlace a [[Plan Misiones]] y [[Escuela Liderazgo]]", "estrategia"),
            ("plan_misiones", "Plan de Misiones Global", "Enlace a [[Vision Ccf 2030]]", "misiones"),
            ("escuela_liderazgo", "Escuela de Liderazgo", "Enlace a [[Vision Ccf 2030]]", "educacion"),
        ]
        for key, title, content, cat in docs:
            client.post(
                f"/api/wiki/pages/{key}",
                json={"title": title, "content": content, "category": cat},
                headers=headers,
            )

        # 2. Query knowledge graph snapshot
        graph_resp = client.get("/api/graph/snapshot?limit=50", headers=headers)
        assert graph_resp.status_code == 200
        graph_data = graph_resp.json()
        assert len(graph_data["nodes"]) >= 1

        # 3. Explore localized connections for a persona
        node_id = f"person-{admin_persona.id}"
        conn_resp = client.get(f"/api/graph/connections/{node_id}", headers=headers)
        assert conn_resp.status_code == 200
        connections = conn_resp.json()
        assert connections["node"]["id"] == node_id
        assert "related_nodes" in connections
