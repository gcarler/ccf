"""
Coverage tests for services requiring DB fixtures.
knowledge_base, conversation_memory, cms crud.
"""
import uuid

import pytest

from backend import models
from backend.models_knowledge_base import AgentKnowledgeBase
from backend.services.knowledge_base import KnowledgeIndexer
from backend.services.image_optimizer import ImageOptimizer
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    return {"db": db_session, "admin": admin, "persona": persona, "sede": sede}


class TestKnowledgeIndexerDB:
    def test_init_with_db(self, full):
        indexer = KnowledgeIndexer(full["db"])
        assert indexer is not None

    def test_has_table_personas(self, full):
        indexer = KnowledgeIndexer(full["db"])
        # SQLite in test — has_table may behave differently
        result = indexer._has_table("personas")
        assert isinstance(result, bool)

    def test_rebuild_all_empty_db(self, full):
        indexer = KnowledgeIndexer(full["db"])
        stats = indexer.rebuild_all()
        assert isinstance(stats, dict)
        assert "courses" in stats


class TestImageOptimizer:
    def test_init(self):
        opt = ImageOptimizer()
        assert opt is not None


class TestCmsBase:
    def test_announcement_model(self, full):
        ann = models.Announcement(
            title="Test Announcement",
            content="Content for coverage",
            created_by_persona_id=full["persona"].id,
            sede_id=full["sede"].id,
        )
        full["db"].add(ann)
        full["db"].commit()
        assert ann.id is not None


class TestDonationModel:
    def test_create_donation_model(self, full):
        donation = models.Donation(
            amount=10000,
            donation_type="Diezmo",
            donor_name="Coverage Test",
            persona_id=full["persona"].id,
            sede_id=full["sede"].id,
        )
        full["db"].add(donation)
        full["db"].commit()
        assert donation.id is not None


