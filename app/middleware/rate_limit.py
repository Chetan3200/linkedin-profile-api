import asyncio
from collections import defaultdict, deque
from time import monotonic
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, per_ip: int, global_limit: int, window_seconds: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.per_ip = per_ip
        self.global_limit = global_limit
        self.window_seconds = window_seconds
        self._global: deque[float] = deque()
        self._by_ip: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path != "/v1/profiles/resolve":
            return await call_next(request)
        request_id = getattr(request.state, "request_id", str(uuid4()))
        client_ip = request.client.host if request.client else "unknown"
        async with self._lock:
            now = monotonic()
            cutoff = now - self.window_seconds
            _discard_old(self._global, cutoff)
            ip_requests = self._by_ip[client_ip]
            _discard_old(ip_requests, cutoff)
            if len(self._global) >= self.global_limit or len(ip_requests) >= self.per_ip:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "SERVICE_RATE_LIMITED",
                            "message": (
                                "The service request limit has been reached. Try again later."
                            ),
                            "request_id": request_id,
                            "retryable": True,
                        }
                    },
                    headers={"Cache-Control": "no-store", "X-Request-ID": request_id},
                )
            self._global.append(now)
            ip_requests.append(now)
        return await call_next(request)


def _discard_old(values: deque[float], cutoff: float) -> None:
    while values and values[0] <= cutoff:
        values.popleft()
