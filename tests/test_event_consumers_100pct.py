"""Tests exhaustivos y estructurales para backend/services/event_consumers.py (100% Cobertura)."""

import pytest
from unittest.mock import MagicMock, patch

from backend.services.event_consumers import (
    EventConsumer,
    IntelligenceConsumer,
    GraphUpdateConsumer,
    KBIndexConsumer,
    register_consumer,
    dispatch_event,
    register_all_consumers,
    _event_registry,
)


class CustomConsumer(EventConsumer):
    @property
    def subscribed_events(self):
        return ["custom_event"]

    def handle_custom_event(self, payload):
        if payload.get("raise_err"):
            raise ValueError("Error intencional en consumer")
        payload["processed"] = True


class TestEventConsumers100Pct:

    def test_base_event_consumer(self):
        base = EventConsumer()
        assert base.subscribed_events == []
        # Calling handle on base with unhandled event should do nothing
        base.handle("unknown_event", {})

    def test_handle_exception_logging(self):
        consumer = CustomConsumer()
        # Should catch exception internally and log it without crashing
        consumer.handle("custom_event", {"raise_err": True})

        payload = {"raise_err": False}
        consumer.handle("custom_event", payload)
        assert payload["processed"] is True

    @patch("backend.core.database.SessionLocal")
    @patch("backend.crud.agents.create_agent_insight")
    def test_intelligence_consumer_persona_registered(self, mock_create_insight, mock_session):
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        consumer = IntelligenceConsumer()
        assert "persona_registered" in consumer.subscribed_events

        payload = {"name": "Juan Perez", "church_role": "lider"}
        consumer.handle("persona_registered", payload)

        mock_create_insight.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("backend.core.database.SessionLocal")
    @patch("backend.services.knowledge_base.KnowledgeIndexer")
    def test_intelligence_consumer_enrollment_created(self, mock_indexer_cls, mock_session):
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_indexer = MagicMock()
        mock_indexer_cls.return_value = mock_indexer

        consumer = IntelligenceConsumer()
        assert "enrollment_created" in consumer.subscribed_events

        consumer.handle("enrollment_created", {})

        mock_indexer._index_courses.assert_called_once_with(agent_id=None)
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("backend.core.database.SessionLocal")
    @patch("backend.crud.agents.create_agent_task")
    @patch("backend.crud.agents.create_agent_insight")
    def test_intelligence_consumer_task_overdue(self, mock_create_insight, mock_create_task, mock_session):
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        consumer = IntelligenceConsumer()
        assert "task_overdue" in consumer.subscribed_events

        payload = {"title": "Revisar reporte", "description": "Pendiente desde ayer"}
        consumer.handle("task_overdue", payload)

        mock_create_insight.assert_called_once()
        mock_create_task.assert_called_once()
        mock_db.close.assert_called_once()

    def test_graph_update_consumer(self):
        consumer = GraphUpdateConsumer()
        assert "persona_status_changed" in consumer.subscribed_events
        assert "spiritual_stage_transition" in consumer.subscribed_events

        # These handle methods issue log.info statements
        consumer.handle("persona_status_changed", {"persona_id": "123"})
        consumer.handle("spiritual_stage_transition", {
            "from_stage": "believer",
            "to_stage": "disciple",
            "agent_id": "agent-456",
        })

    @patch("backend.core.database.SessionLocal")
    @patch("backend.services.knowledge_base.KnowledgeIndexer")
    def test_kb_index_consumer(self, mock_indexer_cls, mock_session):
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_indexer = MagicMock()
        mock_indexer_cls.return_value = mock_indexer

        consumer = KBIndexConsumer()
        assert "course_created" in consumer.subscribed_events
        assert "project_created" in consumer.subscribed_events
        assert "strategy_created" in consumer.subscribed_events

        consumer.handle("course_created", {})
        mock_indexer._index_courses.assert_called_once_with(agent_id=None)

        consumer.handle("project_created", {})
        mock_indexer._index_projects.assert_called_once_with(agent_id=None)

        consumer.handle("strategy_created", {})
        mock_indexer._index_evangelism.assert_called_once_with(agent_id=None)

        assert mock_db.commit.call_count == 3
        assert mock_db.close.call_count == 3

    def test_dispatch_and_register_all_consumers(self):
        _event_registry.clear()
        reg = register_all_consumers()
        assert "persona_registered" in reg
        assert "course_created" in reg

        with patch.object(IntelligenceConsumer, "handle") as mock_handle:
            # We construct a new consumer to test register_consumer
            c = IntelligenceConsumer()
            register_consumer(c)
            dispatch_event("persona_registered", {"name": "Test"})
            mock_handle.assert_called()
