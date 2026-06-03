from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@dataclass
class UserRecord:
    email: str
    full_name: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.counts: dict[str, int] = {}
        self.expirations: dict[str, int] = {}
        self.closed = False
        self.ping_count = 0

    async def ping(self) -> bool:
        self.ping_count += 1
        return True

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        self.values[key] = value
        self.expirations[key] = ex

    async def delete(self, key: str) -> int:
        return int(self.values.pop(key, None) is not None)

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds

    async def ttl(self, key: str) -> int:
        return self.expirations.get(key, 60)

    async def aclose(self) -> None:
        self.closed = True


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: list[UserRecord] = []

    async def get_by_email(self, email: str) -> UserRecord | None:
        return next((user for user in self.users if user.email == email), None)

    async def create(self, payload) -> UserRecord:
        user = UserRecord(email=payload.email, full_name=payload.full_name)
        self.users.append(user)
        return user

    async def list(self, limit: int, offset: int) -> list[UserRecord]:
        return self.users[offset : offset + limit]

    async def get_by_id(self, user_id: UUID) -> UserRecord | None:
        return next((user for user in self.users if user.id == user_id), None)


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    redis = FakeRedis()
    monkeypatch.setattr("app.services.redis._redis", redis)
    return redis


@pytest.fixture
def app(fake_redis: FakeRedis):
    application = create_app()
    application.state.fake_user_repository = FakeUserRepository()

    from app.api.v1.routes.users import get_user_repository

    def override_user_repository() -> FakeUserRepository:
        return application.state.fake_user_repository

    application.dependency_overrides[get_user_repository] = override_user_repository
    return application


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.fixture(autouse=True)
def reset_route_cache() -> Iterator[None]:
    from app.api.v1.routes.cache import cache

    cache.ttl_seconds = 30
    yield
