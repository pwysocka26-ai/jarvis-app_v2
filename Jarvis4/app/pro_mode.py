from __future__ import annotations

from app.config import settings

_override: bool | None = None


def is_pro_enabled() -> bool:
    """Return whether PRO is enabled (env/settings + optional runtime override)."""
    if _override is not None:
        return bool(_override)
    return bool(getattr(settings, "pro_enabled", False))


def set_pro_enabled(value: bool) -> None:
    """Set runtime override for PRO mode (does not persist)."""
    global _override
    _override = bool(value)
