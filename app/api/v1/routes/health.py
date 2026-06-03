from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.services.redis import get_redis

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    await get_redis().ping()
    return {"status": "ok", "database": "ok", "redis": "ok"}
