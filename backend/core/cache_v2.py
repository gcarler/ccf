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


def _key_value(value: Any) -> tuple[bool, Any]:
    """Return a stable key value, dropping only nested non-serializable values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return True, value
    if isinstance(value, (list, tuple)):
        clean_items = []
        for item in value:
            valid, clean = _key_value(item)
            if valid:
                clean_items.append(clean)
        return True, clean_items
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            valid, clean = _key_value(item)
            if valid:
                result[key] = clean
        return True, result
    return False, None


def _is_serializable(value: Any) -> bool:
    """Return True if value can be represented in a stable cache key."""
    return _key_value(value)[0]


def _to_jsonable(value: Any, seen: set[int] | None = None) -> Any:
    """Recursively convert Pydantic models (and containers of them) to JSON-safe types.

    Pydantic v2 models expose ``model_dump()``; Pydantic v1 exposes ``dict()``.
    Either way, the original instance is not JSON-serializable directly —
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

    if seen is None:
        seen = set()

    val_id = id(value)
    if val_id in seen:
        return None

    seen.add(val_id)
    try:
        if hasattr(value, "model_dump"):
            return _to_jsonable(value.model_dump(), seen)
        if hasattr(value, "dict") and not isinstance(value, type):
            # ``.dict()`` was Pydantic v1's API; kept for backwards compat
            # with any leftover v1 models. Skip ``type`` because every class
            # has a ``.dict`` attribute via ``__class__``.
            return _to_jsonable(value.dict(), seen)
        if hasattr(value, "_sa_instance_state"):
            # SQLAlchemy model — extract column values, skip internal SA keys.
            return _to_jsonable({k: v for k, v in value.__dict__.items() if not k.startswith("_")}, seen)
        if isinstance(value, (list, tuple)):
            return [_to_jsonable(item, seen) for item in value]
        if isinstance(value, dict):
            return {str(k): _to_jsonable(v, seen) for k, v in value.items()}
        # Pydantic v2 ``RootModel`` / ``Generic`` and other exotic bases —
        # fall back to str repr so we don't silently drop the cached entry
        # (matches the prior behavior of ``json.dumps(..., default=str)``).
        return str(value)
    finally:
        seen.remove(val_id)


def _build_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Build a deterministic cache key, skipping non-serializable args."""
    serializable_args = tuple(_key_value(arg)[1] for arg in args if _key_value(arg)[0])
    serializable_kwargs = {
        key: _key_value(value)[1]
        for key, value in kwargs.items()
        if _key_value(value)[0]
    }
    payload = json.dumps(
        {"args": serializable_args, "kwargs": serializable_kwargs},
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"cache:v2:{func_name}:{digest}"


def invalidate_cached_public(func_name: str, *args: Any, **kwargs: Any) -> None:
    """Delete a cached public entry by rebuilding its deterministic key.

    Must be called with the same serializable args/kwargs the endpoint
    was cached under (e.g. ``site_key`` and ``menu_key`` for
    ``public_menu``), so the sha256 digest matches. Non-serializable
    values (like the ``Session`` dependency) are skipped exactly like
    ``cached_public`` does when writing.
    """
    redis = get_redis()
    key = _build_cache_key(func_name, args, kwargs)
    try:
        redis.delete(key)
    except (ConnectionError, TypeError, ValueError) as exc:
        logger.debug("Cache invalidation skipped: %s", exc)


def invalidate_cached_public_pattern(func_name: str) -> None:
    """Delete every cached entry for a public endpoint function.

    Used for list endpoints whose cache key also includes query params
    (``skip``/``limit``/``category_slug``/``tag_slug``), so the exact key
    cannot be rebuilt from the mutation alone. Deletes all keys prefixed
    ``cache:v2:{func_name}:`` — works with real Redis (``scan_iter``)
    and the test MemoryRedis fallback (``scan_keys``).
    """
    redis = get_redis()
    prefix = f"cache:v2:{func_name}:"
    try:
        if hasattr(redis, "scan_iter"):
            for key in redis.scan_iter(f"{prefix}*"):
                redis.delete(key)
        else:
            for key in redis.scan_keys(f"{prefix}*"):
                redis.delete(key)
    except (ConnectionError, TypeError, ValueError) as exc:
        logger.debug("Cache pattern invalidation skipped: %s", exc)


def cached_public(ttl: int = 300) -> Callable[[F], F]:
    """Cache decorator for public FastAPI endpoints.

    Skips SQLAlchemy Session, Request, and other non-serializable arguments
    when building the cache key so that ``Depends(get_db)`` does not bust
    the cache on every request. Automatically attaches Cache-Control and ETag
    headers to the Response object when provided in kwargs.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            redis = get_redis()
            key = _build_cache_key(func.__name__, args, kwargs)
            response = kwargs.get("response")

            cached_val = redis.get(key)
            if cached_val:
                try:
                    data = json.loads(cached_val)
                except (json.JSONDecodeError, TypeError):
                    data = cached_val
                if response is not None and hasattr(response, "headers"):
                    response.headers["Cache-Control"] = f"public, max-age={ttl}, s-maxage={ttl*2}, stale-while-revalidate=86400"
                    etag = hashlib.md5(str(cached_val).encode("utf-8")).hexdigest()
                    response.headers["ETag"] = f'"{etag}"'
                return data

            result = func(*args, **kwargs)

            try:
                # Convert Pydantic models — and any list/tuple/dict that
                # contains them — into plain JSON-safe types BEFORE
                # ``json.dumps`` so the cache stores a real dict/list
                # structure instead of the ``str(model)`` debug repr.
                serializable = _to_jsonable(result)
                dumped = json.dumps(serializable, default=str)
                redis.setex(key, ttl, dumped)
                if response is not None and hasattr(response, "headers"):
                    response.headers["Cache-Control"] = f"public, max-age={ttl}, s-maxage={ttl*2}, stale-while-revalidate=86400"
                    etag = hashlib.md5(dumped.encode("utf-8")).hexdigest()
                    response.headers["ETag"] = f'"{etag}"'
            except (TypeError, ValueError, ConnectionError) as exc:
                logger.debug("Cache store skipped: %s", exc)

            return result

        return wrapper  # type: ignore[return-value]

    return decorator
