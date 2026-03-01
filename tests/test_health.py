from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_v1_includes_ids():
    r = client.get("/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "request_id" in data and data["request_id"]
    assert "trace_id" in data and data["trace_id"]
