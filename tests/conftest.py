import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def api_headers():
    # Keep in sync with app.api.security.verify_token
    token = os.getenv("API_TOKEN", "dev-token")
    return {"Authorization": f"Bearer {token}", "user-agent": "testclient"}


@pytest.fixture()
def client(api_headers):
    # Import inside the fixture so environment variables set by run_tests.cmd
    # are applied before app startup.
    from app.main import app

    with TestClient(app, headers=api_headers) as c:
        yield c


def _chat_post(client: TestClient, message: str, mode: str | None = None):
    payload = {"message": message}
    # Default to b2c mode for product tests (stable behavior).
    payload["mode"] = mode or os.getenv("JARVIS_TEST_MODE", "b2c")
    return client.post("/chat", json=payload)


@pytest.fixture()
def chat(client):
    """Simple helper: chat('text') -> Response"""
    def _send(message: str):
        return _chat_post(client, message)
    return _send


@pytest.fixture()
def chat2(client):
    """Alias used by newer flow tests."""
    def _send(message: str):
        return _chat_post(client, message)
    return _send


@pytest.fixture()
def chat_flow(client):
    """Flow helper (currently same as chat)."""
    def _send(message: str):
        return _chat_post(client, message)
    return _send
