"""
Coverage tests for backend services.
"""
import pytest

from backend import models
from backend.services.intelligence import IntelligenceMESH
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    return {"db": db_session, "admin": admin, "persona": persona, "sede": sede}


class TestIntelligenceService:
    def test_analyze_academy_performance(self, full):
        insights = IntelligenceMESH.analyze_academy_performance(full["db"])
        assert isinstance(insights, list)

    def test_analyze_project_health(self, full):
        insights = IntelligenceMESH.analyze_project_health(full["db"])
        assert isinstance(insights, list)

    def test_analyze_pastoral_care(self, full):
        insights = IntelligenceMESH.analyze_pastoral_care(full["db"])
        assert isinstance(insights, list)


class TestAgentInsightModel:
    def test_create_agent_insight(self, full):
        insight = models.AgentInsight(
            title="Test",
            insight_type="observation",
            insight_payload={"msg": "hello"},
        )
        full["db"].add(insight)
        full["db"].commit()
        assert insight.id is not None
