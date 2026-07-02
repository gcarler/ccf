"""Cache helpers for FastAPI endpoints with non-serializable dependencies.

Extends ``backend.core.cache`` with decorators that safely ignore SQLAlchemy
Session, Request, and other non-JSON-serializable arguments when building
cache keys.
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
from typing import Any, Callable, TypeVar

from backend.core.cache import get_redis

logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


def _is_serializable(value: Any) -> bool:
    """Return True if value can be JSON-serialized in a stable way."""
    if value is None:
        return True
    if isinstance(value, (str, int, float, bool, list, dict, tuple)):
        return True
    return False


def _build_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Build a deterministic cache key, skipping non-serializable args."""
    serializable_args = tuple(
        arg for arg in args if _is_serializable(arg)
    )
    serializable_kwargs = {
        k: v for k, v in kwargs.items() if _is_serializable(v)
    }
    payload = json.dumps(
        {"args": serializable_args, "kwargs": serializable_kwargs},
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"cache:v2:{func_name}:{digest}"


def cached_public(ttl: int = 300) -> Callable[[F], F]:
    """Cache decorator for public FastAPI endpoints.

    Skips SQLAlchemy Session, Request, and other non-serializable arguments
    when building the cache key so that ``Depends(get_db)`` does not bust
    the cache on every request.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            redis = get_redis()
            key = _build_cache_key(func.__name__, args, kwargs)

            cached_val = redis.get(key)
            if cached_val:
                try:
                    return json.loads(cached_val)
                except (json.JSONDecodeError, TypeError):
                    return cached_val

            result = func(*args, **kwargs)

            try:
                serializable = result
                if hasattr(result, "model_dump"):
                    serializable = result.model_dump()
                elif hasattr(result, "dict"):
                    serializable = result.dict()
                redis.setex(key, ttl, json.dumps(serializable, default=str))
            except (TypeError, ValueError, ConnectionError) as exc:
                logger.debug("Cache store skipped: %s", exc)

            return result

        return wrapper  # type: ignore[return-value]

    return decorator
