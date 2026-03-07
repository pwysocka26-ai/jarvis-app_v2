"""Scheduling utilities.

The production app uses APScheduler to run background jobs.

Important constraints:
* App startup may happen multiple times in tests (multiple TestClient instances).
  Starting the same scheduler twice raises SchedulerAlreadyRunningError.
* Tests must not break production: by default we start the scheduler on startup,
  but allow disabling via env for test runs.
"""

from __future__ import annotations

import os
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler


def scheduler_disabled() -> bool:
    """Return True when background scheduling should not start."""
    val = (os.getenv("JARVIS_DISABLE_SCHEDULER") or "").strip().lower()
    if val in {"1", "true", "yes", "y", "on"}:
        return True
    env = (os.getenv("JARVIS_ENV") or os.getenv("ENV") or os.getenv("ENVIRONMENT") or "").strip().lower()
    return env in {"test", "tests", "pytest"}


def create_scheduler() -> BackgroundScheduler:
    # Keep configuration minimal; add jobs elsewhere.
    return BackgroundScheduler()


def safe_start(scheduler: BackgroundScheduler) -> None:
    """Start scheduler if not running.

    APScheduler raises SchedulerAlreadyRunningError when start() is called twice.
    We treat that as a no-op.
    """

    if scheduler_disabled():
        return
    try:
        # APScheduler exposes `.running` on BaseScheduler.
        if getattr(scheduler, "running", False):
            return
        scheduler.start()
    except Exception as e:
        # Avoid importing APScheduler exception class just for this.
        if e.__class__.__name__ == "SchedulerAlreadyRunningError":
            return
        raise


def safe_shutdown(scheduler: Optional[BackgroundScheduler]) -> None:
    if not scheduler:
        return
    try:
        if getattr(scheduler, "running", False):
            scheduler.shutdown(wait=False)
    except Exception:
        # Shutdown should never crash the app.
        return
