from tests._auth import get_auth_headers, get_chat_post_path

def test_validation_error_is_400_with_standard_shape(client):
    """When payload is invalid, API should return 400/422 with a stable JSON shape (not 500, not 401)."""
    chat_path = get_chat_post_path(client)
    headers = get_auth_headers(client)

    # Missing required / invalid fields (depending on schema)
    r = client.post(chat_path, json={"text": ""}, headers=headers)

    # If auth is enabled, headers should avoid 401
    assert r.status_code != 401

    # Accept FastAPI's default 422 or our standardized 400
    assert r.status_code in (400, 422)

    data = r.json()
    assert isinstance(data, dict)

    # Two acceptable shapes:
    # 1) FastAPI validation: {"detail":[...]}
    # 2) Our standardized error wrapper: {"error_code": "...", "message": "...", "details":[...], "request_id": "..."}
    if "detail" in data:
        assert isinstance(data["detail"], list)
    else:
        assert data.get("error_code") is not None
        assert data.get("message") is not None
        # details may be list or absent depending on implementation
