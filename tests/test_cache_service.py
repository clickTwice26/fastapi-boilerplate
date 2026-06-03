import json

from app.core.security import stable_cache_key
from app.services.cache import CacheService


async def test_cache_service_returns_cached_json(fake_redis) -> None:
    service = CacheService(namespace="users", ttl_seconds=15)
    key = stable_cache_key("users", "1")
    fake_redis.values[key] = json.dumps({"id": "1"})

    async def loader() -> dict[str, str]:
        raise AssertionError("loader should not be called on cache hit")

    assert await service.get_or_set("1", loader) == {"id": "1"}


async def test_cache_service_loads_and_stores_miss(fake_redis) -> None:
    service = CacheService(namespace="users", ttl_seconds=15)

    async def loader() -> dict[str, str]:
        return {"id": "1"}

    assert await service.get_or_set("1", loader) == {"id": "1"}

    key = stable_cache_key("users", "1")
    assert json.loads(fake_redis.values[key]) == {"id": "1"}
    assert fake_redis.expirations[key] == 15


async def test_cache_service_uses_default_ttl(fake_redis) -> None:
    service = CacheService(namespace="default-ttl")

    async def loader() -> dict[str, str]:
        return {"ok": "true"}

    await service.get_or_set("key", loader)

    key = stable_cache_key("default-ttl", "key")
    assert fake_redis.expirations[key] == service.ttl_seconds


async def test_cache_service_delete(fake_redis) -> None:
    service = CacheService(namespace="users", ttl_seconds=15)
    key = stable_cache_key("users", "1")
    fake_redis.values[key] = json.dumps({"id": "1"})

    await service.delete("1")

    assert key not in fake_redis.values
