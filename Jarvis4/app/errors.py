from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

log = logging.getLogger("jarvis.errors")

def _ctx(request: Request):
    return {
        "request_id": getattr(request.state, "request_id", None),
        "trace_id": getattr(request.state, "trace_id", None),
    }

def http_exception_handler(request: Request, exc: StarletteHTTPException):
    ctx = _ctx(request)
    detail = exc.detail if isinstance(exc.detail, dict) else {"error_code": "http_error", "message": str(exc.detail)}
    payload = {
        "error_code": detail.get("error_code", "http_error"),
        "message": detail.get("message", "HTTP error"),
        "details": detail.get("details"),
        **ctx,
    }
    return JSONResponse(status_code=exc.status_code, content=payload)

def validation_exception_handler(request: Request, exc: RequestValidationError):
    ctx = _ctx(request)
    payload = {
        "error_code": "bad_request",
        "message": "Invalid request",
        "details": {"errors": exc.errors()},
        **ctx,
    }
    return JSONResponse(status_code=400, content=payload)

def unhandled_exception_handler(request: Request, exc: Exception):
    ctx = _ctx(request)
    log.exception("unhandled_exception", extra=ctx)
    payload = {
        "error_code": "internal_error",
        "message": "Unexpected error",
        "details": None,
        **ctx,
    }
    return JSONResponse(status_code=500, content=payload)
