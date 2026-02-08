import os
import jwt
from jwt import PyJWKClient
from dataclasses import dataclass
from typing import Optional, List

class AuthError(RuntimeError):
    pass

@dataclass
class Actor:
    subject: str
    upn: Optional[str]
    roles: List[str]
    tenant_id: Optional[str]

_JWKS_CLIENT: PyJWKClient | None = None
_JWKS_URL_CACHE: str | None = None

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")

def _expected_dev_token() -> str:
    # Prefer API_TOKEN (used by chat_cli.py), then DEV_API_KEY, then fallback.
    return (os.getenv("API_TOKEN") or os.getenv("DEV_API_KEY") or "dev-token").strip()

def _is_dev_mode() -> bool:
    """DEV bypass toggle.

    Enabled when:
      - AUTH_MODE=dev, OR
      - ENTRA_ENABLED=false, OR
      - ENTRA_AUDIENCE is not set (typical offline/local run)

    In dev mode we accept a shared token instead of Entra JWT.
    """
    auth_mode = os.getenv("AUTH_MODE", "").strip().lower()
    entra_enabled = _env_bool("ENTRA_ENABLED", True)
    audience = os.getenv("ENTRA_AUDIENCE", "").strip()
    return (auth_mode == "dev") or (entra_enabled is False) or (audience == "")

def _get_jwks_client() -> PyJWKClient:
    global _JWKS_CLIENT, _JWKS_URL_CACHE
    jwks_url = os.getenv("ENTRA_JWKS_URL", "").strip()
    if not jwks_url:
        tenant = os.getenv("ENTRA_TENANT_ID", "common")
        jwks_url = f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys"
    if _JWKS_CLIENT is None or _JWKS_URL_CACHE != jwks_url:
        _JWKS_CLIENT = PyJWKClient(jwks_url)
        _JWKS_URL_CACHE = jwks_url
    return _JWKS_CLIENT

def validate_bearer_token(auth_header: str) -> Actor:
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise AuthError("Missing bearer token")

    token = auth_header.split(" ", 1)[1].strip()

    # --- DEV BYPASS (offline/local run) ---
    if _is_dev_mode():
        expected = _expected_dev_token()
        if token != expected:
            raise AuthError("Invalid dev token")
        return Actor(subject="dev-user", upn="dev@local", roles=["dev"], tenant_id="dev")
    # --- END DEV BYPASS ---

    audience = os.getenv("ENTRA_AUDIENCE", "").strip()
    if not audience:
        # Should not happen because _is_dev_mode() would be True, but keep defensive.
        raise AuthError("Missing ENTRA_AUDIENCE")

    issuer = os.getenv("ENTRA_ISSUER", "").strip()

    jwks_client = _get_jwks_client()
    signing_key = jwks_client.get_signing_key_from_jwt(token).key

    options = {"verify_aud": True, "verify_exp": True, "verify_signature": True}
    decoded = jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        audience=audience,
        issuer=issuer if issuer else None,
        options=options if issuer else {**options, "verify_iss": False},
    )

    roles = decoded.get("roles") or decoded.get("scp", "").split(" ")
    if isinstance(roles, str):
        roles = [roles]

    return Actor(
        subject=decoded.get("sub") or decoded.get("oid") or "unknown",
        upn=decoded.get("preferred_username") or decoded.get("upn"),
        roles=[r for r in roles if r],
        tenant_id=decoded.get("tid"),
    )
