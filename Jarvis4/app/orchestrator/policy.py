from app.config import settings
from app.policy.engine import evaluate, PolicyError

def needs_approval_for(plan_side_effects: bool, actor_roles: list[str] | None = None) -> bool:
    if not plan_side_effects:
        return False
    if not settings.require_approval_for_side_effects:
        return False

    # Optional policy-as-code via OPA:
    try:
        decision = evaluate(
            "jarvis/approvals",
            input_data={"plan": {"side_effects": plan_side_effects}, "actor": {"roles": actor_roles or []}},
        )
        # If policy explicitly allows side-effects without approval, return False.
        if decision.allow and ("Jarvis.Admin" in (actor_roles or [])):
            return False
    except PolicyError:
        # Fail-safe: require approval on policy errors
        return True

    return True
