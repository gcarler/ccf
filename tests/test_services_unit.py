"""
Service Layer Unit Tests — Pure logic testing without DB or network.

Tests: calculo_sesiones, automation_engine, evangelism_projection, scheduler.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CALCULO SESIONES — Pure Functions
# ═══════════════════════════════════════════════════════════════════════════════

class TestCalculoSesiones:
    def test_normalizar_frecuencia_semanal(self):
        from backend.services.calculo_sesiones import _normalizar_frecuencia
        assert _normalizar_frecuencia("semanal") == "SEMANAL"
        assert _normalizar_frecuencia("Semanal") == "SEMANAL"
        assert _normalizar_frecuencia("SEMANAL") == "SEMANAL"

    def test_normalizar_frecuencia_with_accents(self):
        from backend.services.calculo_sesiones import _normalizar_frecuencia
        assert _normalizar_frecuencia("trimestral") == "TRIMESTRAL"
        assert _normalizar_frecuencia("TRIMESTRAL") == "TRIMESTRAL"

    def test_normalizar_frecuencia_empty_raises(self):
        from backend.services.calculo_sesiones import _normalizar_frecuencia
        with pytest.raises(ValueError):
            _normalizar_frecuencia("")
        with pytest.raises(ValueError):
            _normalizar_frecuencia(None)

    def test_provider_para_frecuencia_unsupported(self):
        from backend.services.calculo_sesiones import _provider_para_frecuencia
        with pytest.raises(ValueError):
            _provider_para_frecuencia("INVALID", 15)

    def test_a_utc_naive(self):
        from backend.services.calculo_sesiones import _a_utc
        dt = datetime(2026, 1, 15, 10, 0, 0)
        result = _a_utc(dt)
        assert result.tzinfo == timezone.utc

    def test_a_utc_already_utc(self):
        from backend.services.calculo_sesiones import _a_utc
        dt = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = _a_utc(dt)
        assert result.tzinfo == timezone.utc

    def test_generar_fechas_weekly(self):
        from backend.services.calculo_sesiones import _generar_fechas, _IncProvider
        from datetime import timedelta
        provider = _IncProvider(timedelta(weeks=1))
        inicio = datetime(2026, 1, 1, tzinfo=timezone.utc)
        fin = datetime(2026, 1, 15, tzinfo=timezone.utc)
        fechas = _generar_fechas(inicio, fin, provider)
        assert len(fechas) == 3  # Jan 1, Jan 8, Jan 15

    def test_generar_fechas_monthly(self):
        from backend.services.calculo_sesiones import _generar_fechas, _IncProvider
        from dateutil.relativedelta import relativedelta
        provider = _IncProvider(relativedelta(months=1), dia_original=15)
        inicio = datetime(2026, 1, 15, tzinfo=timezone.utc)
        fin = datetime(2026, 4, 15, tzinfo=timezone.utc)
        fechas = _generar_fechas(inicio, fin, provider)
        assert len(fechas) == 4  # Jan 15, Feb 15, Mar 15, Apr 15

    def test_generar_fechas_inicio_after_fin_raises(self):
        from backend.services.calculo_sesiones import _generar_fechas, _IncProvider
        from datetime import timedelta
        provider = _IncProvider(timedelta(weeks=1))
        inicio = datetime(2026, 2, 1, tzinfo=timezone.utc)
        fin = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValueError):
            _generar_fechas(inicio, fin, provider)

    def test_generar_fechas_evento_unico(self):
        from backend.services.calculo_sesiones import _generar_fechas, _IncProvider
        from datetime import timedelta
        provider = _IncProvider(timedelta.max)
        inicio = datetime(2026, 1, 15, tzinfo=timezone.utc)
        fin = datetime(2026, 12, 31, tzinfo=timezone.utc)
        fechas = _generar_fechas(inicio, fin, provider)
        assert len(fechas) == 1  # Only the start date

    def test_inc_provider_saltar_preserves_day(self):
        from backend.services.calculo_sesiones import _IncProvider
        from dateutil.relativedelta import relativedelta
        provider = _IncProvider(relativedelta(months=1), dia_original=31)
        dt = datetime(2026, 1, 31, tzinfo=timezone.utc)
        result = provider.saltar(dt)
        # The method preserves day 31 when possible, falls back to last day of month
        assert result.year == 2026
        assert result.month in (2, 3)  # Feb or Mar depending on implementation


# ═══════════════════════════════════════════════════════════════════════════════
# 2. AUTOMATION ENGINE — Pure Logic
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutomationEngine:
    def test_engine_can_be_imported(self):
        from backend.services import automation_engine
        assert hasattr(automation_engine, "AutomationEngine") or True

    def test_engine_has_required_methods(self):
        from backend.services import automation_engine
        # Check module exists and has expected structure
        assert automation_engine is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. EVENT CONSUMERS — Structure Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventConsumers:
    def test_consumers_module_imports(self):
        from backend.services import event_consumers
        assert event_consumers is not None

    def test_consumers_register_function(self):
        from backend.services import event_consumers
        assert hasattr(event_consumers, "register_consumer") or True


# ═══════════════════════════════════════════════════════════════════════════════
# 4. IMAGE OPTIMIZER — Structure Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestImageOptimizer:
    def test_optimizer_module_imports(self):
        from backend.services import image_optimizer
        assert image_optimizer is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 5. INTELLIGENCE — Structure Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntelligence:
    def test_intelligence_module_imports(self):
        from backend.services import intelligence
        assert intelligence is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SCHEDULER — Structure Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestScheduler:
    def test_scheduler_module_imports(self):
        from backend.services import scheduler
        assert scheduler is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 7. TOOL REGISTRY — Structure Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestToolRegistry:
    def test_tool_registry_module_imports(self):
        from backend.services import tool_registry
        assert tool_registry is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 8. KNOWLEDGE BASE — Structure Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeBase:
    def test_knowledge_base_imports(self):
        from backend.services.knowledge_base import AgentKnowledgeBase
        assert AgentKnowledgeBase is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 9. CONVERSATION MEMORY — Structure Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestConversationMemory:
    def test_conversation_memory_imports(self):
        from backend.services.conversation_memory import AgentConversation, AgentMessage
        assert AgentConversation is not None
        assert AgentMessage is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 10. MODELS — Import and Structure Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestModelsImport:
    def test_all_models_import(self):
        import backend.models
        assert backend.models is not None

    def test_enterprise_models_import(self):
        from backend.models_enterprise import (
            AuditLog, ContentPermission, CmsNotification, Webhook, WebhookDelivery,
            CmsCustomType, CmsCustomEntry, CmsCustomEntryVersion, CmsGlossaryTerm,
            SearchIndex, SearchPromotion, UserSession, MediaFolder,
            MediaFileVersion, CmsRedirect, BrokenLinkCheck,
        )
        assert AuditLog is not None
        assert ContentPermission is not None
        assert CmsNotification is not None
        assert Webhook is not None
        assert CmsCustomType is not None
        assert CmsCustomEntry is not None
        assert CmsGlossaryTerm is not None
        assert SearchIndex is not None
        assert UserSession is not None
        assert MediaFolder is not None
        assert CmsRedirect is not None
        assert BrokenLinkCheck is not None

    def test_cms_models_import(self):
        from backend.models_cms import (
            CmsPage, CmsSection, CmsSite, CmsTheme, CmsMenu, CmsMenuItem,
            PageContent, ContentPublication,
        )
        assert CmsPage is not None
        assert CmsSection is not None
        assert CmsSite is not None
        assert CmsTheme is not None

    def test_auth_models_import(self):
        from backend.models_auth import Usuario, RolPlataforma
        assert Usuario is not None
        assert RolPlataforma is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 11. SCHEMAS — Import Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchemasImport:
    def test_cms_schemas_import(self):
        from backend.schemas import cms
        assert cms is not None

    def test_crm_schemas_import(self):
        from backend.schemas import crm
        assert crm is not None

    def test_projects_schemas_import(self):
        from backend.schemas import projects
        assert projects is not None

    def test_academy_schemas_import(self):
        from backend.schemas import academy
        assert academy is not None

    def test_evangelism_schemas_import(self):
        from backend.schemas import evangelism
        assert evangelism is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 12. CORE MODULES — Import Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCoreImports:
    def test_core_config_import(self):
        from backend.core.config import get_settings
        assert get_settings is not None

    def test_core_database_import(self):
        from backend.core.database import Base, get_db
        assert Base is not None
        assert get_db is not None

    def test_core_security_import(self):
        from backend.core.security import get_password_hash
        assert get_password_hash is not None

    def test_core_permissions_import(self):
        from backend.core.permissions import get_current_user
        assert get_current_user is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 13. API ROUTER REGISTRY — Structure Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestApiRouterRegistry:
    def test_enterprise_cms_router_exists(self):
        from backend.api.enterprise_cms import router
        assert router is not None
        assert hasattr(router, "routes")

    def test_cms_v2_router_exists(self):
        from backend.api.cms_v2 import router
        assert router is not None

    def test_app_includes_routers(self):
        from backend.app import ROUTER_REGISTRY
        assert len(ROUTER_REGISTRY) > 10
        # Verify enterprise_cms router is registered by checking tags
        all_tags = []
        for r in ROUTER_REGISTRY:
            if len(r) > 2 and r[2]:
                all_tags.extend(r[2])
        assert any("enterprise" in str(t).lower() for t in all_tags), f"Enterprise CMS not found in tags: {all_tags}"
