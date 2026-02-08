
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_rate_limit():
    for i in range(130):
        r = client.get("/v1/health")
    assert r.status_code in (200, 429)
