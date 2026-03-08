"""
Redis cache utility module for Stock Tracer.

Provides simple async get/set cache functions with JSON serialization.
Gracefully degrades when Redis is unavailable (returns None / silently fails).

Usage:
    from app.cache import get_cache, set_cache

    # In an async endpoint:
    cached = await get_cache("stocks:list")
    if cached is not None:
        return cached

    data = await fetch_from_db()
    await set_cache("stocks:list", data, ttl=300)  # cache for 5 minutes
    return data
"""

import json
import logging
from typing import Any

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    """Lazily initialize and return the Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_client


async def get_cache(key: str) -> Any | None:
    """
    Retrieve a cached value by key.

    Returns the deserialized value, or None if the key does not exist
    or Redis is unavailable.
    """
    try:
        client = _get_client()
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.debug("Redis get failed for key=%s", key, exc_info=True)
        return None


async def set_cache(key: str, value: Any, ttl: int = 300) -> None:
    """
    Store a value in the cache with an expiration time.

    Args:
        key: Cache key string.
        value: Value to cache (must be JSON-serializable).
        ttl: Time-to-live in seconds (default 300 = 5 minutes).
    """
    try:
        client = _get_client()
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        await client.set(key, serialized, ex=ttl)
    except Exception:
        logger.debug("Redis set failed for key=%s", key, exc_info=True)


async def delete_cache(key: str) -> None:
    """
    Delete a cached value by key.

    Silently ignores errors if Redis is unavailable.
    """
    try:
        client = _get_client()
        await client.delete(key)
    except Exception:
        logger.debug("Redis delete failed for key=%s", key, exc_info=True)


async def clear_pattern(pattern: str) -> None:
    """
    Delete all keys matching a pattern (e.g., "stocks:*").

    Useful for cache invalidation after data updates.
    Silently ignores errors if Redis is unavailable.
    """
    try:
        client = _get_client()
        cursor = None
        while cursor != 0:
            cursor, keys = await client.scan(cursor=cursor or 0, match=pattern, count=100)
            if keys:
                await client.delete(*keys)
    except Exception:
        logger.debug("Redis clear_pattern failed for pattern=%s", pattern, exc_info=True)
