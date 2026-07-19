"""Structured JSON logging + observability middleware (TKT-201).

Combines:
- JSONFormatter con 5 campos (request_id, user_id, sede_id, endpoint, latency_ms)
- observability_middleware que extrae X-Request-ID, decodifica JWT sin
  verificar firma para logging, mide latencia, setea contextvars

Mantiene ``request_id_middleware`` como alias para backward compat con
tests existentes.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from logging.config import dictConfig
from typing import Any

from fastapi import Request

# Context vars populated by observability_middleware / auth deps
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")
sede_id_ctx: ContextVar[str] = ContextVar("sede_id", default="")
endpoint_ctx: ContextVar[str] = ContextVar("endpoint", default="")
latency_ms_ctx: ContextVar[float] = ContextVar("latency_ms", default=0.0)

# Endpoints excluidos del tracing activo (alto volumen, baja señal)
NOISY_PATHS = {"/", "/healthz", "/readyz"}

# Regex UUID v1-v5 para validar X-Request-ID entrante
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


_OBSERVABILITY_FIELDS = ("request_id", "user_id", "sede_id", "endpoint", "latency_ms")
_OBSERVABILITY_CONTEXTVARS = {
    "request_id": request_id_ctx,
    "user_id": user_id_ctx,
    "sede_id": sede_id_ctx,
    "endpoint": endpoint_ctx,
    "latency_ms": latency_ms_ctx,
}


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter (TKT-201: 5 campos del observability).

    Lee los 5 campos primero de ``record.__dict__`` (seteados vía ``extra=``
    al loggear), con fallback al contextvar correspondiente. Esto permite
    emitir un log con ``extra={...}`` sin tener que repopular contextvars.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        for field in _OBSERVABILITY_FIELDS:
            value = getattr(record, field, None)
            if value is None or value == "":
                # Fallback al contextvar (caso: log manual sin extra=)
                value = _OBSERVABILITY_CONTEXTVARS[field].get()
            if value and value != 0.0:
                if field == "latency_ms":
                    log_entry[field] = round(float(value), 2)
                else:
                    log_entry[field] = value
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging for production."""

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": JSONFormatter,
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "level": level,
                }
            },
            "root": {
                "handlers": ["default"],
                "level": level,
            },
        }
    )


def _unverified_jwt_payload(token: str) -> dict[str, Any]:
    """Decode JWT payload WITHOUT signature verification — solo para logging.

    Returns {} si el token está malformado, expirado, o no es JWT.
    NO usar para autorización; sólo para extraer ``sub`` y ``sede_id`` con
    fines de observabilidad. La verificación real ocurre en ``get_current_user``.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1]
        # Base64 urlsafe requiere padding múltiplo de 4
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


async def observability_middleware(request: Request, call_next):
    """TKT-201: middleware unificado de observabilidad.

    Responsabilidades:
    1. Extrae o genera ``X-Request-ID`` (UUID v4 si falta o es inválido)
    2. Decodifica JWT del header Authorization (sin verificar firma) para
       extraer ``user_id`` y ``sede_id`` con fines de log
    3. Mide ``latency_ms`` del request
    4. Popula los 5 contextvars que ``JSONFormatter`` lee
    5. Emite un log JSON con el resumen del request (excepto endpoints ruidosos)
    6. Devuelve el response con header ``X-Request-ID`` propagado
    """
    # 1. Request ID — aceptar UUID válido entrante o generar nuevo
    incoming_rid = request.headers.get("X-Request-ID", "")
    request_id = incoming_rid if _UUID_RE.match(incoming_rid) else str(uuid.uuid4())
    request.state.request_id = request_id
    rid_token = request_id_ctx.set(request_id)

    # 2. Endpoint (METHOD + path)
    endpoint = f"{request.method} {request.url.path}"
    ep_token = endpoint_ctx.set(endpoint)

    # 3. User/sede desde JWT (unverified — sólo logging)
    auth_header = request.headers.get("Authorization", "")
    user_id = ""
    sede_id = ""
    if auth_header.lower().startswith("bearer "):
        payload = _unverified_jwt_payload(auth_header[7:].strip())
        user_id = str(payload.get("sub") or payload.get("user_id") or "")
        sede_id = str(payload.get("sede_id") or "")
    uid_token = user_id_ctx.set(user_id) if user_id else None
    sid_token = sede_id_ctx.set(sede_id) if sede_id else None

    # 4. Latency measurement
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        lat_token = latency_ms_ctx.set(latency_ms)
        # Reset contextvars (orden LIFO)
        if lat_token is not None:
            latency_ms_ctx.reset(lat_token)
        if sid_token is not None:
            sede_id_ctx.reset(sid_token)
        if uid_token is not None:
            user_id_ctx.reset(uid_token)
        endpoint_ctx.reset(ep_token)
        request_id_ctx.reset(rid_token)

    # 5. Log estructurado (excepto endpoints ruidosos)
    if request.url.path not in NOISY_PATHS:
        status_code = getattr(response, "status_code", 0)
        log_level = logging.WARNING if status_code >= 500 else logging.INFO
        logging.getLogger("CCF.Observability").log(
            log_level,
            "%s %s -> %d",
            request.method,
            request.url.path,
            status_code,
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "sede_id": sede_id,
                "endpoint": endpoint,
                "latency_ms": latency_ms,
            },
        )

    # 6. Propagar X-Request-ID en response
    response.headers["X-Request-ID"] = request_id
    return response


# Alias para backward compat con tests que importan ``request_id_middleware``
async def request_id_middleware(request: Request, call_next):
    """Backward-compat alias para ``observability_middleware``."""
    return await observability_middleware(request, call_next)


configure_logging()
