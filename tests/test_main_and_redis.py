from fastapi import FastAPI

from app.main import create_app, lifespan
from app.services import redis as redis_service


def test_create_app_configures_routes_and_middleware() -> None:
    app = create_app()
    paths = {route.path for route in app.routes}
    middleware_names = {middleware.cls.__name__ for middleware in app.user_middleware}

    assert "/api/v1/health" in paths
    assert "CORSMiddleware" in middleware_names
    assert "RateLimitMiddleware" in middleware_names
    assert "RequestContextMiddleware" in middleware_names


async def test_lifespan_initializes_and_closes_redis(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_init_redis() -> None:
        calls.append("init")

    async def fake_close_redis() -> None:
        calls.append("close")

    monkeypatch.setattr("app.main.configure_logging", lambda: calls.append("logging"))
    monkeypatch.setattr("app.main.init_redis", fake_init_redis)
    monkeypatch.setattr("app.main.close_redis", fake_close_redis)

    async with lifespan(FastAPI()):
        calls.append("inside")

    assert calls == ["logging", "init", "inside", "close"]


async def test_redis_lifecycle(monkeypatch) -> None:
    class FakeRedisClient:
        def __init__(self) -> None:
            self.closed = False

        async def ping(self) -> bool:
            return True

        async def aclose(self) -> None:
            self.closed = True

    fake_client = FakeRedisClient()

    class FakeRedisFactory:
        @staticmethod
        def from_url(url: str, encoding: str, decode_responses: bool, health_check_interval: int):
            assert url.startswith("redis://")
            assert encoding == "utf-8"
            assert decode_responses is True
            assert health_check_interval == 30
            return fake_client

    monkeypatch.setattr(redis_service, "Redis", FakeRedisFactory)
    monkeypatch.setattr(redis_service, "_redis", None)

    assert await redis_service.init_redis() is fake_client
    assert redis_service.get_redis() is fake_client

    await redis_service.close_redis()

    assert fake_client.closed is True
    assert redis_service._redis is None


async def test_close_redis_is_noop_when_not_initialized(monkeypatch) -> None:
    monkeypatch.setattr(redis_service, "_redis", None)

    await redis_service.close_redis()

    assert redis_service._redis is None


def test_get_redis_raises_when_uninitialized(monkeypatch) -> None:
    monkeypatch.setattr(redis_service, "_redis", None)

    try:
        redis_service.get_redis()
    except RuntimeError as exc:
        assert str(exc) == "Redis has not been initialized"
    else:
        raise AssertionError("expected RuntimeError")
