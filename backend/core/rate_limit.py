import logging
import os

from fastapi import HTTPException, Request, status

from backend.core.cache import MemoryRedis, get_redis
from backend.core.config import get_settings

logger = logging.getLogger(__name__)


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
