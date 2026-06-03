from fastapi import APIRouter

from app.api.v1.routes import cache, health, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(cache.router, prefix="/cache", tags=["cache"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
