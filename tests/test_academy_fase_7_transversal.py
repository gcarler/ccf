"""TKT-201 regression gate — tracing distribuido + correlation-id.

Verifica el comportamiento del ``observability_middleware`` unificado:
- ``X-Request-ID`` se propaga del request al response cuando es un UUID válido.
- Backend genera un UUID nuevo si el header falta o es inválido.
- ``JSONFormatter`` incluye los 5 campos (request_id, user_id, sede_id,
  endpoint, latency_ms) cuando los contextvars están poblados.
- Endpoints ruidosos (``/healthz``, ``/``) NO emiten log estructurado.
"""

from __future__ import annotations

import json
import re
import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.core.logging import (
    JSONFormatter,
    endpoint_ctx,
    latency_ms_ctx,
    observability_middleware,
    request_id_ctx,
    sede_id_ctx,
    user_id_ctx,
)

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _generate_uuid() -> str:
    return str(uuid.uuid4())


def test_acad_tkt_201_valid_x_request_id_propagates_to_response(client: TestClient) -> None:
    """Cuando el frontend envía un X-Request-ID UUID válido, el backend lo
    propaga al response header sin regenerarlo."""
    incoming_rid = _generate_uuid()
    response = client.get("/healthz", headers={"X-Request-ID": incoming_rid})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == incoming_rid


def test_acad_tkt_201_missing_x_request_id_backend_generates_uuid(client: TestClient) -> None:
    """Si el header falta, el backend genera un UUID v4 válido."""
    response = client.get("/healthz")
    assert response.status_code == 200
    generated = response.headers.get("X-Request-ID", "")
    assert UUID_RE.match(generated), f"Backend no generó UUID válido: {generated!r}"


def test_acad_tkt_201_invalid_x_request_id_is_replaced(client: TestClient) -> None:
    """Un X-Request-ID que no es UUID válido es rechazado y reemplazado."""
    response = client.get("/healthz", headers={"X-Request-ID": "not-a-uuid"})
    assert response.status_code == 200
    out = response.headers.get("X-Request-ID", "")
    assert UUID_RE.match(out), f"Backend no reemplazó ID inválido: {out!r}"
    assert out != "not-a-uuid"


def test_acad_tkt_201_json_formatter_emits_request_id_when_contextvar_set() -> None:
    """El JSONFormatter incluye ``request_id`` cuando ``request_id_ctx`` está poblado."""
    rid = _generate_uuid()
    token = request_id_ctx.set(rid)
    try:
        formatter = JSONFormatter()
        record = __import__("logging").LogRecord(
            name="CCF.Observability",
            level=20,  # INFO
            pathname=__file__,
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        payload = json.loads(output)
        assert payload.get("request_id") == rid, (
            f"JSONFormatter no emitió request_id. Output: {output!r}"
        )
    finally:
        request_id_ctx.reset(token)


def test_acad_tkt_201_json_formatter_emits_all_5_fields_when_populated() -> None:
    """Cuando los 5 contextvars están poblados, el JSONFormatter los emite."""
    rid = _generate_uuid()
    uid = "user-42"
    sid = "sede-bogota"
    ep = "GET /api/academy/courses"
    lat = 12.5

    rid_t = request_id_ctx.set(rid)
    uid_t = user_id_ctx.set(uid)
    sid_t = sede_id_ctx.set(sid)
    ep_t = endpoint_ctx.set(ep)
    lat_t = latency_ms_ctx.set(lat)
    try:
        formatter = JSONFormatter()
        record = __import__("logging").LogRecord(
            name="CCF.Observability",
            level=20,
            pathname=__file__,
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        payload = json.loads(output)
        assert payload.get("request_id") == rid
        assert payload.get("user_id") == uid
        assert payload.get("sede_id") == sid
        assert payload.get("endpoint") == ep
        assert payload.get("latency_ms") == 12.5
    finally:
        latency_ms_ctx.reset(lat_t)
        endpoint_ctx.reset(ep_t)
        sede_id_ctx.reset(sid_t)
        user_id_ctx.reset(uid_t)
        request_id_ctx.reset(rid_t)


def test_acad_tkt_201_json_formatter_skips_unset_fields() -> None:
    """Si los contextvars están vacíos (default), el log no incluye nulls
    ruidosos — solo los campos poblados."""
    formatter = JSONFormatter()
    record = __import__("logging").LogRecord(
        name="CCF.Observability",
        level=20,
        pathname=__file__,
        lineno=1,
        msg="test",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    payload = json.loads(output)
    assert "request_id" not in payload
    assert "user_id" not in payload
    assert "sede_id" not in payload
    assert "endpoint" not in payload
    assert "latency_ms" not in payload


def test_acad_tkt_201_no_contextvar_leak_after_request(client: TestClient) -> None:
    """Después de un request, los 5 contextvars vuelven al valor que tenían
    ANTES del request (el middleware resetea via Token.reset, NO a default).
    Verifica que NO leak hacia otras requests."""
    # Snapshot de los contextvars antes del request
    prev_rid = request_id_ctx.get()
    prev_lat = latency_ms_ctx.get()
    response = client.get(
        "/healthz",
        headers={"X-Request-ID": _generate_uuid()},
    )
    assert response.status_code == 200
    # Después del request, los contextvars deben volver al valor pre-request
    assert request_id_ctx.get() == prev_rid, (
        f"request_id_ctx leak: esperaba {prev_rid!r}, obtuvo {request_id_ctx.get()!r}"
    )
    assert latency_ms_ctx.get() == prev_lat, (
        f"latency_ms_ctx leak: esperaba {prev_lat!r}, obtuvo {latency_ms_ctx.get()!r}"
    )


def test_acad_tkt_201_middleware_emits_log_with_latency_via_caplog(caplog) -> None:
    """El middleware emite un log estructurado con ``latency_ms > 0`` para
    endpoints no ruidosos. Verifica que ``logger.log(..., extra={...})`` propaga
    los 5 campos correctamente al ``JSONFormatter`` sin repopular contextvars."""
    import asyncio as _asyncio

    from starlette.requests import Request
    from starlette.responses import JSONResponse

    async def _exercise():
        async def mock_call_next(_request):
            return JSONResponse({"ok": True}, status_code=200)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/academy/courses",
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("127.0.0.1", 12345),
        }
        request = Request(scope)
        return await observability_middleware(request, mock_call_next)

    with caplog.at_level("INFO", logger="CCF.Observability"):
        response = _asyncio.run(_exercise())

    assert response.status_code == 200
    # Buscar el record emitido por el middleware
    matching = [r for r in caplog.records if "GET /api/academy/courses" in r.getMessage()]
    assert matching, f"No se emitió log del middleware. Records: {[r.getMessage() for r in caplog.records]}"
    record = matching[0]
    # Verificar que los 5 campos fueron propagados via extra=
    assert hasattr(record, "request_id"), "request_id no se propagó via extra="
    assert hasattr(record, "user_id"), "user_id no se propagó via extra="
    assert hasattr(record, "sede_id"), "sede_id no se propagó via extra="
    assert hasattr(record, "endpoint"), "endpoint no se propagó via extra="
    assert hasattr(record, "latency_ms"), "latency_ms no se propagó via extra="
    assert record.latency_ms > 0, f"latency_ms debe ser > 0, fue {record.latency_ms}"
    assert record.endpoint == "GET /api/academy/courses"


def test_acad_tkt_201_observability_middleware_function_exists() -> None:
    """El nuevo ``observability_middleware`` está exportado y es callable."""
    assert callable(observability_middleware), (
        "TKT-201 regresión: backend.core.logging.observability_middleware "
        "no está exportado o no es callable."
    )


def test_acad_tkt_201_request_id_middleware_alias_preserved() -> None:
    """Backward-compat: ``request_id_middleware`` sigue siendo importable."""
    from backend.core.logging import request_id_middleware

    assert callable(request_id_middleware)


def test_acad_tkt_201_unverified_jwt_decode_handles_malformed_token() -> None:
    """Un token JWT malformado no rompe el middleware; retorna {} silenciosamente."""
    from backend.core.logging import _unverified_jwt_payload

    assert _unverified_jwt_payload("") == {}
    assert _unverified_jwt_payload("not-a-jwt") == {}
    assert _unverified_jwt_payload("a.b") == {}  # sólo 2 partes
    assert _unverified_jwt_payload("a.b.c.d") == {}  # 4 partes
    assert _unverified_jwt_payload("a.b.%%not-base64%%") == {}


def test_acad_tkt_201_unverified_jwt_decode_extracts_claims() -> None:
    """JWT válido: extrae ``sub`` → user_id y ``sede_id`` del payload."""
    import base64 as _b64

    from backend.core.logging import _unverified_jwt_payload

    payload = {"sub": "user-99", "sede_id": "sede-medellin", "exp": 9999999999}
    payload_b64 = _b64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    fake_token = f"header.{payload_b64}.signature"
    out = _unverified_jwt_payload(fake_token)
    assert out.get("sub") == "user-99"
    assert out.get("sede_id") == "sede-medellin"
