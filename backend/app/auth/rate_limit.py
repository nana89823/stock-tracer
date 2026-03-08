import logging

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request, status

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy-initialized Redis client
_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


# Rate limit rules: (key_suffix, max_attempts, window_seconds)
_RULES = [
    ("minute", 10, 60),
    ("hour", 30, 3600),
]


async def login_rate_limit(request: Request) -> None:
    """FastAPI dependency that enforces login rate limiting via Redis."""
    client_ip = (
        request.headers.get("X-Real-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )

    try:
        r = _get_redis()

        for suffix, max_attempts, window in _RULES:
            key = f"rate_limit:login:{client_ip}:{suffix}"
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, window)

            if count > max_attempts:
                ttl = await r.ttl(key)
                retry_after = max(ttl, 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many login attempts. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )
    except HTTPException:
        raise
    except Exception:
        logger.warning("Redis unavailable for rate limiting; allowing request through", exc_info=True)
