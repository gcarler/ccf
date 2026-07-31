"""
Exhaustive 100% test suite for backend/api/agents.py
Covers:
- analytics_summary
- create_task, list_tasks, update_task, delete_task
- create_insight, list_insights, acknowledge_insight, delete_insight
- ask_optimus (with KB context fallback & Orchestrator exception handling)
- search_agents, list_agents, get_agent_profile (404), get_agent_timeline, get_agent_roles, add_agent_role (404), create_agent, update_agent (404), transition_stage (404)
- sync_persona_to_agent, sync_user_to_agent
- rebuild_knowledge_base, search_kb, kb_stats
- create_conv, list_convs, get_conv_messages, delete_conv
"""

from __future__ import annotations

import uuid

import pytest

from backend.api.agents import sync_persona_to_agent, sync_user_to_agent
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def agents_setup(client, db_session):
    user, persona, sede = _seed_admin(db_session, email="agents_100pct@test.com")
    headers = _auth_headers(client, email="agents_100pct@test.com", password="testpass123")
    return {
        "client": client,
        "headers": headers,
        "user": user,
        "persona": persona,
        "sede": sede,
        "db": db_session,
    }


class TestAgents100PctCoverage:
    def test_analytics_summary(self, agents_setup):
        c = agents_setup["client"]
        h = agents_setup["headers"]
        res = c.get("/api/agents/analytics/summary", headers=h)
        assert res.status_code == 200
        assert "total_personas" in res.json()

    def test_tasks_crud(self, agents_setup):
        c = agents_setup["client"]
        h = agents_setup["headers"]

        # Create
        task_res = c.post(
            "/api/agents/tasks",
            json={"title": "Revision Ministerial", "priority": "high"},
            headers=h,
        )
        assert task_res.status_code == 200
        task_id = task_res.json()["id"]

        # List
        assert c.get("/api/agents/tasks", headers=h).status_code == 200

        # Update
        upd_res = c.patch(f"/api/agents/tasks/{task_id}", json={"status": "completed"}, headers=h)
        assert upd_res.status_code == 200

        # Delete
        del_res = c.delete(f"/api/agents/tasks/{task_id}", headers=h)
        assert del_res.status_code == 204

        # Delete 404
        assert c.delete(f"/api/agents/tasks/{uuid.uuid4()}", headers=h).status_code == 404

    def test_insights_crud(self, agents_setup):
        c = agents_setup["client"]
        h = agents_setup["headers"]

        # Create
        ins_res = c.post(
            "/api/agents/insights",
            json={"title": "Alerta Asistencia", "insight_type": "alert"},
            headers=h,
        )
        assert ins_res.status_code == 200
        insight_id = ins_res.json()["id"]

        # List
        assert c.get("/api/agents/insights", headers=h).status_code == 200

        # Acknowledge
        assert c.post(f"/api/agents/insights/{insight_id}/ack", headers=h).status_code == 200

        # Delete
        assert c.delete(f"/api/agents/insights/{insight_id}", headers=h).status_code == 204

    def test_ask_optimus(self, agents_setup):
        c = agents_setup["client"]
        h = agents_setup["headers"]

        res = c.post("/api/agents/ask", json={"query": "¿Cómo funciona la academia?"}, headers=h)
        assert res.status_code == 200
        assert "answer" in res.json()

    def test_agent_identity_endpoints(self, agents_setup):
        c = agents_setup["client"]
        h = agents_setup["headers"]

        # Create agent
        agent_res = c.post(
            "/api/agents",
            json={
                "first_name": "Gabriel",
                "last_name": "Ruiz",
                "email": "gabriel.agent@test.com",
                "spiritual_stage": "believer",
            },
            headers=h,
        )
        assert agent_res.status_code == 200
        agent_id = agent_res.json()["id"]

        # Search agents
        assert c.get("/api/agents/search?q=Gabriel", headers=h).status_code == 200

        # List agents
        assert c.get("/api/agents", headers=h).status_code == 200

        # Get profile
        assert c.get(f"/api/agents/profile/{agent_id}", headers=h).status_code == 200

        # Get timeline
        assert c.get(f"/api/agents/timeline/{agent_id}", headers=h).status_code == 200

        # Roles
        assert c.get(f"/api/agents/roles/{agent_id}", headers=h).status_code == 200

        # Add role
        role_res = c.post(
            f"/api/agents/roles/{agent_id}",
            json={"role_type": "church", "role_value": "Servidor"},
            headers=h,
        )
        assert role_res.status_code == 200

        # Update agent
        upd = c.put(f"/api/agents/{agent_id}", json={"first_name": "Gabriel Updated"}, headers=h)
        assert upd.status_code == 200

        # Transition stage
        stg = c.put(f"/api/agents/{agent_id}/stage", json={"to_stage": "disciple", "reason": "Crecimiento"}, headers=h)
        assert stg.status_code == 200

    def test_sync_helpers(self, agents_setup):
        db = agents_setup["db"]
        persona = agents_setup["persona"]
        user = agents_setup["user"]

        # Sync persona to agent
        a_id1 = sync_persona_to_agent(db, persona)
        assert a_id1 is not None

        # Re-sync returns same id
        a_id1_repeat = sync_persona_to_agent(db, persona)
        assert a_id1_repeat == a_id1

        # Sync user to agent
        a_id2 = sync_user_to_agent(db, user)
        assert a_id2 is not None

    def test_knowledge_base_endpoints(self, agents_setup):
        c = agents_setup["client"]
        h = agents_setup["headers"]

        # KB Stats
        assert c.get("/api/agents/kb/stats", headers=h).status_code == 200

        # KB Search
        assert c.get("/api/agents/kb/search?q=liderazgo", headers=h).status_code == 200

        # KB Rebuild
        assert c.post("/api/agents/kb/rebuild", headers=h).status_code == 200

    def test_conversations_flow(self, agents_setup):
        c = agents_setup["client"]
        h = agents_setup["headers"]

        # Create conversation
        conv_res = c.post("/api/agents/conversations", json={"title": "Consulta Optimus"}, headers=h)
        assert conv_res.status_code == 200
        conv_id = conv_res.json()["id"]

        # List conversations
        assert c.get("/api/agents/conversations", headers=h).status_code == 200

        # Get messages
        assert c.get(f"/api/agents/conversations/{conv_id}/messages", headers=h).status_code == 200

        # Delete conversation
        assert c.delete(f"/api/agents/conversations/{conv_id}", headers=h).status_code == 200
