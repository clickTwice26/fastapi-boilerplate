from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import settings

_redis: Redis | None = None


async def init_redis() -> Redis:
    global _redis
    _redis = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        health_check_interval=30,
    )
    await _redis.ping()
    return _redis


def get_redis() -> Redis:
    if _redis is None:
        msg = "Redis has not been initialized"
        raise RuntimeError(msg)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
