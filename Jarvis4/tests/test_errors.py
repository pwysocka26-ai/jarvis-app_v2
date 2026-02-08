from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_validation_error_returns_standard_shape():
    # Missing required fields -> 400 with standardized error
    r = client.post("/v1/chat", json={"text": ""})
    assert r.status_code == 400
    data = r.json()
    assert data["error_code"] == "bad_request"
    assert "request_id" in data and data["request_id"]
