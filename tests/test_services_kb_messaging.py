"""Tests for the Knowledge Base service (knowledge_base.py).

Covers KnowledgeIndexer, search_knowledge_base_real, and edge cases.
"""
from __future__ import annotations

import asyncio
import uuid
from unittest.mock import patch

from backend.models_knowledge_base import AgentKnowledgeBase
from backend.models_crm import Persona
from backend.models_academy_core import Course
from backend.models_evangelism import EstrategiaEvangelismo
from backend.models_projects import Project
from backend.models_ops import SystemVariable
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def _ensure_kb_entry(db_session, **overrides):
    """Helper to create a KB entry."""
    entry = AgentKnowledgeBase(
        title=overrides.get("title", "Test Doc"),
        content=overrides.get("content", "Test content for knowledge base"),
        summary=overrides.get("summary", "Test summary"),
        category=overrides.get("category", "test"),
        source_module=overrides.get("source_module", "test"),
        source_id=overrides.get("source_id", "test-1"),
        source_url=overrides.get("source_url", "/test"),
        is_active=overrides.get("is_active", True),
        relevance_score=overrides.get("relevance_score", 1.0),
    )
    db_session.add(entry)
    db_session.commit()
    return entry


class TestKnowledgeIndexer:
    """Tests for KnowledgeIndexer class."""

    def _ensure_sede(self, db_session):
        """Create a sede for tests that need it."""
        from backend.models_evangelism import Sede
        s = Sede(id=uuid.uuid4(), nombre="Test Sede", ciudad="Bogota", es_activa=True)
        db_session.add(s)
        db_session.commit()
        return s

    def test_has_table_false(self, db_session):
        """_has_table returns False for non-existent tables."""
        from backend.services.knowledge_base import KnowledgeIndexer

        indexer = KnowledgeIndexer(db_session)
        assert indexer._has_table("nonexistent_table_xyz") is False

    def test_has_table_true(self, db_session):
        """_has_table returns True for existing tables."""
        from backend.services.knowledge_base import KnowledgeIndexer

        indexer = KnowledgeIndexer(db_session)
        assert indexer._has_table("wiki_pages") is True

    def test_rebuild_all_empty(self, db_session):
        """rebuild_all with no data returns zero stats."""
        from backend.services.knowledge_base import KnowledgeIndexer

        indexer = KnowledgeIndexer(db_session)
        stats = indexer.rebuild_all(indexed_by_agent_id=uuid.uuid4())
        assert isinstance(stats, dict)
        for k in ("courses", "strategies", "projects", "personas_stats", "system_vars"):
            assert k in stats

    def test_index_courses(self, db_session):
        """_index_courses must index published courses."""
        from backend.services.knowledge_base import KnowledgeIndexer

        course = Course(
            id=uuid.uuid4(), code="TEST-001", title="Test Course", description="A test course",
            modality="online", duration_hours=10, is_published=True, is_self_paced=True,
            xp_per_lesson=100,
        )
        db_session.add(course)
        db_session.commit()

        indexer = KnowledgeIndexer(db_session)
        count = indexer._index_courses(None)
        assert count == 1

        entry = db_session.query(AgentKnowledgeBase).filter(
            AgentKnowledgeBase.source_module == "academy"
        ).first()
        assert entry is not None
        assert "Test Course" in entry.title
        assert entry.is_active is True

    def test_index_courses_skipped_when_table_missing(self, db_session):
        """_index_courses returns 0 when academy_courses table doesn't exist."""
        from backend.services.knowledge_base import KnowledgeIndexer

        indexer = KnowledgeIndexer(db_session)
        with patch.object(indexer, "_has_table", return_value=False):
            count = indexer._index_courses(None)
        assert count == 0

    def test_index_projects(self, db_session):
        """_index_projects must index active/planning projects."""
        from backend.services.knowledge_base import KnowledgeIndexer

        project = Project(
            id=uuid.uuid4(), title="Test Project", description="A test project",
            status="active",
        )
        db_session.add(project)
        db_session.commit()

        indexer = KnowledgeIndexer(db_session)
        count = indexer._index_projects(None)
        assert count == 1

    def test_index_persona_stats(self, db_session):
        """_index_persona_stats must create a KB entry with role distribution."""
        from backend.services.knowledge_base import KnowledgeIndexer

        p = Persona(id=uuid.uuid4(), first_name="Stats", last_name="Test", church_role="LIDER")
        db_session.add(p)
        db_session.commit()

        indexer = KnowledgeIndexer(db_session)
        count = indexer._index_persona_stats(None)
        assert count == 1
        entry = db_session.query(AgentKnowledgeBase).filter(
            AgentKnowledgeBase.category == "crm_stats"
        ).first()
        assert entry is not None
        assert "LIDER" in entry.content

    def test_index_evangelism(self, db_session):
        """_index_evangelism must index active strategies."""
        from backend.services.knowledge_base import KnowledgeIndexer
        from backend.models_evangelism import CategoriaEstrategia

        sede = self._ensure_sede(db_session)
        cat = CategoriaEstrategia(id=uuid.uuid4(), nombre="Test Cat")
        db_session.add(cat)
        db_session.flush()
        strategy = EstrategiaEvangelismo(
            id=uuid.uuid4(), name="Test Strategy", description="A strategy",
            activa=True, sede_id=sede.id, categoria_id=cat.id,
        )
        db_session.add(strategy)
        db_session.commit()

        indexer = KnowledgeIndexer(db_session)
        count = indexer._index_evangelism(None)
        assert count == 1

    def test_index_system_vars(self, db_session):
        """_index_system_vars must index system variables."""
        from backend.services.knowledge_base import KnowledgeIndexer

        var = SystemVariable(key="test_key", value="test_value")
        db_session.add(var)
        db_session.commit()

        indexer = KnowledgeIndexer(db_session)
        count = indexer._index_system_vars(None)
        assert count == 1
        entry = db_session.query(AgentKnowledgeBase).filter(
            AgentKnowledgeBase.category == "system"
        ).first()
        assert entry is not None
        assert "test_key" in entry.content

    def test_upsert_kb_existing_updates(self, db_session):
        """_upsert_kb must update existing entries."""
        from backend.services.knowledge_base import KnowledgeIndexer

        entry = AgentKnowledgeBase(
            title="Original Title", content="old", source_module="test",
            source_id="test-1", is_active=False, category="test",
        )
        db_session.add(entry)
        db_session.commit()

        indexer = KnowledgeIndexer(db_session)
        indexer._upsert_kb(
            title="Original Title", content="updated content",
            source_module="test", source_id="test-1",
            summary="new summary", category="test", indexed_by=None,
        )
        db_session.commit()
        db_session.refresh(entry)
        assert entry.content == "updated content"
        assert entry.is_active is True


class TestSearchKnowledgeBaseReal:
    """Tests for search_knowledge_base_real function."""

    def test_empty_query_returns_empty(self, db_session):
        """Empty or whitespace-only query must return []."""
        from backend.services.knowledge_base import search_knowledge_base_real

        assert search_knowledge_base_real(db_session, "") == []
        assert search_knowledge_base_real(db_session, "   ") == []

    def test_no_results_returns_empty(self, db_session):
        """Query with no matches returns []."""
        from backend.services.knowledge_base import search_knowledge_base_real

        assert search_knowledge_base_real(db_session, "nonexistentxyz123") == []

    def test_search_by_title(self, db_session):
        """Search must find entries by title."""
        from backend.services.knowledge_base import search_knowledge_base_real

        _ensure_kb_entry(db_session, title="Pastoral Care Guide", category="pastoral")
        _ensure_kb_entry(db_session, title="Finance Manual", category="finance")

        results = search_knowledge_base_real(db_session, "pastoral")
        assert len(results) == 1
        assert results[0].title == "Pastoral Care Guide"

    def test_search_by_content(self, db_session):
        """Search must find entries by content."""
        from backend.services.knowledge_base import search_knowledge_base_real

        _ensure_kb_entry(db_session, title="Doc A", content="How to manage volunteers in the church")
        results = search_knowledge_base_real(db_session, "volunteers")
        assert len(results) == 1

    def test_search_by_summary(self, db_session):
        """Search must find entries by summary."""
        from backend.services.knowledge_base import search_knowledge_base_real

        _ensure_kb_entry(db_session, title="Doc B", content="x", summary="Important guidelines for worship")
        results = search_knowledge_base_real(db_session, "worship")
        assert len(results) == 1

    def test_filter_by_category(self, db_session):
        """Category filter must narrow results."""
        from backend.services.knowledge_base import search_knowledge_base_real

        _ensure_kb_entry(db_session, title="Pastoral Doc", category="pastoral", content="guidelines")
        _ensure_kb_entry(db_session, title="Academy Doc", category="academy", content="guidelines")

        results = search_knowledge_base_real(db_session, "guidelines", category="pastoral")
        assert len(results) == 1
        assert results[0].category == "pastoral"

    def test_inactive_entries_are_excluded(self, db_session):
        """is_active=False entries must not appear in results."""
        from backend.services.knowledge_base import search_knowledge_base_real

        _ensure_kb_entry(db_session, title="Active Doc", content="findable", is_active=True)
        _ensure_kb_entry(db_session, title="Inactive Doc", content="findable", is_active=False)

        results = search_knowledge_base_real(db_session, "findable")
        assert len(results) == 1
        assert results[0].title == "Active Doc"

    def test_top_k_limits_results(self, db_session):
        """top_k parameter must limit result count."""
        from backend.services.knowledge_base import search_knowledge_base_real

        for i in range(5):
            _ensure_kb_entry(db_session, title=f"Doc {i}", content="searchable content", category="test")

        results = search_knowledge_base_real(db_session, "searchable", top_k=2)
        assert len(results) == 2

    def test_relevance_ordering(self, db_session):
        """Results must be ordered by relevance_score desc, then updated_at desc."""
        from backend.services.knowledge_base import search_knowledge_base_real
        from datetime import datetime, timezone

        _ensure_kb_entry(db_session, title="High Relevance", content="term", relevance_score=5.0)
        _ensure_kb_entry(db_session, title="Low Relevance", content="term", relevance_score=1.0)

        results = search_knowledge_base_real(db_session, "term")
        assert len(results) == 2
        assert results[0].title == "High Relevance"
        assert results[1].title == "Low Relevance"

    def test_multi_term_search(self, db_session):
        """Search with multiple terms requires ALL terms in one doc."""
        from backend.services.knowledge_base import search_knowledge_base_real

        _ensure_kb_entry(db_session, title="Church Growth", content="growing the church community")
        _ensure_kb_entry(db_session, title="Finances", content="managing church funds")

        # "growing" only appears in the first doc
        results = search_knowledge_base_real(db_session, "growing community")
        assert len(results) == 1
        assert results[0].title == "Church Growth"


class TestMessagingGateway:
    """Tests for MessagingGateway class."""

    def test_send_whatsapp_success(self, db_session):
        """send_whatsapp must create a CommunicationLog entry."""
        from backend.services.messaging import MessagingGateway

        gateway = MessagingGateway()
        p = Persona(id=uuid.uuid4(), first_name="Test", last_name="User", phone="+573001234567")
        db_session.add(p)
        db_session.commit()

        log = asyncio.run(gateway.send_whatsapp(
            db_session,
            persona_id=str(p.id),
            content="Test WhatsApp message",
            leader_id=None,
        ))
        assert log is not None
        assert log.channel == "WhatsApp"
        assert log.outcome == "sent"

    def test_send_whatsapp_no_phone_raises(self, db_session):
        """send_whatsapp must fail if persona has no phone."""
        from backend.services.messaging import MessagingGateway

        gateway = MessagingGateway()
        p = Persona(id=uuid.uuid4(), first_name="Test", last_name="User", phone=None)
        db_session.add(p)
        db_session.commit()

        try:
            asyncio.run(gateway.send_whatsapp(
                db_session,
                persona_id=str(p.id),
                content="Test",
                leader_id=None,
            ))
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "sin numero de telefono" in str(e)

    def test_send_sms_success(self, db_session):
        """send_sms must create a CommunicationLog entry."""
        from backend.services.messaging import MessagingGateway

        gateway = MessagingGateway()
        p = Persona(id=uuid.uuid4(), first_name="Test", last_name="User", phone="+573001234567")
        db_session.add(p)
        db_session.commit()

        log = asyncio.run(gateway.send_sms(
            db_session,
            persona_id=str(p.id),
            content="Test SMS",
            leader_id=None,
        ))
        assert log is not None
        assert log.channel == "SMS"

    def test_send_sms_no_phone_raises(self, db_session):
        """send_sms must fail if persona has no phone."""
        from backend.services.messaging import MessagingGateway

        gateway = MessagingGateway()
        p = Persona(id=uuid.uuid4(), first_name="Test", last_name="User", phone=None)
        db_session.add(p)
        db_session.commit()

        try:
            asyncio.run(gateway.send_sms(
                db_session,
                persona_id=str(p.id),
                content="Test",
                leader_id=None,
            ))
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "sin numero celular" in str(e)

    def test_send_email_no_smtp_config(self, db_session):
        """Without SMTP config, send_email must log with PENDING_SMTP_CONFIG."""
        from backend.services.messaging import MessagingGateway
        from backend.services.messaging_outcomes import CommunicationOutcome
        from backend.core.config import get_settings

        gateway = MessagingGateway()
        p = Persona(id=uuid.uuid4(), first_name="Test", last_name="User", email="test@example.com")
        db_session.add(p)
        db_session.commit()

        # Clear SMTP settings for this test
        settings = get_settings()
        with patch.object(settings, "smtp_host", ""):
            with patch.object(settings, "smtp_user", ""):
                with patch.object(settings, "smtp_password", ""):
                    log = asyncio.run(gateway.send_email(
                        db_session,
                        persona_id=str(p.id),
                        content="Test email",
                        leader_id=None,
                    ))
        assert log is not None
        assert log.channel == "Email"
        assert log.outcome == CommunicationOutcome.PENDING_SMTP_CONFIG.value

    def test_send_email_with_html(self, db_session):
        """send_email with html param must log successfully."""
        from backend.services.messaging import MessagingGateway
        from backend.core.config import get_settings

        gateway = MessagingGateway()
        p = Persona(id=uuid.uuid4(), first_name="HTML", last_name="Test", email="html@test.com")
        db_session.add(p)
        db_session.commit()

        settings = get_settings()
        with patch.object(settings, "smtp_host", ""):
            with patch.object(settings, "smtp_user", ""):
                with patch.object(settings, "smtp_password", ""):
                    log = asyncio.run(gateway.send_email(
                        db_session,
                        persona_id=str(p.id),
                        content="plain text",
                        leader_id=None,
                        html="<p>HTML content</p>",
                    ))
        assert log is not None
        assert log.channel == "Email"

    def test_send_email_no_email_raises(self, db_session):
        """send_email must fail if persona has no email."""
        from backend.services.messaging import MessagingGateway

        gateway = MessagingGateway()
        p = Persona(id=uuid.uuid4(), first_name="Test", last_name="User", email=None)
        db_session.add(p)
        db_session.commit()

        try:
            asyncio.run(gateway.send_email(
                db_session,
                persona_id=str(p.id),
                content="Test",
                leader_id=None,
            ))
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "sin correo electronico" in str(e)

    def test_persona_not_found_raises(self, db_session):
        """Sending to a non-existent persona must raise ValueError."""
        from backend.services.messaging import MessagingGateway

        gateway = MessagingGateway()
        fake_id = str(uuid.uuid4())

        try:
            asyncio.run(gateway.send_email(
                db_session,
                persona_id=fake_id,
                content="Test",
                leader_id=None,
            ))
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Persona no encontrada" in str(e)

    def test_leader_id_conversion(self, db_session):
        """leader_id as string must be converted to UUID."""
        from backend.services.messaging import MessagingGateway

        gateway = MessagingGateway()
        p = Persona(id=uuid.uuid4(), first_name="Test", last_name="User", phone="+573001234567")
        db_session.add(p)
        db_session.commit()
        leader_id_str = str(uuid.uuid4())

        log = asyncio.run(gateway.send_whatsapp(
            db_session,
            persona_id=str(p.id),
            content="Test with leader",
            leader_id=leader_id_str,
        ))
        assert log is not None
        assert log.leader_id is not None


class TestStubMessagingGateway:
    """Tests for StubMessagingGateway class."""

    def test_stub_whatsapp_never_sends(self, db_session):
        """Stub must log with STUB outcome."""
        from backend.services.messaging import StubMessagingGateway
        from backend.services.messaging_outcomes import CommunicationOutcome

        gateway = StubMessagingGateway()
        p = Persona(id=uuid.uuid4(), first_name="Stub", last_name="User", phone="+573001234567")
        db_session.add(p)
        db_session.commit()

        log = asyncio.run(gateway.send_whatsapp(
            db_session,
            persona_id=str(p.id),
            content="Stub test",
            leader_id=None,
        ))
        assert log.outcome == CommunicationOutcome.STUB.value

    def test_stub_email_override(self, db_session):
        """TEST_EMAIL_OVERRIDE must delegate to real gateway."""
        from backend.services.messaging import StubMessagingGateway
        from backend.services.messaging_outcomes import CommunicationOutcome
        from backend.core.config import get_settings

        settings = get_settings()
        with patch.object(settings, "test_email_override", "override@test.com"):
            with patch.object(settings, "smtp_host", ""):
                with patch.object(settings, "smtp_user", ""):
                    with patch.object(settings, "smtp_password", ""):
                        gateway = StubMessagingGateway()
                        p = Persona(id=uuid.uuid4(), first_name="Override", last_name="User", email="override@test.com")
                        db_session.add(p)
                        db_session.commit()

                        log = asyncio.run(gateway.send_email(
                            db_session,
                            persona_id=str(p.id),
                            content="Override test",
                            leader_id=None,
                        ))
                        assert log.outcome == CommunicationOutcome.PENDING_SMTP_CONFIG.value

    def test_stub_email_override_no_match(self, db_session):
        """If TEST_EMAIL_OVERRIDE doesn't match, stub must log."""
        from backend.services.messaging import StubMessagingGateway
        from backend.services.messaging_outcomes import CommunicationOutcome
        from backend.core.config import get_settings

        settings = get_settings()
        with patch.object(settings, "test_email_override", "different@test.com"):
            gateway = StubMessagingGateway()
            p = Persona(id=uuid.uuid4(), first_name="NoMatch", last_name="User", email="other@test.com")
            db_session.add(p)
            db_session.commit()

            log = asyncio.run(gateway.send_email(
                db_session,
                persona_id=str(p.id),
                content="No match",
                leader_id=None,
            ))
            assert log.outcome == CommunicationOutcome.STUB.value


class TestGetMessagingGateway:
    """Tests for get_messaging_gateway factory."""

    def test_gateway_singleton(self):
        """get_messaging_gateway must return same instance on repeated calls."""
        from backend.services.messaging import get_messaging_gateway, reset_gateway_singleton

        reset_gateway_singleton()
        g1 = get_messaging_gateway()
        g2 = get_messaging_gateway()
        assert g1 is g2

    def test_reset_gateway(self):
        """reset_gateway_singleton must clear the cached instance."""
        from backend.services.messaging import get_messaging_gateway, reset_gateway_singleton

        reset_gateway_singleton()
        g1 = get_messaging_gateway()
        reset_gateway_singleton()
        g2 = get_messaging_gateway()
        assert g1 is not g2

    def test_gateway_leader_id_as_uuid(self, db_session):
        """leader_id passed as UUID object must work (line 53)."""
        from backend.services.messaging import get_messaging_gateway, reset_gateway_singleton

        reset_gateway_singleton()
        gateway = get_messaging_gateway()
        p = Persona(id=uuid.uuid4(), first_name="Leader", last_name="Test", phone="+573001234567")
        db_session.add(p)
        db_session.commit()

        leader_uuid = uuid.uuid4()
        log = asyncio.run(gateway.send_whatsapp(
            db_session, persona_id=str(p.id), content="Leader test",
            leader_id=leader_uuid,
        ))
        assert log.leader_id == leader_uuid

    def test_gateway_invalid_leader_id_ignored(self, db_session):
        """Invalid leader_id string must be silently ignored (lines 57-58)."""
        from backend.services.messaging import get_messaging_gateway, reset_gateway_singleton

        reset_gateway_singleton()
        gateway = get_messaging_gateway()
        p = Persona(id=uuid.uuid4(), first_name="BadLeader", last_name="Test", phone="+573001234567")
        db_session.add(p)
        db_session.commit()

        log = asyncio.run(gateway.send_whatsapp(
            db_session, persona_id=str(p.id), content="Bad leader",
            leader_id="not-a-valid-uuid",
        ))
        assert log.leader_id is None

    def test_stub_sms(self, db_session):
        """Stub send_sms must log with STUB outcome (lines 272-280)."""
        from backend.services.messaging import StubMessagingGateway
        from backend.services.messaging_outcomes import CommunicationOutcome

        gateway = StubMessagingGateway()
        p = Persona(id=uuid.uuid4(), first_name="StubSMS", last_name="User", phone="+573001234567")
        db_session.add(p)
        db_session.commit()

        log = asyncio.run(gateway.send_sms(
            db_session, persona_id=str(p.id), content="SMS stub", leader_id=None,
        ))
        assert log.outcome == CommunicationOutcome.STUB.value

    def test_stub_whatsapp_no_persona(self, db_session):
        """Stub send_whatsapp with non-existent persona must handle gracefully."""
        from backend.services.messaging import StubMessagingGateway
        from backend.services.messaging_outcomes import CommunicationOutcome

        gateway = StubMessagingGateway()
        log = asyncio.run(gateway.send_whatsapp(
            db_session, persona_id=str(uuid.uuid4()), content="No persona", leader_id=None,
        ))
        assert log.outcome == CommunicationOutcome.STUB.value

    def test_get_messaging_gateway_stub_mode(self):
        """get_messaging_gateway with stub_comms must return StubMessagingGateway (lines 364-366)."""
        from backend.services.messaging import get_messaging_gateway, reset_gateway_singleton, StubMessagingGateway
        from backend.core.config import get_settings

        reset_gateway_singleton()
        settings = get_settings()
        with patch.object(settings, "stub_comms", True):
            gateway = get_messaging_gateway()
            assert isinstance(gateway, StubMessagingGateway)

    def test_gateway_smtp_failure(self, db_session):
        """SMTP connection failure must result in SMTP_FAILED outcome."""
        from backend.services.messaging import MessagingGateway
        from backend.services.messaging_outcomes import CommunicationOutcome
        from backend.core.config import get_settings

        gateway = MessagingGateway()
        p = Persona(id=uuid.uuid4(), first_name="SMTP", last_name="Fail", email="smtp@test.com")
        db_session.add(p)
        db_session.commit()

        settings = get_settings()
        # Set SMTP config that will fail to connect
        with patch.object(settings, "smtp_host", "smtp.invalid.local"):
            with patch.object(settings, "smtp_user", "user"):
                with patch.object(settings, "smtp_password", "pass"):
                    log = asyncio.run(gateway.send_email(
                        db_session, persona_id=str(p.id), content="Fail test",
                        leader_id=None,
                    ))
        assert log.outcome == CommunicationOutcome.SMTP_FAILED.value

    def test_gateway_smtp_success_with_html(self, db_session):
        """SMTP success with HTML must execute MIMEMultipart path (lines 190, 193-198)."""
        from backend.services.messaging import MessagingGateway
        from backend.services.messaging_outcomes import CommunicationOutcome
        from backend.core.config import get_settings
        import smtplib

        gateway = MessagingGateway()
        p = Persona(id=uuid.uuid4(), first_name="SMTP", last_name="HTML", email="html@test.com")
        db_session.add(p)
        db_session.commit()

        settings = get_settings()
        with patch.object(settings, "smtp_host", "smtp.test.com"):
            with patch.object(settings, "smtp_user", "user@test.com"):
                with patch.object(settings, "smtp_password", "pass"):
                    # Mock smtplib.SMTP to avoid real connection
                    with patch("smtplib.SMTP") as mock_smtp:
                        mock_instance = mock_smtp.return_value.__enter__.return_value
                        log = asyncio.run(gateway.send_email(
                            db_session, persona_id=str(p.id),
                            content="plain", leader_id=None,
                            html="<p>html</p>",
                        ))
        assert log.outcome == CommunicationOutcome.SENT_REAL.value
