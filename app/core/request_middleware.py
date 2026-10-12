import asyncio
import logging
import math
import re
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger("chordweaver.requests")

REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
RATE_LIMITED_PATHS = {
    "/api/v1/style/learn",
    "/api/v1/style/suggest",
    "/api/v1/feedback",
    "/api/v1/billing/checkout",
}


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int, window: int) -> int | None:
        now = time.monotonic()
        async with self._lock:
            requests = self._requests[key]
            while requests and requests[0] <= now - window:
                requests.popleft()
            if len(requests) >= limit:
                return max(1, math.ceil(window - (now - requests[0])))
            requests.append(now)
            return None

    def clear(self) -> None:
        self._requests.clear()


rate_limiter = InMemoryRateLimiter()


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    if forwarded_for:
        return forwarded_for
    return request.client.host if request.client else "unknown"


class RequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        supplied_id = request.headers.get("x-request-id", "")
        request_id = supplied_id if REQUEST_ID_RE.fullmatch(supplied_id) else str(uuid4())
        request.state.request_id = request_id

        if request.method == "POST" and request.url.path in RATE_LIMITED_PATHS and settings.rate_limit_active:
            retry_after = await rate_limiter.check(
                f"{request.url.path}:{_client_key(request)}",
                settings.rate_limit_requests,
                settings.rate_limit_window_seconds,
            )
            if retry_after is not None:
                logger.warning("request_id=%s rate_limited path=%s", request_id, request.url.path)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests"},
                    headers={"X-Request-ID": request_id, "Retry-After": str(retry_after)},
                )

        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_id=%s failed path=%s", request_id, request.url.path)
            raise
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            round((time.monotonic() - started) * 1000),
        )
        return response
