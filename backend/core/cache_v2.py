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


def _to_jsonable(value: Any) -> Any:
    """Recursively convert Pydantic models (and containers of them) to JSON-safe types.

    Pydantic v2 models expose ``model_dump()``; Pydantic v1 exposes ``dict()``.
    Either way, the original instance is not JSON-serializable directly \u2014
    ``json.dumps(model, default=str)`` falls back to ``str(model)`` which
    produces a debug string like ``id=UUID('...') name='Alex'...``. Round-
    tripping that through ``json.loads`` yields a list of strings, which
    FastAPI's ``response_model`` then fails to validate with
    ``Input should be a valid dictionary or object to extract fields from``.

    This helper walks the value once and produces a structure that
    ``json.dumps`` can serialize without falling back to ``str()``.
    Handles ``list``/``tuple``/``dict`` containers (including nested
    combinations) and Pydantic models at any depth.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return _to_jsonable(value.model_dump())
    if hasattr(value, "dict") and not isinstance(value, type):
        # ``.dict()`` was Pydantic v1's API; kept for backwards compat
        # with any leftover v1 models. Skip ``type`` because every class
        # has a ``.dict`` attribute via ``__class__``.
        return _to_jsonable(value.dict())
    if hasattr(value, "_sa_instance_state"):
        # SQLAlchemy model — extract column values, skip internal SA keys.
        return _to_jsonable({
            k: v for k, v in value.__dict__.items()
            if not k.startswith("_")
        })
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    # Pydantic v2 ``RootModel`` / ``Generic`` and other exotic bases \u2014
    # fall back to str repr so we don't silently drop the cached entry
    # (matches the prior behavior of ``json.dumps(..., default=str)``).
    return str(value)


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
                # Convert Pydantic models \u2014 and any list/tuple/dict that
                # contains them \u2014 into plain JSON-safe types BEFORE
                # ``json.dumps`` so the cache stores a real dict/list
                # structure instead of the ``str(model)`` debug repr.
                # Without this, ``List[PastoralProfileRead]`` would round-
                # trip as a list of strings and FastAPI's response_model
                # validation would fail with "Input should be a valid
                # dictionary or object to extract fields from" on the
                # next cache hit.
                serializable = _to_jsonable(result)
                redis.setex(key, ttl, json.dumps(serializable, default=str))
            except (TypeError, ValueError, ConnectionError) as exc:
                logger.debug("Cache store skipped: %s", exc)

            return result

        return wrapper  # type: ignore[return-value]

    return decorator
