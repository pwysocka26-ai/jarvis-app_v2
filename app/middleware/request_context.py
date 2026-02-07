import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "x-request-id"

class RequestContextMiddleware(BaseHTTPMiddleware):
    """Adds request_id and trace_id to request.state and response headers.
    - request_id: unique per HTTP request
    - trace_id: propagated if client provides x-trace-id; else equals request_id
    """
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        trace_id = request.headers.get("x-trace-id") or request_id

        request.state.request_id = request_id
        request.state.trace_id = trace_id

        response: Response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers["x-trace-id"] = trace_id
        return response
