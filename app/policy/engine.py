import os
import requests
from dataclasses import dataclass
from typing import Any, Dict, Optional

class PolicyError(RuntimeError):
    pass

@dataclass
class PolicyDecision:
    allow: bool
    reason: str = ""
    details: Optional[Dict[str, Any]] = None

def _opa_url() -> str:
    return os.getenv("OPA_URL", "").strip()

def evaluate(policy_path: str, input_data: Dict[str, Any]) -> PolicyDecision:
    """Evaluate a policy decision.
    
    If OPA_URL is configured, we call OPA REST API:
      POST {OPA_URL}/v1/data/<policy_path>
    
    Expected OPA response shape:
      {"result": {"allow": true, "reason": "...", "details": {...}}}
    
    If OPA_URL is not configured, falls back to local default rules (permit + reason).
    """
    opa = _opa_url()
    if not opa:
        # Local fallback: allow everything (MVP). Enforce critical rules elsewhere too.
        return PolicyDecision(allow=True, reason="local_fallback_allow")

    url = f"{opa.rstrip('/')}/v1/data/{policy_path.lstrip('/')}"
    try:
        r = requests.post(url, json={"input": input_data}, timeout=10)
    except Exception as e:
        raise PolicyError(f"OPA request failed: {e}")

    if r.status_code >= 400:
        raise PolicyError(f"OPA error: {r.status_code} {r.text}")

    payload = r.json()
    result = payload.get("result", {})
    allow = bool(result.get("allow", False))
    return PolicyDecision(
        allow=allow,
        reason=str(result.get("reason", "")),
        details=result.get("details"),
    )
