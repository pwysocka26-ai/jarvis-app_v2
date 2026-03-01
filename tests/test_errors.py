def test_validation_error_is_400_with_standard_shape(client):
    # Missing required fields according to schemas -> 400 with standardized error
    r = client.post("/v1/chat", json={"text": ""})
    assert r.status_code == 400
    data = r.json()
    assert data["error_code"] == "bad_request"
    assert "request_id" in data and data["request_id"]
