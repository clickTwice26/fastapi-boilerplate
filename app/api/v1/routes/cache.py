from datetime import datetime, timezone

from fastapi import APIRouter

from app.services.cache import CacheService

router = APIRouter()
cache = CacheService(namespace="demo", ttl_seconds=30)


@router.get("/time")
async def cached_time() -> dict[str, str]:
    async def load_time() -> dict[str, str]:
        return {"generated_at": datetime.now(timezone.utc).isoformat()}

    return await cache.get_or_set("current-time", load_time)


@router.delete("/time")
async def clear_cached_time() -> dict[str, str]:
    await cache.delete("current-time")
    return {"message": "cache cleared"}
