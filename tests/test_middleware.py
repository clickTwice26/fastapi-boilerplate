from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Response

from app.core import middleware as middleware_module
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware, request_id_ctx


class FakeURL:
    def __init__(self, path: str) -> None:
        self.path = path


class FakeRequest:
    def __init__(
        self,
        path: str = "/items",
        method: str = "GET",
        client_host: str | None = "127.0.0.1",
        request_id: str | None = None,
    ) -> None:
        self.url = FakeURL(path)
        self.method = method
        self.client = SimpleNamespace(host=client_host) if client_host is not None else None
        self.headers = {}
        if request_id:
            self.headers["x-request-id"] = request_id


async def ok_response(_: FakeRequest) -> Response:
    return Response(content="ok", media_type="text/plain")


async def test_request_context_middleware_sets_headers_and_resets_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(middleware_module.time, "perf_counter", iter([1.0, 1.12345]).__next__)
    request = FakeRequest(path="/items", method="POST", request_id="request-123")
    middleware = RequestContextMiddleware(FastAPI())

    response = await middleware.dispatch(request, ok_response)

    assert response.headers["x-request-id"] == "request-123"
    assert response.headers["x-response-time-ms"] == "123.45"
    assert request_id_ctx.get() == "-"


async def test_request_context_middleware_resets_context_on_error() -> None:
    async def raises(_: FakeRequest) -> Response:
        raise ValueError("boom")

    middleware = RequestContextMiddleware(FastAPI())

    with pytest.raises(ValueError, match="boom"):
        await middleware.dispatch(FakeRequest(), raises)

    assert request_id_ctx.get() == "-"


async def test_rate_limit_skips_health_endpoint(fake_redis) -> None:
    middleware = RateLimitMiddleware(FastAPI())

    response = await middleware.dispatch(FakeRequest(path="/api/v1/health"), ok_response)

    assert response.status_code == 200
    assert fake_redis.counts == {}


async def test_rate_limit_skips_when_disabled(monkeypatch: pytest.MonkeyPatch, fake_redis) -> None:
    monkeypatch.setattr(middleware_module.settings, "rate_limit_enabled", False)
    middleware = RateLimitMiddleware(FastAPI())

    response = await middleware.dispatch(FakeRequest(), ok_response)

    assert response.status_code == 200
    assert fake_redis.counts == {}


async def test_rate_limit_adds_headers(monkeypatch: pytest.MonkeyPatch, fake_redis) -> None:
    monkeypatch.setattr(middleware_module.settings, "rate_limit_enabled", True)
    monkeypatch.setattr(middleware_module.settings, "rate_limit_requests", 2)
    monkeypatch.setattr(middleware_module.settings, "rate_limit_window_seconds", 30)
    middleware = RateLimitMiddleware(FastAPI())

    response = await middleware.dispatch(FakeRequest(path="/limited"), ok_response)

    assert response.status_code == 200
    assert response.headers["x-rate-limit-limit"] == "2"
    assert response.headers["x-rate-limit-remaining"] == "1"
    assert response.headers["x-rate-limit-reset"] == "30"


async def test_rate_limit_blocks_when_limit_exceeded(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis,
) -> None:
    monkeypatch.setattr(middleware_module.settings, "rate_limit_enabled", True)
    monkeypatch.setattr(middleware_module.settings, "rate_limit_requests", 0)
    fake_redis.expirations["rate-limit:unknown:/limited"] = -1
    middleware = RateLimitMiddleware(FastAPI())

    response = await middleware.dispatch(
        FakeRequest(path="/limited", client_host=None),
        ok_response,
    )

    assert response.status_code == 429
    assert response.body == b'{"detail":"rate limit exceeded"}'
    assert response.headers["retry-after"] == "1"
    assert response.headers["x-rate-limit-remaining"] == "0"
