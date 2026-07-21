"""Tests de alto leverage para subir el coverage global 38.40% → ≥39%.

Per ``pytest.ini``: ``--cov-fail-under=39``. Este módulo añade cobertura
dirigida a archivos con alta relación líneas-cubiertas-por-test:

- ``backend/crud/_utils.py`` (heurísticas Optimus Brain + ``_slugify`` +
  ``_coerce_uuid_or_404``): funciones puras, ningún side effect.
- ``backend/services/payments.py`` (MercadoPago SDK mockeado vía
  ``_get_sdk`` + ``PaymentPreference``/``PaymentResult`` dataclasses).
- ``backend/services/scheduler.py`` (wrappers de scheduler, mocks de
  ``SessionLocal`` + ``threading.Thread`` + dependencias evangelismo).

Las queries pesdas (mock_chain sobre ``db.query()``) se cubren sólo para
path cortos para evitar alucinaciones. La meta no es 100% de cobertura
sobre estos archivos, sino aportar suficientes líneas (≈180‑200) para
cubrir el gap global de 0.60%.
"""

from __future__ import annotations

import datetime as dt
import uuid as _uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def _reset_telemetry_state_globally():
    """Resetea ``_configured`` en ``backend.core.telemetry`` antes de cada test.

    Sin este fixture, los tests que mutan ``_configured=True`` (en este
    mismo modulo) contaminarian el estado global para tests posteriores
    de la suite que importen ``backend.core.telemetry``.
    """
    from backend.core import telemetry as telemetry_module

    saved = telemetry_module._configured
    telemetry_module._configured = False
    yield
    telemetry_module._configured = saved


# ── backend/crud/_utils.py ──────────────────────────────────────────────
from backend.crud._utils import (
    _coerce_uuid_or_404,
    _slugify,
    _utcnow,
    analyze_pastoral_priority,
    analyze_pastoral_sentiment,
)


# ── _coerce_uuid_or_404 ────────────────────────────────────────────────


def test_coerce_uuid_or_404_accepts_valid_uuid_string():
    u = _uuid.uuid4()
    assert _coerce_uuid_or_404(str(u)) == u


def test_coerce_uuid_or_404_returns_uuid_for_uuid_object():
    u = _uuid.uuid4()
    coerced = _coerce_uuid_or_404(u)
    # Identity assertion is brittle across pytest/coverage instrumentation;
    # equality on UUID value is the canonical equivalence.
    assert coerced == u


def test_coerce_uuid_or_404_raises_404_for_malformed_string():
    with pytest.raises(HTTPException) as exc:
        _coerce_uuid_or_404("not-a-uuid")
    assert exc.value.status_code == 404
    assert exc.value.detail == "Resource not found"


def test_coerce_uuid_or_404_uses_custom_detail():
    with pytest.raises(HTTPException) as exc:
        _coerce_uuid_or_404("xyz", detail="Custom not found")
    assert exc.value.status_code == 404
    assert exc.value.detail == "Custom not found"


# ── _slugify ───────────────────────────────────────────────────────────


def test_slugify_lowercases():
    assert _slugify("HELLO") == "hello"


def test_slugify_strips_accents_nfd():
    assert _slugify("Canción") == "cancion"


def test_slugify_replaces_spaces_with_dash():
    assert _slugify("hello world") == "hello-world"


def test_slugify_collapses_repeated_dashes():
    assert _slugify("hello---world") == "hello-world"


def test_slugify_strips_leading_trailing_dashes():
    assert _slugify("--hello--") == "hello"


def test_slugify_handles_empty_string():
    assert _slugify("") == ""
    assert _slugify(None) == ""  # type: ignore[arg-type]


def test_slugify_combined_accent_and_punctuation():
    assert _slugify(" Canción #2 con ácentos!! ") == "cancion-2-con-acentos"


# ── _utcnow ────────────────────────────────────────────────────────────


def test_utcnow_returns_timezone_aware_datetime():
    now = _utcnow()
    assert isinstance(now, dt.datetime)
    assert now.tzinfo is not None
    assert now.utcoffset() == dt.timedelta(0)


# ── analyze_pastoral_priority ──────────────────────────────────────────


def test_pastoral_priority_critical_triggers_urgente():
    assert analyze_pastoral_priority("riesgo de suicidio") == "URGENTE"
    assert analyze_pastoral_priority("violencia doméstica") == "URGENTE"
    assert analyze_pastoral_priority("emergencia familiar") == "URGENTE"


def test_pastoral_priority_high_triggers_alta():
    assert analyze_pastoral_priority("conflicto familiar grave") == "ALTA"
    assert analyze_pastoral_priority("soledad profunda") == "ALTA"
    assert analyze_pastoral_priority("crisis económica") == "ALTA"


def test_pastoral_priority_neutral_is_normal():
    assert analyze_pastoral_priority("nada en particular") == "NORMAL"


def test_pastoral_priority_empty_is_normal():
    assert analyze_pastoral_priority("") == "NORMAL"


# ── analyze_pastoral_sentiment ─────────────────────────────────────────


def test_pastoral_sentiment_positive_dominant():
    score, label = analyze_pastoral_sentiment("mucha paz, fe y esperanza")
    assert label == "POSITIVE"
    assert score > 0


def test_pastoral_sentiment_negative_dominant():
    score, label = analyze_pastoral_sentiment("miedo, angustia, dolor")
    assert label == "NEGATIVE"
    assert score < 0


def test_pastoral_sentiment_neutral_when_empty():
    score, label = analyze_pastoral_sentiment("")
    assert score == 0.0
    assert label == "NEUTRAL"


def test_pastoral_sentiment_neutral_when_balanced():
    """Tie entre positive y negative words → NEUTRAL con score ≈ 0."""
    score, label = analyze_pastoral_sentiment("paz y dolor")
    # pos=1, neg=1 → score = 0/2 = 0 → NEUTRAL
    assert label == "NEUTRAL"


# ── backend/services/payments.py ───────────────────────────────────────
from backend.services.payments import (  # noqa: E402
    PaymentPreference,
    PaymentResult,
    create_donation_preference,
    get_payment_status,
    process_webhook_notification,
)


def test_payment_preference_dataclass_defaults():
    pref = PaymentPreference(amount=100.0, title="Diezmo")
    assert pref.amount == 100.0
    assert pref.title == "Diezmo"
    assert pref.email is None
    assert pref.payment_type_id == "ticket"
    assert pref.installments == 1
    assert pref.metadata == {}


def test_payment_result_dataclass_allows_none_email():
    pr = PaymentResult(
        payment_id=999,
        status="approved",
        status_detail="accredited",
        amount=100.0,
    )
    assert pr.payment_id == 999
    assert pr.email is None


@patch("backend.services.payments._get_sdk")
def test_create_donation_preference_extracts_response(mock_get_sdk):
    mock_sdk = MagicMock()
    mock_get_sdk.return_value = mock_sdk
    mock_sdk.preference().create.return_value = {
        "response": {
            "id": "pref-123",
            "init_point": "https://www.mercadopago.com/checkout/123",
            "sandbox_init_point": "https://sandbox.mercadopago.com/checkout/123",
        }
    }

    pref = PaymentPreference(amount=50.0, title="Diezmo", email="donor@example.com")
    response = create_donation_preference(pref)

    assert response["id"] == "pref-123"
    assert response["init_point"].startswith("https://")
    # Verifica que la metadata source se inyectó
    call_args = mock_sdk.preference().create.call_args
    pref_data = call_args[0][0]
    assert pref_data["metadata"]["source"] == "ccf-donate-web"


@patch("backend.services.payments._get_sdk")
def test_create_donation_preference_propagates_sdk_error(mock_get_sdk):
    mock_sdk = MagicMock()
    mock_get_sdk.return_value = mock_sdk
    mock_sdk.preference().create.side_effect = RuntimeError("MP down")

    pref = PaymentPreference(amount=10.0, title="X")
    with pytest.raises(RuntimeError, match="MP down"):
        create_donation_preference(pref)


@patch("backend.services.payments._get_sdk")
def test_get_payment_status_builds_dataclass(mock_get_sdk):
    mock_sdk = MagicMock()
    mock_get_sdk.return_value = mock_sdk
    mock_sdk.payment().get.return_value = {
        "response": {
            "id": 42,
            "status": "approved",
            "status_detail": "accredited",
            "transaction_amount": "75.50",
            "payer": {"email": "user@x.com", "name": "John"},
        }
    }

    result = get_payment_status(42)
    assert isinstance(result, PaymentResult)
    assert result.payment_id == 42
    assert result.status == "approved"
    assert result.amount == 75.5
    assert result.email == "user@x.com"
    assert result.donor_name == "John"


@patch("backend.services.payments._get_sdk")
def test_get_payment_status_handles_missing_fields(mock_get_sdk):
    mock_sdk = MagicMock()
    mock_get_sdk.return_value = mock_sdk
    mock_sdk.payment().get.return_value = {"response": {}}

    result = get_payment_status(999)
    assert result.payment_id == 999
    assert result.status == "unknown"
    assert result.amount == 0.0


@patch("backend.services.payments._get_sdk")
def test_process_webhook_notification_payment_type_resolves(mock_get_sdk):
    mock_sdk = MagicMock()
    mock_get_sdk.return_value = mock_sdk
    mock_sdk.payment().get.return_value = {
        "response": {
            "id": 555,
            "status": "approved",
            "status_detail": "accredited",
            "transaction_amount": "10.00",
        }
    }

    data = {"type": "payment", "data": {"id": "555"}}
    result = process_webhook_notification(data)
    assert isinstance(result, PaymentResult)
    assert result.payment_id == 555


def test_process_webhook_notification_unknown_type_returns_none():
    assert process_webhook_notification({"type": "test", "data": {}}) is None


@patch("backend.services.payments._get_sdk")
def test_process_webhook_notification_payment_in_action(mock_get_sdk):
    """Webhook con action conteniendo 'payment' pero type distinto."""
    mock_sdk = MagicMock()
    mock_get_sdk.return_value = mock_sdk
    mock_sdk.payment().get.return_value = {
        "response": {
            "id": 777,
            "status": "approved",
            "status_detail": "accredited",
            "transaction_amount": "5.00",
        }
    }
    data = {"type": "plan", "action": "payment.created", "data": {"id": "777"}}
    result = process_webhook_notification(data)
    assert isinstance(result, PaymentResult)
    assert result.payment_id == 777


def test_get_sdk_raises_when_mercadopago_not_installed():
    """Si mercadopago en el módulo es None, _get_sdk raises."""
    with patch("backend.services.payments.mercadopago", None):
        from backend.services.payments import _get_sdk
        with pytest.raises(RuntimeError, match=r"mercadopago.*no.*instalado"):
            _get_sdk()


# ── backend/services/scheduler.py ──────────────────────────────────────
from backend.services.scheduler import (  # noqa: E402
    run_ai_analysis,
    run_session_governance,
    start_background_scheduler,
)


@patch("backend.services.scheduler.run_proactive_analysis", return_value=3)
@patch("backend.services.scheduler.SessionLocal")
def test_run_ai_analysis_calls_proactive_with_session(mock_session_local, mock_proactive):
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    run_ai_analysis()

    mock_session_local.assert_called_once()
    mock_proactive.assert_called_once_with(mock_db)
    mock_db.close.assert_called_once()


@patch("backend.services.scheduler.run_proactive_analysis", return_value=0)
@patch("backend.services.scheduler.SessionLocal")
def test_run_ai_analysis_swallows_proactive_exception(mock_session_local, mock_proactive):
    """Si proactive_analysis levanta, run_ai_analysis NO propaga, db.close igual."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_proactive.side_effect = RuntimeError("AI down")

    run_ai_analysis()  # should NOT raise
    mock_db.close.assert_called_once()


@patch("backend.services.scheduler.sessions_grupo_has_estado_habilitacion", return_value=False)
@patch("backend.services.scheduler.SessionLocal")
def test_run_session_governance_returns_early_when_no_estado(mock_session_local, mock_hab):
    """Cuando estado no inicializado, retorna sin tocar SesionGrupo."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    run_session_governance()

    mock_hab.assert_called_once_with(mock_db)
    mock_db.query.assert_not_called()


@patch("backend.services.scheduler.sessions_grupo_has_estado_habilitacion", return_value=True)
@patch("backend.services.scheduler.SessionLocal")
def test_run_session_governance_commits_when_estado_ok(mock_session_local, mock_hab):
    """Cuando estado=True, ejecuta query+update+commit+close."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # Mock chain: query(SesionGrupo).filter(...).update(...) → returns int
    mock_query_filtered = MagicMock()
    mock_query_filtered.update.return_value = 1
    mock_db.query.return_value.filter.return_value = mock_query_filtered

    run_session_governance()

    mock_db.commit.assert_called_once()
    mock_db.close.assert_called_once()


@patch("backend.services.scheduler.threading.Thread")
def test_start_background_scheduler_creates_daemon_thread(mock_thread_cls):
    """start_background_scheduler lanza un Thread daemon y lo inicia."""
    mock_thread_instance = MagicMock()
    mock_thread_cls.return_value = mock_thread_instance

    start_background_scheduler()

    mock_thread_cls.assert_called_once()
    # Acepta cualquier kwargs (incluyendo daemon=True)
    _, kwargs = mock_thread_cls.call_args
    assert kwargs.get("daemon") is True
    mock_thread_instance.start.assert_called_once()


# ── backend/core/events.py ──────────────────────────────────────────────────
import json  # noqa: E402

from backend.core import events as events_module  # noqa: E402
from backend.core.events import (  # noqa: E402
    DomainEvent,
    EventBus,
    KafkaEventBus,
    RedisEventBus,
    configure_event_bus,
)


def test_domain_event_to_json_serializes_payload():
    """DomainEvent.to_json produce bytes JSON con name+payload."""
    event = DomainEvent(name="user.created", payload={"id": 1, "email": "u@x.com"})
    out = event.to_json()
    decoded = json.loads(out.decode("utf-8"))
    assert decoded["name"] == "user.created"
    assert decoded["payload"] == {"id": 1, "email": "u@x.com"}


def test_event_bus_publish_is_noop():
    """EventBus base.publish() no hace nada."""
    bus = EventBus()
    # No debe levantar, no debe side-effect
    bus.publish("any.topic", DomainEvent("x", {"k": "v"}))


def test_redis_event_bus_publishes_to_redis():
    """RedisEventBus publica a Redis con JSON serializado."""
    bus = RedisEventBus()
    bus._redis = MagicMock()

    event = DomainEvent(name="test.event", payload={"a": 1})
    bus.publish("topic.x", event)

    bus._redis.publish.assert_called_once()
    args = bus._redis.publish.call_args
    assert args[0][0] == "topic.x"
    decoded = json.loads(args[0][1])
    assert decoded["name"] == "test.event"


def test_redis_event_bus_swallows_exception():
    """Si Redis falla, el publicador no propaga la excepción."""
    bus = RedisEventBus()
    bus._redis = MagicMock()
    bus._redis.publish.side_effect = RuntimeError("redis down")

    # No debe levantar
    bus.publish("topic", DomainEvent("x", {"k": "v"}))


def test_kafka_event_bus_publishes_when_producer_exists():
    """KafkaEventBus con producer válido publica + flush."""
    bus = KafkaEventBus.__new__(KafkaEventBus)  # bypass __init__
    bus._producer = MagicMock()

    bus.publish("kafka-topic", DomainEvent("e", {"v": 1}))
    bus._producer.send.assert_called_once()
    bus._producer.flush.assert_called_once()


def test_kafka_event_bus_noop_when_producer_none():
    """Sin producer (init falló), publish es no-op sin levantar."""
    bus = KafkaEventBus.__new__(KafkaEventBus)  # bypass __init__
    bus._producer = None

    bus.publish("kafka-topic", DomainEvent("e", {"v": 1}))


def test_configure_event_bus_noop_when_no_redis_no_kafka(monkeypatch):
    """Sin Redis ni Kafka disponibles → event_bus queda en EventBus no-op."""
    import backend.core.events as events_mod

    # Forzar ningún transporte disponible
    monkeypatch.setattr(events_mod.settings, "redis_url", None)
    monkeypatch.setattr(events_mod.settings, "kafka_bootstrap_servers", None)

    # Reset estado global
    events_mod.event_bus = events_mod.EventBus()

    configure_event_bus()

    assert isinstance(events_mod.event_bus, EventBus)


def test_configure_event_bus_uses_redis_when_available(monkeypatch):
    """Si Redis.url está configurado y funciona, usa RedisEventBus."""
    import backend.core.events as events_mod

    monkeypatch.setattr(events_mod.settings, "redis_url", "redis://localhost:6379")
    monkeypatch.setattr(events_mod.settings, "kafka_bootstrap_servers", None)

    fake_bus = MagicMock()
    fake_bus.publish.return_value = None  # healthcheck OK
    monkeypatch.setattr(events_mod, "RedisEventBus", lambda: fake_bus)

    events_mod.event_bus = events_mod.EventBus()
    configure_event_bus()

    assert events_mod.event_bus is fake_bus
    fake_bus.publish.assert_called_once()


# ── backend/core/telemetry.py ──────────────────────────────────────────────
from backend.core import telemetry as telemetry_module  # noqa: E402


@patch("backend.core.telemetry.trace", None)
@patch("backend.core.telemetry._configured", new=False, create=True)
def test_configure_telemetry_noop_when_opentelemetry_missing(monkeypatch):
    """Si ``trace`` es ``None`` (OpenTelemetry no instalado), la función retorna sin configurar nada."""
    telemetry_module._configured = False
    monkeypatch.setattr(telemetry_module, "trace", None)

    app_mock = MagicMock()
    engine_mock = MagicMock()

    telemetry_module.configure_telemetry(app=app_mock, engine=engine_mock)

    # _configured se mantiene False (no-op path).
    assert telemetry_module._configured is False
    app_mock.assert_not_called()


def test_configure_telemetry_skips_when_already_configured():
    """Si ``_configured=True``, configure_telemetry retorna sin tocar ``trace`` ni SDK."""
    telemetry_module._configured = True

    app_mock = MagicMock()
    engine_mock = MagicMock()

    telemetry_module.configure_telemetry(app=app_mock, engine=engine_mock)

    # _configured sigue True y ningún SDK fue invocado.
    assert telemetry_module._configured is True
    app_mock.assert_not_called()
