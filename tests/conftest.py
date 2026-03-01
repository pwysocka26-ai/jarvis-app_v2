from __future__ import annotations

import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app

# ---- Test environment defaults ----
@pytest.fixture(scope="session", autouse=True)
def _test_env():
    # Ensure tests do not start background schedulers
    os.environ.setdefault("JARVIS_DISABLE_SCHEDULER", "1")

    # Jarvis uses JARVIS_API_TOKEN or API_TOKEN with a fallback to "dev-token".
    # For production-like tests, keep auth ON and use a known token.
    os.environ.setdefault("JARVIS_API_TOKEN", "dev-token")
    os.environ.setdefault("API_TOKEN", "dev-token")

    # Use sqlite by default if app.config supports it
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
    yield

# ---- Default authenticated client fixture ----
@pytest.fixture()
def client():
    return TestClient(app, headers={"X-API-Token": "dev-token"})

# ---- Collection guardrails (default suite only) ----
_SKIP_FILES = {
    "test_intents.py",
    "test_jarvis_b2c_flow.py",
    "test_rano_smoke.py",
    "test_rate_limit.py",
    "test_alembic_migrations.py",
}

def pytest_ignore_collect(collection_path: Path, config):  # pytest 8/9 compatible
    try:
        return collection_path.name in _SKIP_FILES
    except Exception:
        return False
