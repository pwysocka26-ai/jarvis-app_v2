"""Compatibility wrapper.

Some environments referenced `process_due_reminders` from `app.tasks`.
Jarvis handles reminders inside intent router flows; there is no background
queue in this minimal version. We provide a safe no-op to keep imports stable.
"""

from __future__ import annotations

from typing import Any

def process_due_reminders(*args: Any, **kwargs: Any) -> int:
    """No-op placeholder for legacy/background reminder processing.

    Returns:
        int: number of processed reminders (always 0 in this implementation)
    """
    return 0
