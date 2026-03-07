from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach request_id/trace_id to each request.

    Tests expect /v1/health to include non-empty IDs.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        request.state.trace_id = trace_id

        response: Response = await call_next(request)
        response.headers.setdefault("x-request-id", request_id)
        response.headers.setdefault("x-trace-id", trace_id)
        return response
