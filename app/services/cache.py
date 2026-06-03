from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.config import settings
from app.core.security import stable_cache_key
from app.services.redis import get_redis

T = TypeVar("T")


class CacheService:
    def __init__(self, namespace: str, ttl_seconds: int | None = None) -> None:
        self.namespace = namespace
        self.ttl_seconds = ttl_seconds or settings.cache_default_ttl_seconds

    async def get_or_set(self, key: str, loader: Callable[[], Awaitable[T]]) -> T:
        redis = get_redis()
        redis_key = stable_cache_key(self.namespace, key)

        cached_value = await redis.get(redis_key)
        if cached_value is not None:
            return json.loads(cached_value)

        value = await loader()
        await redis.set(redis_key, json.dumps(value, default=str), ex=self.ttl_seconds)
        return value

    async def delete(self, key: str) -> None:
        await get_redis().delete(stable_cache_key(self.namespace, key))
