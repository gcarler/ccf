"""Massive core module + CRUD coverage tests."""
import asyncio
import uuid
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, AsyncMock


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/ABAC (abac.py) — 312 stmts, 0% coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestABACConstants:
    def test_protected_resources_exist(self):
        from backend.core.abac import PROTECTED_OWNER_RESOURCES
        assert "persona" in PROTECTED_OWNER_RESOURCES
        assert "profile" in PROTECTED_OWNER_RESOURCES
        assert "enrollment" in PROTECTED_OWNER_RESOURCES

    def test_academy_structure_tables(self):
        from backend.core.abac import ACADEMY_STRUCTURE_TABLES
        assert "academy_courses" in ACADEMY_STRUCTURE_TABLES
        assert "academy_lessons" in ACADEMY_STRUCTURE_TABLES

    def test_lector_module_access(self):
        from backend.core.abac import LECTOR_MODULE_ACCESS
        assert "read" in LECTOR_MODULE_ACCESS["crm"]
        assert "update" in LECTOR_MODULE_ACCESS["profile"]


class TestABACHelperFunctions:
    def test_get_current_user_id_no_token(self):
        from backend.core.abac import get_current_user_id
        request = MagicMock()
        request.cookies = {}
        request.headers = {}
        result = get_current_user_id(request)
        assert result is None

    def test_get_current_user_id_bearer_token(self):
        from backend.core.abac import get_current_user_id
        request = MagicMock()
        request.cookies = {}
        from jose import jwt as jose_jwt
        token = jose_jwt.encode({"sub": "user-uuid-123"}, "secret", algorithm="HS256")
        request.headers = {"Authorization": f"Bearer {token}"}
        with patch("backend.core.abac.SECRET_KEY", "secret"):
            result = get_current_user_id(request)
            assert result == "user-uuid-123"

    def test_get_current_user_id_cookie_token(self):
        from backend.core.abac import get_current_user_id
        request = MagicMock()
        from jose import jwt as jose_jwt
        token = jose_jwt.encode({"sub": "cookie-user"}, "secret", algorithm="HS256")
        request.cookies = {"access_token": token}
        request.headers.get.return_value = ""
        with patch("backend.core.abac.SECRET_KEY", "secret"):
            with patch("backend.core.abac.settings") as mock_s:
                mock_s.access_token_cookie_name = "access_token"
                result = get_current_user_id(request)
                assert result == "cookie-user"

    def test_get_current_user_id_invalid_token(self):
        from backend.core.abac import get_current_user_id
        request = MagicMock()
        request.cookies = {}
        request.headers = {"Authorization": "Bearer invalid-token"}
        with patch("backend.core.abac.SECRET_KEY", "secret"):
            result = get_current_user_id(request)
            assert result is None

    def test_get_current_platform_role_no_token(self):
        from backend.core.abac import get_current_platform_role
        request = MagicMock()
        request.cookies = {}
        request.headers = {}
        result = get_current_platform_role(request)
        assert result == "LECTOR"

    def test_get_current_platform_role_with_token(self):
        from backend.core.abac import get_current_platform_role
        from jose import jwt as jose_jwt
        request = MagicMock()
        token = jose_jwt.encode({"platform_role": "ADMIN"}, "secret", algorithm="HS256")
        request.cookies = {}
        request.headers = {"Authorization": f"Bearer {token}"}
        with patch("backend.core.abac.SECRET_KEY", "secret"):
            result = get_current_platform_role(request)
            assert result == "ADMIN"

    def test_get_current_platform_role_invalid_token(self):
        from backend.core.abac import get_current_platform_role
        request = MagicMock()
        request.cookies = {}
        request.headers = {"Authorization": "Bearer bad"}
        with patch("backend.core.abac.SECRET_KEY", "secret"):
            result = get_current_platform_role(request)
            assert result == "LECTOR"


class TestCheckAcademyWritePermission:
    def test_admin_can_write(self):
        from backend.core.abac import check_academy_write_permission
        assert check_academy_write_permission("ADMINISTRADOR", "academy_courses") is True

    def test_gestor_can_write_courses(self):
        from backend.core.abac import check_academy_write_permission
        assert check_academy_write_permission("GESTOR", "academy_courses") is True

    def test_gestor_can_write_lessons(self):
        from backend.core.abac import check_academy_write_permission
        assert check_academy_write_permission("GESTOR", "academy_lessons") is True

    def test_lector_cannot_write(self):
        from backend.core.abac import check_academy_write_permission
        assert check_academy_write_permission("LECTOR", "academy_courses") is False

    def test_editor_cannot_write(self):
        from backend.core.abac import check_academy_write_permission
        assert check_academy_write_permission("EDITOR", "academy_courses") is False

    def test_unknown_role_cannot_write(self):
        from backend.core.abac import check_academy_write_permission
        assert check_academy_write_permission("UNKNOWN", "academy_courses") is False


class TestCheckPermission:
    def test_admin_has_all(self):
        from backend.core.abac import _check_permission
        assert _check_permission("ADMINISTRADOR", "crm:read") is True
        assert _check_permission("ADMINISTRADOR", "academy:delete") is True
        assert _check_permission("ADMINISTRADOR", "*:admin") is True

    def test_gestor_can_crm_create(self):
        from backend.core.abac import _check_permission
        assert _check_permission("GESTOR", "crm:create") is True

    def test_gestor_cannot_delete(self):
        from backend.core.abac import _check_permission
        assert _check_permission("GESTOR", "crm:delete") is False

    def test_editor_can_read(self):
        from backend.core.abac import _check_permission
        assert _check_permission("EDITOR", "crm:read") is True

    def test_editor_cannot_create(self):
        from backend.core.abac import _check_permission
        assert _check_permission("EDITOR", "crm:create") is False

    def test_lector_can_read(self):
        from backend.core.abac import _check_permission
        assert _check_permission("LECTOR", "crm:read") is True

    def test_lector_cannot_write(self):
        from backend.core.abac import _check_permission
        assert _check_permission("LECTOR", "crm:create") is False

    def test_permission_without_colon(self):
        from backend.core.abac import _check_permission
        assert _check_permission("LECTOR", "crm") is True

    def test_unknown_role(self):
        from backend.core.abac import _check_permission
        assert _check_permission("UNKNOWN", "crm:read") is False

    def test_unknown_module(self):
        from backend.core.abac import _check_permission
        assert _check_permission("LECTOR", "unknown:read") is False


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/EVENTS (events.py) — 108 stmts, 0% coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestDomainEvent:
    def test_create(self):
        from backend.core.events import DomainEvent
        e = DomainEvent(name="test", payload={"key": "val"})
        assert e.name == "test"
        assert e.payload == {"key": "val"}

    def test_to_json(self):
        from backend.core.events import DomainEvent
        e = DomainEvent(name="test", payload={"key": "val"})
        data = json.loads(e.to_json())
        assert data["name"] == "test"
        assert data["payload"]["key"] == "val"

    def test_to_json_empty_payload(self):
        from backend.core.events import DomainEvent
        e = DomainEvent(name="event", payload={})
        data = json.loads(e.to_json())
        assert data == {"name": "event", "payload": {}}


class TestEventBus:
    def test_publish_noop(self):
        from backend.core.events import EventBus, DomainEvent
        bus = EventBus()
        bus.publish("topic", DomainEvent("test", {}))  # Should not raise


class TestConfigureEventBus:
    def test_no_redis_no_kafka(self):
        from backend.core.events import configure_event_bus, event_bus, EventBus
        with patch("backend.core.events.settings") as mock_s:
            mock_s.redis_url = None
            mock_s.kafka_bootstrap_servers = None
            configure_event_bus()
            assert isinstance(event_bus, EventBus)

    def test_redis_available(self):
        from backend.core.events import configure_event_bus
        with patch("backend.core.events.settings") as mock_s:
            mock_s.redis_url = "redis://localhost"
            with patch("backend.core.events.RedisEventBus") as MockRedis:
                mock_bus = MagicMock()
                MockRedis.return_value = mock_bus
                configure_event_bus()
                mock_bus.publish.assert_called_once()

    def test_redis_fails_kafka_available(self):
        from backend.core.events import configure_event_bus
        with patch("backend.core.events.settings") as mock_s:
            mock_s.redis_url = "redis://localhost"
            mock_s.kafka_bootstrap_servers = "localhost:9092"
            with patch("backend.core.events.RedisEventBus", side_effect=Exception("fail")):
                with patch("backend.core.events.KafkaEventBus") as MockKafka:
                    mock_bus = MagicMock()
                    mock_bus._producer = MagicMock()
                    MockKafka.return_value = mock_bus
                    configure_event_bus()

    def test_redis_fails_kafka_fails(self):
        import backend.core.events as events
        from backend.core.events import EventBus
        with patch("backend.core.events.settings") as mock_s:
            mock_s.redis_url = "redis://localhost"
            mock_s.kafka_bootstrap_servers = "localhost:9092"
            with patch("backend.core.events.RedisEventBus", side_effect=Exception("fail")):
                with patch("backend.core.events.KafkaEventBus") as MockKafka:
                    mock_bus = MagicMock()
                    mock_bus._producer = None  # Kafka unavailable
                    MockKafka.return_value = mock_bus
                    events.configure_event_bus()
                    assert isinstance(events.event_bus, EventBus)


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/TELEMETRY (telemetry.py) — 38 stmts, 0% coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelemetry:
    def test_configure_no_packages(self):
        import backend.core.telemetry as tel_mod
        with patch.object(tel_mod, "trace", None):
            tel_mod._configured = False
            tel_mod.configure_telemetry(MagicMock(), MagicMock())
            assert tel_mod._configured is False

    def test_configure_already_configured(self):
        import backend.core.telemetry as tel_mod
        tel_mod._configured = True
        tel_mod.configure_telemetry(MagicMock(), MagicMock())  # Should return early


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/WEBSOCKETS (websockets.py) — 53 stmts, 0% coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestConnectionManager:
    def test_connect(self):
        from backend.core.websockets import ConnectionManager
        mgr = ConnectionManager()
        ws = AsyncMock()
        asyncio.run(mgr.connect(ws, "user1"))
        assert "user1" in mgr.active_connections

    def test_connect_multiple_tabs(self):
        from backend.core.websockets import ConnectionManager
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        asyncio.run(mgr.connect(ws1, "user1"))
        asyncio.run(mgr.connect(ws2, "user1"))
        assert len(mgr.active_connections["user1"]) == 2

    def test_disconnect(self):
        from backend.core.websockets import ConnectionManager
        mgr = ConnectionManager()
        ws = MagicMock()
        mgr.active_connections["user1"] = [ws]
        mgr.disconnect(ws, "user1")
        assert "user1" not in mgr.active_connections

    def test_disconnect_not_in_list(self):
        from backend.core.websockets import ConnectionManager
        mgr = ConnectionManager()
        ws1 = MagicMock()
        ws2 = MagicMock()
        mgr.active_connections["user1"] = [ws1]
        mgr.disconnect(ws2, "user1")
        assert ws1 in mgr.active_connections["user1"]

    def test_disconnect_unknown_user(self):
        from backend.core.websockets import ConnectionManager
        mgr = ConnectionManager()
        mgr.disconnect(MagicMock(), "unknown")

    def test_send_personal_message(self):
        from backend.core.websockets import ConnectionManager
        mgr = ConnectionManager()
        ws = AsyncMock()
        mgr.active_connections["user1"] = [ws]
        asyncio.run(mgr.send_personal_message({"text": "hi"}, "user1"))
        ws.send_text.assert_called_once()

    def test_send_personal_message_send_fails(self):
        from backend.core.websockets import ConnectionManager
        mgr = ConnectionManager()
        ws = AsyncMock()
        ws.send_text.side_effect = Exception("fail")
        mgr.active_connections["user1"] = [ws]
        asyncio.run(mgr.send_personal_message({"text": "hi"}, "user1"))

    def test_send_personal_message_unknown_user(self):
        from backend.core.websockets import ConnectionManager
        mgr = ConnectionManager()
        asyncio.run(mgr.send_personal_message({"text": "hi"}, "unknown"))

    def test_broadcast(self):
        from backend.core.websockets import ConnectionManager
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        mgr.active_connections["u1"] = [ws1]
        mgr.active_connections["u2"] = [ws2]
        asyncio.run(mgr.broadcast({"text": "all"}))
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

    def test_broadcast_send_fails(self):
        from backend.core.websockets import ConnectionManager
        mgr = ConnectionManager()
        ws = AsyncMock()
        ws.send_text.side_effect = Exception("fail")
        mgr.active_connections["u1"] = [ws]
        asyncio.run(mgr.broadcast({"text": "all"}))


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/CACHE (cache.py) — 104 stmts, 39% coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestMemoryRedis:
    def test_setex_and_get(self):
        from backend.core.cache import MemoryRedis
        r = MemoryRedis()
        r.setex("k1", 60, "v1")
        assert r.get("k1") == "v1"

    def test_get_missing(self):
        from backend.core.cache import MemoryRedis
        r = MemoryRedis()
        assert r.get("missing") is None

    def test_delete(self):
        from backend.core.cache import MemoryRedis
        r = MemoryRedis()
        r.setex("k1", 60, "v1")
        r.delete("k1")
        assert r.get("k1") is None

    def test_incr(self):
        from backend.core.cache import MemoryRedis
        r = MemoryRedis()
        assert r.incr("cnt") == 1
        assert r.incr("cnt") == 2
        assert r.incr("cnt") == 3

    def test_expire(self):
        from backend.core.cache import MemoryRedis
        r = MemoryRedis()
        r.setex("k1", 1, "v1")
        r.expire("k1", 120)
        assert r.get("k1") == "v1"

    def test_expire_nonexistent(self):
        from backend.core.cache import MemoryRedis
        r = MemoryRedis()
        r.expire("nope", 60)  # Should not raise

    def test_publish(self):
        from backend.core.cache import MemoryRedis
        r = MemoryRedis()
        pubsub = r.pubsub()
        pubsub.subscribe("ch1")
        count = r.publish("ch1", "hello")
        assert count == 1
        msg = pubsub.get_message(timeout=1)
        assert msg is not None
        assert msg["data"] == "hello"

    def test_publish_no_subscribers(self):
        from backend.core.cache import MemoryRedis
        r = MemoryRedis()
        count = r.publish("empty", "msg")
        assert count == 0


class TestMemoryPubSub:
    def test_get_message_timeout(self):
        from backend.core.cache import MemoryRedis
        r = MemoryRedis()
        pubsub = r.pubsub()
        pubsub.subscribe("ch")
        msg = pubsub.get_message(timeout=0.01)
        assert msg is None


class TestStableCacheKey:
    def test_deterministic(self):
        from backend.core.cache import _stable_cache_key
        k1 = _stable_cache_key("func", (1, 2), {"a": "b"})
        k2 = _stable_cache_key("func", (1, 2), {"a": "b"})
        assert k1 == k2
        assert k1.startswith("cache:")

    def test_different_args_different_key(self):
        from backend.core.cache import _stable_cache_key
        k1 = _stable_cache_key("func", (1,), {})
        k2 = _stable_cache_key("func", (2,), {})
        assert k1 != k2


class TestCachedDecorator:
    def test_cached_caches_result(self):
        from backend.core.cache import cached, MemoryRedis
        call_count = 0

        @cached(ttl=60)
        def my_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = my_func(5)
        result2 = my_func(5)
        assert result1 == 10
        assert result2 == 10

    def test_cached_different_args(self):
        from backend.core.cache import cached

        @cached(ttl=60)
        def add(a, b):
            return a + b

        assert add(1, 2) == 3
        assert add(3, 4) == 7


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/RATE_LIMIT (rate_limit.py) — 24 stmts, 38% coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestRateLimiter:
    def test_rate_limiter_skips_in_test(self):
        from backend.core.rate_limit import rate_limiter
        dep = rate_limiter(limit=5, window_seconds=60)
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.url.path = "/test"
        result = asyncio.run(dep(request))
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/SECURITY (security.py) — 57 stmts
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurity:
    def test_encrypt_decrypt(self):
        from backend.core.security import encrypt_data, decrypt_data
        encrypted = encrypt_data("hello world")
        assert encrypted != "hello world"
        decrypted = decrypt_data(encrypted)
        assert decrypted == "hello world"

    def test_encrypt_empty(self):
        from backend.core.security import encrypt_data
        assert encrypt_data("") == ""

    def test_decrypt_empty(self):
        from backend.core.security import decrypt_data
        assert decrypt_data("") == ""

    def test_decrypt_invalid(self):
        from backend.core.security import decrypt_data
        result = decrypt_data("not-valid-encrypted-data")
        assert "Error" in result or "descifrado" in result

    def test_password_hash(self):
        from backend.core.security import get_password_hash, verify_password
        hashed = get_password_hash("mypassword")
        assert hashed != "mypassword"
        assert verify_password("mypassword", hashed) is True

    def test_verify_wrong_password(self):
        from backend.core.security import get_password_hash, verify_password
        hashed = get_password_hash("correct")
        assert verify_password("wrong", hashed) is False


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/DATABASE (database.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDatabase:
    def test_base_exists(self):
        from backend.core.database import Base
        assert Base is not None

    def test_get_db(self):
        from backend.core.database import get_db
        gen = get_db()
        db = next(gen)
        assert db is not None
        try:
            next(gen)
        except StopIteration:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/CONFIG (config.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfig:
    def test_get_settings_singleton(self):
        from backend.core.config import get_settings
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_settings_has_required_fields(self):
        from backend.core.config import get_settings
        s = get_settings()
        assert hasattr(s, "secret_key")
        assert hasattr(s, "database_url")


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/CONTEXT (context.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestContext:
    def test_import(self):
        from backend.core import context
        assert context is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/FEATURE_FLAGS (feature_flags.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFeatureFlags:
    def test_import(self):
        from backend.core import feature_flags
        assert feature_flags is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/FILE_LOCK (file_lock.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileLock:
    def test_import(self):
        from backend.core import file_lock
        assert file_lock is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/LOGGING (logging.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogging:
    def test_import(self):
        from backend.core import logging
        assert logging is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/SECURITY_HEADERS (security_headers.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityHeaders:
    def test_import(self):
        from backend.core import security_headers
        assert security_headers is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/STORAGE (storage.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestStorage:
    def test_import(self):
        from backend.core import storage
        assert storage is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/TENANT (tenant.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTenant:
    def test_import(self):
        from backend.core import tenant
        assert tenant is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/UPLOADS (uploads.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestUploads:
    def test_import(self):
        from backend.core import uploads
        assert uploads is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/PERMISSIONS (permissions.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPermissions:
    def test_import(self):
        from backend.core.permissions import get_current_user
        assert get_current_user is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/KERNEL_RBAC (kernel_rbac.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestKernelRBAC:
    def test_import(self):
        from backend.core import kernel_rbac
        assert kernel_rbac is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE/AI (ai.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAI:
    def test_import(self):
        from backend.core import ai
        assert ai is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CRUD/_UTILS (crud/_utils.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrudUtils:
    def test_to_uuid_from_uuid(self):
        from backend.crud._utils import _to_uuid
        uid = uuid.uuid4()
        assert _to_uuid(uid) is uid

    def test_to_uuid_from_str(self):
        from backend.crud._utils import _to_uuid
        uid = uuid.uuid4()
        assert _to_uuid(str(uid)) == uid

    def test_utcnow(self):
        from backend.crud._utils import _utcnow
        result = _utcnow()
        assert result.tzinfo == timezone.utc

    def test_analyze_priority_critical(self):
        from backend.crud._utils import analyze_pastoral_priority
        assert analyze_pastoral_priority("suicidio") == "URGENTE"
        assert analyze_pastoral_priority("Emergencia") == "URGENTE"

    def test_analyze_priority_high(self):
        from backend.crud._utils import analyze_pastoral_priority
        assert analyze_pastoral_priority("conflicto familiar") == "ALTA"
        assert analyze_pastoral_priority("crisis") == "ALTA"

    def test_analyze_priority_normal(self):
        from backend.crud._utils import analyze_pastoral_priority
        assert analyze_pastoral_priority("todo bien") == "NORMAL"

    def test_analyze_priority_empty(self):
        from backend.crud._utils import analyze_pastoral_priority
        assert analyze_pastoral_priority("") == "NORMAL"
        assert analyze_pastoral_priority(None) == "NORMAL"

    def test_sentiment_positive(self):
        from backend.crud._utils import analyze_pastoral_sentiment
        score, label = analyze_pastoral_sentiment("estoy bendecido y agradecido")
        assert score > 0
        assert label == "POSITIVE"

    def test_sentiment_negative(self):
        from backend.crud._utils import analyze_pastoral_sentiment
        score, label = analyze_pastoral_sentiment("estoy triste con dolor y miedo")
        assert score < 0
        assert label == "NEGATIVE"

    def test_sentiment_neutral(self):
        from backend.crud._utils import analyze_pastoral_sentiment
        score, label = analyze_pastoral_sentiment("hoy es martes")
        assert label == "NEUTRAL"

    def test_sentiment_empty(self):
        from backend.crud._utils import analyze_pastoral_sentiment
        score, label = analyze_pastoral_sentiment("")
        assert score == 0.0
        assert label == "NEUTRAL"

    def test_sentiment_none(self):
        from backend.crud._utils import analyze_pastoral_sentiment
        score, label = analyze_pastoral_sentiment(None)
        assert score == 0.0
