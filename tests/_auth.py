import os
from typing import Dict, Optional, Tuple

def _candidate_tokens() -> list[str]:
    return [
        os.getenv("API_TOKEN", ""),
        os.getenv("JARVIS_API_TOKEN", ""),
        os.getenv("JARVIS_TOKEN", ""),
        "dev-token",
    ]

def get_chat_post_path(client) -> str:
    # Prefer route introspection (works even if mounted under /v1 etc.)
    try:
        routes = getattr(client.app, "routes", [])  # FastAPI
        candidates = []
        for r in routes:
            path = getattr(r, "path", None)
            methods = set(getattr(r, "methods", []) or [])
            if not path or "POST" not in methods:
                continue
            if path.endswith("/chat") or path.endswith("/chat/"):
                candidates.append(path.rstrip("/"))
        # Prefer /v1/chat if present
        for p in candidates:
            if p.endswith("/v1/chat") or p == "/v1/chat":
                return p
        if candidates:
            return candidates[0]
    except Exception:
        pass

    # Fallback guesses
    for p in ("/v1/chat", "/chat", "/api/chat"):
        try:
            r = client.post(p, json={"text": "ping"})
            if r.status_code != 404:
                return p
        except Exception:
            continue
    return "/v1/chat"


def get_health_get_path(client) -> str:
    """Return the best-known health endpoint path.

    We keep this tolerant because the app has evolved between versions:
    - some expose /health
    - some expose /v1/health
    """
    try:
        routes = getattr(client.app, "routes", [])
        candidates = []
        for r in routes:
            path = getattr(r, "path", None)
            methods = set(getattr(r, "methods", []) or [])
            if not path or "GET" not in methods:
                continue
            if path.endswith("/health") or path.endswith("/health/"):
                candidates.append(path.rstrip("/"))
        # Prefer /v1/health if present
        for p in candidates:
            if p.endswith("/v1/health") or p == "/v1/health":
                return p
        if candidates:
            return candidates[0]
    except Exception:
        pass

    for p in ("/v1/health", "/health"):
        try:
            r = client.get(p)
            if r.status_code != 404:
                return p
        except Exception:
            continue
    return "/v1/health"

def get_auth_headers(client) -> Dict[str, str]:
    token = ""
    for t in _candidate_tokens():
        if t:
            token = t
            break

    chat_path = get_chat_post_path(client)

    candidates = [
        {"Authorization": f"Bearer {token}"},
        {"Authorization": token},
        {"X-API-Token": token},
        {"X-Api-Token": token},
        {"X-API-Key": token},
        {"x-api-token": token},
    ]
    # Pick the first header that doesn't yield 401 on a harmless request.
    for h in candidates:
        try:
            r = client.post(chat_path, json={"text": "rano"}, headers=h)
            if r.status_code != 401:
                return h
        except Exception:
            continue
    # If auth is disabled, return empty headers
    try:
        r = client.post(chat_path, json={"text": "rano"})
        if r.status_code != 401:
            return {}
    except Exception:
        pass
    return candidates[0]
