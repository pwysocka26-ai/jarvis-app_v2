from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Import routers (keep imports inside try blocks to avoid hard failures if modules move)
from app.api import chat as chat_api

try:
    from app.api import approvals as approvals_api
except Exception:
    approvals_api = None

try:
    from app.api import admin_audit as admin_audit_api
except Exception:
    admin_audit_api = None


def create_app() -> FastAPI:
    app = FastAPI(title="Jarvis", version="1.0.0")

    # CORS (safe defaults; do not break existing deployments)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Core routes
    # Keep legacy /chat working; chat router also exposes /v1/chat alias.
    if hasattr(chat_api, "router"):
        app.include_router(chat_api.router)

    # Approvals + Admin audit routes required by openapi.yaml contract
    if approvals_api is not None and hasattr(approvals_api, "router"):
        app.include_router(approvals_api.router)

    if admin_audit_api is not None and hasattr(admin_audit_api, "router"):
        app.include_router(admin_audit_api.router)

    # Health endpoints (legacy + v1 alias)
    @app.get("/health", tags=["diag"])
    def health(request: Request):
        """Lightweight liveness check. Always includes IDs for observability."""
        request_id = getattr(request.state, "request_id", None) or "unknown"
        trace_id = getattr(request.state, "trace_id", None) or "unknown"
        return {"ok": True, "request_id": request_id, "trace_id": trace_id}

    @app.get("/v1/health", tags=["diag"])
    def health_v1(request: Request):
        """v1 alias for health. Contract: ok + request_id + trace_id."""
        request_id = getattr(request.state, "request_id", None) or "unknown"
        trace_id = getattr(request.state, "trace_id", None) or "unknown"
        return {"ok": True, "request_id": request_id, "trace_id": trace_id}

    return app


app = create_app()
