from fastapi.testclient import TestClient

from app.main import app
from tests._auth import get_health_get_path

client = TestClient(app)

def test_health_v1_includes_ids():
    r = client.get(get_health_get_path(client))
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "request_id" in data and data["request_id"]
    assert "trace_id" in data and data["trace_id"]
