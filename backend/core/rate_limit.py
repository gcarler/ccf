from fastapi import HTTPException, Request, status

from backend.core.cache import get_redis


def rate_limiter(limit: int = 5, window_seconds: int = 60):
    async def dependency(request: Request) -> None:
        redis_client = get_redis()
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
