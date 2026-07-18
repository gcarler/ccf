"""
Additional coverage tests — round 2 for services with 0-30%.
"""
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from backend import models
from backend.services.conversation_memory import (
    create_conversation,
    get_user_conversations,
    save_conversation_turn,
)
from backend.services.email_templates import render_email
from backend.services.knowledge_graph import (
    _has_model,
    _person_nodes,
    _course_nodes,
)
from backend.services.task_notifications import notify_task_assigned, _display_name, _format_due_date
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    return {"db": db_session, "admin": admin, "persona": persona, "sede": sede}


class TestEmailTemplates:
    def test_render_email_returns_str(self):
        r = render_email("body", "title")
        assert isinstance(r, str)

    def test_render_email_empty_body(self):
        r = render_email("", "")
        assert isinstance(r, str)


class TestKnowledgeGraph:
    def test_has_model_checks_table(self, full):
        result = _has_model("personas")
        assert isinstance(result, bool)

    def test_person_nodes_returns_list(self, full):
        nodes = _person_nodes(full["db"], 5, full["sede"].id)
        assert isinstance(nodes, list)

    def test_course_nodes_returns_list(self, full):
        nodes = _course_nodes(full["db"], 5, full["sede"].id)
        assert isinstance(nodes, list)
