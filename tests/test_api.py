from uuid import uuid4

import pytest


async def test_health_check(client, monkeypatch: pytest.MonkeyPatch, fake_redis) -> None:
    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def execute(self, statement) -> None:
            assert str(statement) == "SELECT 1"

    monkeypatch.setattr("app.api.v1.routes.health.AsyncSessionLocal", lambda: FakeSession())

    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "redis": "ok"}
    assert fake_redis.ping_count == 1


async def test_cache_endpoint_reuses_cached_value(client, fake_redis) -> None:
    first_response = await client.get("/api/v1/cache/time")
    second_response = await client.get("/api/v1/cache/time")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert len(fake_redis.values) == 1


async def test_cache_endpoint_can_clear_value(client, fake_redis) -> None:
    await client.get("/api/v1/cache/time")

    response = await client.delete("/api/v1/cache/time")

    assert response.status_code == 200
    assert response.json() == {"message": "cache cleared"}
    assert fake_redis.values == {}


async def test_user_crud_endpoints(client, app) -> None:
    create_response = await client.post(
        "/api/v1/users",
        json={"email": "ada@example.com", "full_name": "Ada Lovelace"},
    )

    assert create_response.status_code == 201
    created_user = create_response.json()
    assert created_user["email"] == "ada@example.com"

    list_response = await client.get("/api/v1/users", params={"limit": 10, "offset": 0})
    assert list_response.status_code == 200
    assert list_response.json() == [created_user]

    get_response = await client.get(f"/api/v1/users/{created_user['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == created_user

    assert len(app.state.fake_user_repository.users) == 1


async def test_create_user_rejects_duplicate_email(client) -> None:
    payload = {"email": "grace@example.com", "full_name": "Grace Hopper"}
    assert (await client.post("/api/v1/users", json=payload)).status_code == 201

    response = await client.post("/api/v1/users", json=payload)

    assert response.status_code == 409
    assert response.json() == {"detail": "a user with this email already exists"}


async def test_get_user_returns_404(client) -> None:
    response = await client.get(f"/api/v1/users/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "user not found"}
