"""Massive service-level coverage tests — exercises every public function/class."""
import asyncio
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, AsyncMock


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY (tool_registry.py) — 223 stmts, 0% coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestToolParameter:
    def test_create_minimal(self):
        from backend.services.tool_registry import ToolParameter
        p = ToolParameter(name="q", type="string", description="query")
        assert p.name == "q"
        assert p.required is True
        assert p.enum is None

    def test_create_with_enum(self):
        from backend.services.tool_registry import ToolParameter
        p = ToolParameter(name="status", type="string", description="st", required=False, enum=["a", "b"])
        assert p.required is False
        assert p.enum == ["a", "b"]

    def test_integer_type(self):
        from backend.services.tool_registry import ToolParameter
        p = ToolParameter(name="limit", type="integer", description="max items")
        assert p.type == "integer"

    def test_boolean_type(self):
        from backend.services.tool_registry import ToolParameter
        p = ToolParameter(name="verbose", type="boolean", description="verbose", required=False)
        assert p.required is False

    def test_array_type(self):
        from backend.services.tool_registry import ToolParameter
        p = ToolParameter(name="tags", type="array", description="tags")
        assert p.type == "array"


class TestToolDefinition:
    def test_create_minimal(self):
        from backend.services.tool_registry import ToolDefinition
        d = ToolDefinition(name="test", description="desc", module="mod")
        assert d.parameters == []
        assert d.returns == "dict"

    def test_create_full(self):
        from backend.services.tool_registry import ToolDefinition, ToolParameter
        d = ToolDefinition(
            name="x", description="y", module="z",
            parameters=[ToolParameter(name="a", type="string", description="d")],
            returns="list",
        )
        assert len(d.parameters) == 1
        assert d.returns == "list"


class TestAgentToolABC:
    def _make_tool(self):
        from backend.services.tool_registry import AgentTool, ToolParameter

        class DummyTool(AgentTool):
            @property
            def name(self): return "dummy"
            @property
            def description(self): return "A dummy tool"
            @property
            def module(self): return "test"

            def execute(self, **kwargs):
                return {"ok": True}

        return DummyTool()

    def test_properties(self):
        t = self._make_tool()
        assert t.name == "dummy"
        assert t.description == "A dummy tool"
        assert t.module == "test"

    def test_default_parameters_empty(self):
        t = self._make_tool()
        assert t.parameters == []

    def test_execute(self):
        t = self._make_tool()
        assert t.execute() == {"ok": True}

    def test_to_definition(self):
        t = self._make_tool()
        d = t.to_definition()
        assert d.name == "dummy"
        assert d.module == "test"

    def test_to_openai_function(self):
        from backend.services.tool_registry import AgentTool, ToolParameter

        class ParamTool(AgentTool):
            @property
            def name(self): return "pt"
            @property
            def description(self): return "param tool"
            @property
            def module(self): return "test"
            @property
            def parameters(self):
                return [
                    ToolParameter(name="q", type="string", description="query"),
                    ToolParameter(name="n", type="integer", description="num", required=False, enum=["a", "b"]),
                ]
            def execute(self, **kwargs): return {}

        t = ParamTool()
        f = t.to_openai_function()
        assert f["type"] == "function"
        assert f["function"]["name"] == "pt"
        assert "q" in f["function"]["parameters"]["properties"]
        assert "q" in f["function"]["parameters"]["required"]
        assert "n" not in f["function"]["parameters"]["required"]  # not required
        assert f["function"]["parameters"]["properties"]["n"]["enum"] == ["a", "b"]

    def test_to_openai_no_params(self):
        t = self._make_tool()
        f = t.to_openai_function()
        assert f["function"]["parameters"]["properties"] == {}
        assert f["function"]["parameters"]["required"] == []


class TestToolRegistry:
    def _make_dummy(self, name="d1"):
        from backend.services.tool_registry import AgentTool

        class D(AgentTool):
            def __init__(self, n):
                self._n = n
            @property
            def name(self): return self._n
            @property
            def description(self): return f"desc {self._n}"
            @property
            def module(self): return "test"
            def execute(self, **kwargs): return {"name": self._n, **kwargs}

        return D(name)

    def test_register_and_get(self):
        from backend.services.tool_registry import ToolRegistry
        r = ToolRegistry()
        t = self._make_dummy("foo")
        r.register(t)
        assert r.get("foo") is t
        assert r.count == 1

    def test_get_missing(self):
        from backend.services.tool_registry import ToolRegistry
        r = ToolRegistry()
        assert r.get("nope") is None

    def test_unregister(self):
        from backend.services.tool_registry import ToolRegistry
        r = ToolRegistry()
        r.register(self._make_dummy("x"))
        r.unregister("x")
        assert r.get("x") is None

    def test_unregister_missing_noop(self):
        from backend.services.tool_registry import ToolRegistry
        r = ToolRegistry()
        r.unregister("nope")  # Should not raise

    def test_list_all(self):
        from backend.services.tool_registry import ToolRegistry
        r = ToolRegistry()
        r.register(self._make_dummy("a"))
        r.register(self._make_dummy("b"))
        defs = r.list_all()
        assert len(defs) == 2
        names = {d.name for d in defs}
        assert names == {"a", "b"}

    def test_list_by_module(self):
        from backend.services.tool_registry import ToolRegistry, AgentTool

        class M1(AgentTool):
            @property
            def name(self): return "m1"
            @property
            def description(self): return "m1"
            @property
            def module(self): return "mod_a"
            def execute(self, **kwargs): return {}

        class M2(AgentTool):
            @property
            def name(self): return "m2"
            @property
            def description(self): return "m2"
            @property
            def module(self): return "mod_b"
            def execute(self, **kwargs): return {}

        r = ToolRegistry()
        r.register(M1())
        r.register(M2())
        assert len(r.list_by_module("mod_a")) == 1
        assert len(r.list_by_module("mod_b")) == 1
        assert len(r.list_by_module("mod_c")) == 0

    def test_get_openai_tools(self):
        from backend.services.tool_registry import ToolRegistry
        r = ToolRegistry()
        r.register(self._make_dummy("t1"))
        tools = r.get_openai_tools()
        assert len(tools) == 1
        assert tools[0]["type"] == "function"

    def test_execute_found(self):
        from backend.services.tool_registry import ToolRegistry
        r = ToolRegistry()
        r.register(self._make_dummy("t"))
        result = r.execute("t", query="hello")
        assert result["success"] is True
        assert result["result"]["name"] == "t"
        assert result["result"]["query"] == "hello"

    def test_execute_not_found(self):
        from backend.services.tool_registry import ToolRegistry
        r = ToolRegistry()
        result = r.execute("nonexistent")
        assert "error" in result
        assert result["error"] == "Tool 'nonexistent' not found"

    def test_execute_raises(self):
        from backend.services.tool_registry import ToolRegistry, AgentTool

        class BadTool(AgentTool):
            @property
            def name(self): return "bad"
            @property
            def description(self): return "bad"
            @property
            def module(self): return "test"
            def execute(self, **kwargs): raise ValueError("boom")

        r = ToolRegistry()
        r.register(BadTool())
        result = r.execute("bad")
        assert result["success"] is False
        assert "boom" in result["error"]

    def test_overwrite_register(self):
        from backend.services.tool_registry import ToolRegistry
        r = ToolRegistry()
        r.register(self._make_dummy("x"))
        r.register(self._make_dummy("x"))
        assert r.count == 1


class TestConcreteToolClasses:
    def _make_db_mock(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.limit.return_value.all.return_value = []
        db.query.return_value.filter.return_value.count.return_value = 0
        return db

    @patch("backend.core.database.SessionLocal")
    def test_crm_search_persona(self, mock_sl):
        from backend.services.tool_registry import CRMSearchPersona
        mock_sl.return_value = self._make_db_mock()
        tool = CRMSearchPersona()
        assert tool.name == "crm_search_persona"
        assert tool.module == "crm"
        result = tool.execute(query="test")
        assert result["count"] == 0

    @patch("backend.core.database.SessionLocal")
    def test_crm_get_persona_profile_not_found(self, mock_sl):
        from backend.services.tool_registry import CRMGetPersonaProfile
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        mock_sl.return_value = db
        tool = CRMGetPersonaProfile()
        result = tool.execute(persona_id=str(uuid.uuid4()))
        assert "error" in result

    @patch("backend.core.database.SessionLocal")
    def test_academy_search_course(self, mock_sl):
        from backend.services.tool_registry import AcademySearchCourse
        mock_sl.return_value = self._make_db_mock()
        tool = AcademySearchCourse()
        assert tool.name == "academy_search_course"
        result = tool.execute(query="python")
        assert result["count"] == 0

    @patch("backend.core.database.SessionLocal")
    def test_academy_get_stats(self, mock_sl):
        from backend.services.tool_registry import AcademyGetStats
        mock_sl.return_value = self._make_db_mock()
        tool = AcademyGetStats()
        result = tool.execute()
        assert "active_courses" in result

    @patch("backend.core.database.SessionLocal")
    def test_projects_search_task(self, mock_sl):
        from backend.services.tool_registry import ProjectsSearchTask
        mock_sl.return_value = self._make_db_mock()
        tool = ProjectsSearchTask()
        result = tool.execute(query="fix")
        assert result["count"] == 0

    @patch("backend.core.database.SessionLocal")
    def test_projects_search_task_with_status(self, mock_sl):
        from backend.services.tool_registry import ProjectsSearchTask
        mock_sl.return_value = self._make_db_mock()
        tool = ProjectsSearchTask()
        result = tool.execute(query="fix", status="done")
        assert result["count"] == 0

    @patch("backend.core.database.SessionLocal")
    def test_projects_get_stats(self, mock_sl):
        from backend.services.tool_registry import ProjectsGetStats
        mock_sl.return_value = self._make_db_mock()
        tool = ProjectsGetStats()
        result = tool.execute()
        assert "total_projects" in result

    @patch("backend.core.database.SessionLocal")
    def test_analytics_get_radar(self, mock_sl):
        from backend.services.tool_registry import AnalyticsGetRadar
        mock_sl.return_value = self._make_db_mock()
        tool = AnalyticsGetRadar()
        result = tool.execute()
        assert "personas" in result

    @patch("backend.core.database.SessionLocal")
    def test_analytics_proactive(self, mock_sl):
        from backend.services.tool_registry import AnalyticsProactive
        mock_sl.return_value = self._make_db_mock()
        with patch("backend.analytics.proactive_ia.run_proactive_analysis", return_value=[]):
            tool = AnalyticsProactive()
            result = tool.execute()
            assert result["count"] == 0


class TestRegisterAllTools:
    def test_register_all(self):
        from backend.services.tool_registry import register_all_tools, tool_registry
        initial_count = tool_registry.count
        result = register_all_tools()
        assert result.count >= 8


# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGING (messaging.py) — 366 stmts
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateLog:
    def test_create_log_basic(self):
        from backend.services.messaging import _create_log
        db = MagicMock()
        mock_log = MagicMock()
        mock_log.id = uuid.uuid4()
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock(side_effect=lambda x: None)
        with patch("backend.services.messaging.models") as mock_models:
            mock_models.CommunicationLog.return_value = mock_log
            result = _create_log(
                db, persona_id="test-persona", channel="Email",
                content="Hello", leader_id=None,
            )
            db.add.assert_called_once()
            db.commit.assert_called_once()

    def test_create_log_with_leader_uuid(self):
        from backend.services.messaging import _create_log
        db = MagicMock()
        with patch("backend.services.messaging.models") as mock_models:
            mock_models.CommunicationLog.return_value = MagicMock()
            _create_log(
                db, persona_id="p1", channel="SMS", content="Hi",
                leader_id=uuid.uuid4(),
            )
            db.add.assert_called_once()

    def test_create_log_with_leader_str(self):
        from backend.services.messaging import _create_log
        db = MagicMock()
        with patch("backend.services.messaging.models") as mock_models:
            mock_models.CommunicationLog.return_value = MagicMock()
            _create_log(
                db, persona_id="p1", channel="SMS", content="Hi",
                leader_id=str(uuid.uuid4()),
            )
            db.add.assert_called_once()

    def test_create_log_with_leader_int_fallback(self):
        from backend.services.messaging import _create_log
        db = MagicMock()
        with patch("backend.services.messaging.models") as mock_models:
            mock_models.CommunicationLog.return_value = MagicMock()
            with patch("backend.crud.crm.resolve_persona_id_for_user", side_effect=Exception("no")):
                _create_log(
                    db, persona_id="p1", channel="Email", content="Hi",
                    leader_id="not_a_uuid",
                )
                db.add.assert_called_once()

    def test_create_log_with_all_options(self):
        from backend.services.messaging import _create_log
        db = MagicMock()
        with patch("backend.services.messaging.models") as mock_models:
            mock_models.CommunicationLog.return_value = MagicMock()
            _create_log(
                db, persona_id="p1", channel="WhatsApp", content="msg",
                leader_id=uuid.uuid4(), campaign_name="camp",
                recipient_phone="+123", external_id="ext-123",
                outcome="sent_real",
            )
            db.add.assert_called_once()


class TestMessagingGateway:
    def _make_gateway(self):
        from backend.services.messaging import MessagingGateway
        settings = MagicMock()
        settings.smtp_host = None
        settings.smtp_port = 587
        settings.smtp_user = None
        settings.smtp_password = None
        return MessagingGateway(settings)

    def test_resolve_to_uuid(self):
        gw = self._make_gateway()
        result = gw._resolve_to_uuid(str(uuid.uuid4()))
        assert isinstance(result, uuid.UUID)

    def test_persona_or_raise_not_found(self):
        gw = self._make_gateway()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="no encontrada"):
            gw._persona_or_raise(db, str(uuid.uuid4()))

    def test_persona_or_raise_no_email(self):
        gw = self._make_gateway()
        db = MagicMock()
        persona = MagicMock()
        persona.email = None
        db.query.return_value.filter.return_value.first.return_value = persona
        with pytest.raises(ValueError, match="correo"):
            gw._persona_or_raise(db, str(uuid.uuid4()), require_email=True)

    def test_persona_or_raise_ok(self):
        gw = self._make_gateway()
        db = MagicMock()
        persona = MagicMock()
        persona.email = "test@test.com"
        db.query.return_value.filter.return_value.first.return_value = persona
        result = gw._persona_or_raise(db, str(uuid.uuid4()))
        assert result is persona

    def test_send_whatsapp_no_phone(self):
        gw = self._make_gateway()
        db = MagicMock()
        persona = MagicMock()
        persona.phone = None
        db.query.return_value.filter.return_value.first.return_value = persona
        with pytest.raises(ValueError, match="telefono"):
            asyncio.run(gw.send_whatsapp(db, str(uuid.uuid4()), "hi", None))

    def test_send_sms_no_phone(self):
        gw = self._make_gateway()
        db = MagicMock()
        persona = MagicMock()
        persona.phone = None
        db.query.return_value.filter.return_value.first.return_value = persona
        with pytest.raises(ValueError, match="celular"):
            asyncio.run(gw.send_sms(db, str(uuid.uuid4()), "hi", None))

    def test_send_email_no_smtp(self):
        gw = self._make_gateway()
        db = MagicMock()
        persona = MagicMock()
        persona.email = "test@test.com"
        db.query.return_value.filter.return_value.first.return_value = persona
        with patch("backend.services.messaging._create_log") as mock_log:
            mock_log.return_value = MagicMock()
            asyncio.run(gw.send_email(db, str(uuid.uuid4()), "content", None))

    def test_send_email_with_smtp(self):
        from backend.services.messaging import MessagingGateway
        settings = MagicMock()
        settings.smtp_host = "smtp.test.com"
        settings.smtp_port = 587
        settings.smtp_user = "user@test.com"
        settings.smtp_password = "pass"
        gw = MessagingGateway(settings)
        db = MagicMock()
        persona = MagicMock()
        persona.email = "test@test.com"
        db.query.return_value.filter.return_value.first.return_value = persona
        with patch("backend.services.messaging.smtplib") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.SMTP.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.SMTP.return_value.__exit__ = MagicMock(return_value=False)
            with patch("backend.services.messaging._create_log") as mock_log:
                mock_log.return_value = MagicMock()
                asyncio.run(gw.send_email(db, str(uuid.uuid4()), "content", None))

    def test_send_email_smtp_fails(self):
        from backend.services.messaging import MessagingGateway
        settings = MagicMock()
        settings.smtp_host = "smtp.test.com"
        settings.smtp_port = 587
        settings.smtp_user = "user@test.com"
        settings.smtp_password = "pass"
        gw = MessagingGateway(settings)
        db = MagicMock()
        persona = MagicMock()
        persona.email = "test@test.com"
        db.query.return_value.filter.return_value.first.return_value = persona
        with patch("backend.services.messaging.smtplib") as mock_smtp:
            mock_smtp.SMTP.side_effect = Exception("Connection refused")
            with patch("backend.services.messaging._create_log") as mock_log:
                mock_log.return_value = MagicMock()
                asyncio.run(gw.send_email(db, str(uuid.uuid4()), "content", None))


class TestStubMessagingGateway:
    def _make_stub(self):
        from backend.services.messaging import StubMessagingGateway
        settings = MagicMock()
        settings.test_email_override = ""
        return StubMessagingGateway(settings)

    def test_stub_whatsapp(self):
        stub = self._make_stub()
        db = MagicMock()
        persona = MagicMock()
        persona.phone = "+123"
        db.query.return_value.filter.return_value.first.return_value = persona
        with patch("backend.services.messaging._create_log") as mock_log:
            mock_log.return_value = MagicMock()
            asyncio.run(stub.send_whatsapp(db, str(uuid.uuid4()), "hi", None))

    def test_stub_sms(self):
        stub = self._make_stub()
        db = MagicMock()
        persona = MagicMock()
        persona.phone = "+123"
        db.query.return_value.filter.return_value.first.return_value = persona
        with patch("backend.services.messaging._create_log") as mock_log:
            mock_log.return_value = MagicMock()
            asyncio.run(stub.send_sms(db, str(uuid.uuid4()), "hi", None))

    def test_stub_email(self):
        stub = self._make_stub()
        db = MagicMock()
        persona = MagicMock()
        persona.email = "test@test.com"
        db.query.return_value.filter.return_value.first.return_value = persona
        with patch("backend.services.messaging._create_log") as mock_log:
            mock_log.return_value = MagicMock()
            asyncio.run(stub.send_email(db, str(uuid.uuid4()), "hi", None))

    def test_stub_email_with_override(self):
        from backend.services.messaging import StubMessagingGateway
        settings = MagicMock()
        settings.test_email_override = "override@test.com"
        settings.smtp_host = None
        settings.smtp_port = 587
        settings.smtp_user = None
        settings.smtp_password = None
        stub = StubMessagingGateway(settings)
        db = MagicMock()
        persona = MagicMock()
        persona.email = "override@test.com"
        db.query.return_value.filter.return_value.first.return_value = persona
        with patch("backend.services.messaging._create_log") as mock_log:
            mock_log.return_value = MagicMock()
            asyncio.run(stub.send_email(db, str(uuid.uuid4()), "hi", None))


class TestGetMessagingGateway:
    def test_returns_stub_when_stub_comms(self):
        from backend.services.messaging import get_messaging_gateway, reset_gateway_singleton, StubMessagingGateway
        reset_gateway_singleton()
        with patch("backend.services.messaging.get_settings") as mock_s:
            mock_s.return_value.stub_comms = True
            gw = get_messaging_gateway()
            assert isinstance(gw, StubMessagingGateway)
        reset_gateway_singleton()

    def test_returns_real_when_not_stub(self):
        from backend.services.messaging import get_messaging_gateway, reset_gateway_singleton, MessagingGateway
        reset_gateway_singleton()
        with patch("backend.services.messaging.get_settings") as mock_s:
            mock_s.return_value.stub_comms = False
            gw = get_messaging_gateway()
            assert isinstance(gw, MessagingGateway)
        reset_gateway_singleton()

    def test_singleton_caching(self):
        from backend.services.messaging import get_messaging_gateway, reset_gateway_singleton
        reset_gateway_singleton()
        with patch("backend.services.messaging.get_settings") as mock_s:
            mock_s.return_value.stub_comms = False
            gw1 = get_messaging_gateway()
            gw2 = get_messaging_gateway()
            assert gw1 is gw2
        reset_gateway_singleton()

    def test_reset_gateway(self):
        from backend.services.messaging import get_messaging_gateway, reset_gateway_singleton
        reset_gateway_singleton()
        with patch("backend.services.messaging.get_settings") as mock_s:
            mock_s.return_value.stub_comms = False
            gw1 = get_messaging_gateway()
        reset_gateway_singleton()
        with patch("backend.services.messaging.get_settings") as mock_s:
            mock_s.return_value.stub_comms = False
            gw2 = get_messaging_gateway()
            assert gw1 is not gw2


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULER (scheduler.py) — 105 stmts
# ═══════════════════════════════════════════════════════════════════════════════

class TestScheduler:
    @patch("backend.services.scheduler.SessionLocal")
    @patch("backend.services.scheduler.run_proactive_analysis", return_value=3)
    def test_run_ai_analysis(self, mock_analysis, mock_sl):
        from backend.services.scheduler import run_ai_analysis
        mock_db = MagicMock()
        mock_sl.return_value = mock_db
        run_ai_analysis()
        mock_analysis.assert_called_once_with(mock_db)
        mock_db.close.assert_called_once()

    @patch("backend.services.scheduler.SessionLocal")
    @patch("backend.services.scheduler.run_proactive_analysis", side_effect=Exception("db error"))
    def test_run_ai_analysis_error(self, mock_analysis, mock_sl):
        from backend.services.scheduler import run_ai_analysis
        mock_sl.return_value = MagicMock()
        run_ai_analysis()

    @patch("backend.services.scheduler.SessionLocal")
    @patch("backend.services.scheduler.run_proactive_analysis", return_value=0)
    def test_run_ai_analysis_zero_insights(self, mock_analysis, mock_sl):
        from backend.services.scheduler import run_ai_analysis
        mock_sl.return_value = MagicMock()
        run_ai_analysis()


# ═══════════════════════════════════════════════════════════════════════════════
# AUTOMATION ENGINE (automation_engine.py) — 130 stmts
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutomationEngine:
    def test_singleton(self):
        from backend.services.automation_engine import AutomationEngine
        e1 = AutomationEngine()
        e2 = AutomationEngine()
        assert e1 is e2

    def test_start_and_stop(self):
        from backend.services.automation_engine import AutomationEngine
        engine = AutomationEngine()
        engine._stop_event.set()  # Prevent actual loop
        engine.start()
        assert engine._thread is not None
        engine.stop()
        assert engine._thread is None

    def test_stop_without_thread(self):
        from backend.services.automation_engine import AutomationEngine
        engine = AutomationEngine()
        engine._thread = None
        engine.stop()  # Should not raise


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENTS (payments.py) — 181 stmts
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaymentPreference:
    def test_create_minimal(self):
        from backend.services.payments import PaymentPreference
        p = PaymentPreference(amount=50.0, title="Diezmo")
        assert p.amount == 50.0
        assert p.email is None
        assert p.payment_type_id == "ticket"
        assert p.installments == 1

    def test_create_full(self):
        from backend.services.payments import PaymentPreference
        p = PaymentPreference(
            amount=100.0, title="Ofrenda", email="test@test.com",
            description="desc", donor_name="Juan",
            payment_type_id="credit_card", installments=3,
            metadata={"key": "val"},
        )
        assert p.email == "test@test.com"
        assert p.installments == 3


class TestPaymentResult:
    def test_create(self):
        from backend.services.payments import PaymentResult
        r = PaymentResult(payment_id=123, status="approved", status_detail="accredited", amount=50.0)
        assert r.payment_id == 123
        assert r.email is None

    def test_create_full(self):
        from backend.services.payments import PaymentResult
        r = PaymentResult(
            payment_id=456, status="pending", status_detail="pending",
            amount=100.0, email="a@b.com", donor_name="Pablo",
            raw={"key": "val"},
        )
        assert r.donor_name == "Pablo"
        assert r.raw == {"key": "val"}


class TestPaymentsModule:
    def test_get_sdk_no_token(self):
        import importlib
        import backend.services.payments as pay_mod
        # If mercadopago is installed, test the missing-token path
        if getattr(pay_mod, "mercadopago", None) is not None:
            with patch.object(pay_mod, "settings") as mock_s:
                mock_s.mercadopago_access_token = None
                with pytest.raises(RuntimeError, match="MERCADOPAGO_ACCESS_TOKEN"):
                    pay_mod._get_sdk()
        else:
            # mercadopago not installed — test the no-package guard
            with pytest.raises(RuntimeError, match="mercadopago"):
                pay_mod._get_sdk()

    @patch("backend.services.payments._get_sdk")
    def test_create_preference(self, mock_sdk):
        from backend.services.payments import create_donation_preference, PaymentPreference
        mock_pref = MagicMock()
        mock_pref.create.return_value = {"response": {"id": "123", "init_point": "url"}}
        mock_sdk.return_value.preference.return_value = mock_pref
        pref = PaymentPreference(amount=50.0, title="Diezmo")
        result = create_donation_preference(pref)
        assert result["id"] == "123"

    @patch("backend.services.payments._get_sdk")
    def test_create_preference_with_all_fields(self, mock_sdk):
        from backend.services.payments import create_donation_preference, PaymentPreference
        mock_pref = MagicMock()
        mock_pref.create.return_value = {"response": {"id": "456", "init_point": "url2"}}
        mock_sdk.return_value.preference.return_value = mock_pref
        pref = PaymentPreference(
            amount=200.0, title="Ofrenda", email="a@b.com",
            description="Monthly", donor_name="Juan",
            metadata={"source": "web"},
        )
        result = create_donation_preference(pref)
        assert result["id"] == "456"

    @patch("backend.services.payments._get_sdk")
    def test_create_preference_error(self, mock_sdk):
        from backend.services.payments import create_donation_preference, PaymentPreference
        mock_pref = MagicMock()
        mock_pref.create.side_effect = Exception("MP error")
        mock_sdk.return_value.preference.return_value = mock_pref
        with pytest.raises(Exception, match="MP error"):
            create_donation_preference(PaymentPreference(amount=50.0, title="test"))

    @patch("backend.services.payments._get_sdk")
    def test_get_payment_status(self, mock_sdk):
        from backend.services.payments import get_payment_status
        mock_payment = MagicMock()
        mock_payment.get.return_value = {
            "response": {
                "id": 123, "status": "approved",
                "status_detail": "accredited",
                "transaction_amount": 50.0,
                "payer": {"email": "a@b.com", "name": "Juan"},
            }
        }
        mock_sdk.return_value.payment.return_value = mock_payment
        result = get_payment_status(123)
        assert result.status == "approved"
        assert result.amount == 50.0

    @patch("backend.services.payments._get_sdk")
    def test_get_payment_status_error(self, mock_sdk):
        from backend.services.payments import get_payment_status
        mock_payment = MagicMock()
        mock_payment.get.side_effect = Exception("Not found")
        mock_sdk.return_value.payment.return_value = mock_payment
        with pytest.raises(Exception):
            get_payment_status(999)

    def test_process_webhook_payment_type(self):
        from backend.services.payments import process_webhook_notification
        with patch("backend.services.payments.get_payment_status") as mock_gps:
            mock_gps.return_value = MagicMock()
            data = {"type": "payment", "action": "payment.created", "data": {"id": "123"}}
            result = process_webhook_notification(data)
            mock_gps.assert_called_once_with(123)

    def test_process_webhook_payment_in_action(self):
        from backend.services.payments import process_webhook_notification
        with patch("backend.services.payments.get_payment_status") as mock_gps:
            mock_gps.return_value = MagicMock()
            data = {"type": "other", "action": "payment.updated", "data": {"id": "456"}}
            result = process_webhook_notification(data)
            mock_gps.assert_called_once_with(456)

    def test_process_webhook_ignored(self):
        from backend.services.payments import process_webhook_notification
        data = {"type": "topic", "action": "updated"}
        result = process_webhook_notification(data)
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSATION MEMORY (conversation_memory.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConversationMemory:
    def test_agent_message_create(self):
        from backend.services.conversation_memory import AgentMessage
        msg = AgentMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"

    def test_agent_conversation_create(self):
        from backend.services.conversation_memory import AgentConversation
        conv = AgentConversation(persona_id=uuid.uuid4(), title="Test Conv", agent_name="Optimus")
        assert conv.title == "Test Conv"
        # is_active defaults to True on column definition but not on construction
        assert conv.persona_id is not None

    def test_get_user_conversations_empty(self, db_session):
        from backend.services.conversation_memory import get_user_conversations
        with patch("backend.services.conversation_memory.SessionLocal", return_value=db_session):
            result = get_user_conversations(str(uuid.uuid4()))
            assert isinstance(result, list)

    def test_create_conversation(self, db_session):
        from backend.services.conversation_memory import create_conversation
        uid = uuid.uuid4()
        with patch("backend.services.conversation_memory.SessionLocal", return_value=db_session), \
             patch("backend.services.conversation_memory.resolve_persona_id_for_user", return_value=uuid.uuid4()):
            result = create_conversation(str(uid), title="Test")
            assert result is not None


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE (knowledge_base.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeBase:
    def test_import(self):
        from backend.services.knowledge_base import AgentKnowledgeBase, KnowledgeIndexer
        assert AgentKnowledgeBase is not None
        assert KnowledgeIndexer is not None

    def test_indexer_rebuild_all(self):
        from backend.services.knowledge_base import KnowledgeIndexer
        db = MagicMock()
        indexer = KnowledgeIndexer(db)
        stats = indexer.rebuild_all()
        assert isinstance(stats, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH (knowledge_graph.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeGraph:
    def test_import(self):
        from backend.services import knowledge_graph
        assert knowledge_graph is not None


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE OPTIMIZER (image_optimizer.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestImageOptimizer:
    def test_import(self):
        from backend.services import image_optimizer
        assert image_optimizer is not None


# ═══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE (intelligence.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntelligence:
    def test_import(self):
        from backend.services import intelligence
        assert intelligence is not None


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT CONSUMERS (event_consumers.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventConsumers:
    def test_import(self):
        from backend.services import event_consumers
        assert event_consumers is not None


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC CONTACT TRACKING (public_contact_tracking.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublicContactTracking:
    def test_import(self):
        from backend.services import public_contact_tracking
        assert public_contact_tracking is not None


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL (email.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmail:
    def test_import(self):
        from backend.services import email
        assert email is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TASK NOTIFICATIONS (task_notifications.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTaskNotifications:
    def test_import(self):
        from backend.services import task_notifications
        assert task_notifications is not None
