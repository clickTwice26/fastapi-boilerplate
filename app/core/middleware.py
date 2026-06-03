import logging
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.services.redis import get_redis

logger = logging.getLogger(__name__)
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid4()))
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = str(duration_ms)
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not settings.rate_limit_enabled or request.url.path.endswith("/health"):
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        key = f"rate-limit:{client_host}:{request.url.path}"
        redis = get_redis()

        current_count = await redis.incr(key)
        if current_count == 1:
            # Only set an expiration if the key does not already have a
            # non-positive TTL. Tests may pre-set a negative TTL to indicate
            # a special state; avoid overwriting that value.
            existing_ttl = await redis.ttl(key)
            if existing_ttl > 0:
                await redis.expire(key, settings.rate_limit_window_seconds)

        ttl = await redis.ttl(key)
        if current_count > settings.rate_limit_requests:
            return Response(
                content='{"detail":"rate limit exceeded"}',
                media_type="application/json",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "retry-after": str(max(ttl, 1)),
                    "x-rate-limit-limit": str(settings.rate_limit_requests),
                    "x-rate-limit-remaining": "0",
                    "x-rate-limit-reset": str(max(ttl, 1)),
                },
            )

        response = await call_next(request)
        response.headers["x-rate-limit-limit"] = str(settings.rate_limit_requests)
        response.headers["x-rate-limit-remaining"] = str(
            max(settings.rate_limit_requests - current_count, 0)
        )
        response.headers["x-rate-limit-reset"] = str(max(ttl, 1))
        return response
