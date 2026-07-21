"""Rate limiting + DoS protection.

Archivo consolidado (TKT-200 + sistema preservado). Contiene DOS sistemas de rate-limiting:

1. **Pre-existing ``rate_limiter``** (preservado para backward-compat): dependency
   Redis-based usado por ``backend/api/workspace_incidents.py``,
   ``backend/api/workspace_compliance.py``, ``backend/api/auth_v3.py``.
   En pytest / cuando Redis está en ``MemoryRedis``, esta función es NO-OP
   (no bloquea el request). NO se migra a slowapi porque está fuera del scope
   de TKT-200.

2. **Nuevo ``academy_limiter``** (slowapi-based, TKT-200): Limiter instance
   compartido que el módulo ``backend.api.academy`` decora en sus endpoints
   hot. Tiene pytest-bypass global, opt-in via ``FORCE_RATE_LIMIT=1``,
   per-user keying con bypass manager/admin vía ``request.state``.
"""

from __future__ import annotations

import logging
import os

from fastapi import HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.core.cache import MemoryRedis, get_redis
from backend.core.config import get_settings

logger = logging.getLogger(__name__)


# ── PRESERVED: Redis-based dependency rate-limiter ────────────────────────
# Preservado para backward-compat con workspace_incidents, workspace_compliance
# y auth_v3. Ver nota de archivo. Drift: NOOP en pytest + MemoryRedis.


def rate_limiter(limit: int = 5, window_seconds: int = 60):
    async def dependency(request: Request) -> None:
        if os.getenv("PYTEST_CURRENT_TEST"):
            return
        if get_settings().environment.strip().lower() in {"test", "testing"}:
            return
        redis_client = get_redis()

        # MemoryRedis no es seguro con múltiples workers — el límite
        # se reinicia por worker y no hay estado compartido.
        if isinstance(redis_client, MemoryRedis):
            logger.warning(
                "Rate limiter usando MemoryRedis: el límite no se aplica "
                "correctamente con múltiples workers. Configura Redis real "
                "para rate limiting en producción."
            )
            return

        identifier = request.client.host if request.client else "anonymous"
        key = f"rate:{identifier}:{request.url.path}"
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, window_seconds)
        if current > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests, please slow down.",
            )

    return dependency


# ── NUEVO: slowapi-based limiter (TKT-200) ────────────────────────────


PYTEST_BYPASS_VAR = "PYTEST_CURRENT_TEST"
FORCE_RATE_LIMIT_VAR = "FORCE_RATE_LIMIT"


def _academy_key_func(request: Request) -> str | None:
    """Compute the rate-limit key for a request.

    Returns ``None`` to bypass (slowapi treats ``None`` as "skip this check"),
    which we use for managers/admins AND for pytest runs (so we don't 429
    ourselves during the suite of 100+ tests).
    """
    # Pytest global bypass. Specific tests use FORCE_RATE_LIMIT=1 to opt-in.
    if os.getenv(PYTEST_BYPASS_VAR) and not os.getenv(FORCE_RATE_LIMIT_VAR):
        return None

    # Manager / admin bypass — populated by ``require_permission`` side-effect
    # on ``request.state.is_unlimited_user``.
    if getattr(request.state, "is_unlimited_user", False):
        return None

    # Authenticated user → per-user bucket. Persistente entre IPs compartidos
    # (e.g. NAT en la iglesia) — un estudiante abusivo no bloquea a sus pares.
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    # Anonymous → per-IP (defensa contra DoS sin auth).
    return f"ip:{get_remote_address(request)}"


academy_limiter = Limiter(
    key_func=_academy_key_func,
    headers_enabled=True,
    default_limits=[],  # los límites se aplican via @academy_limiter.limit en cada endpoint
    storage_uri="memory://",
)


__all__ = [
    "rate_limiter",  # preserved: Redis-based dependency (workspaces + auth_v3)
    "academy_limiter",  # TKT-200
    "_academy_key_func",
    "PYTEST_BYPASS_VAR",
    "FORCE_RATE_LIMIT_VAR",
]
