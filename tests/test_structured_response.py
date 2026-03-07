import pytest


def test_structured_response_shape(chat2):
    """API should return a stable, structured shape: {reply, intent, meta}."""
    r = chat2("rano")
    assert r.status_code == 200
    data = r.json()

    # Required top-level keys
    assert isinstance(data, dict)
    assert set(["reply", "intent", "meta"]).issubset(set(data.keys()))

    assert isinstance(data.get("reply"), str)
    assert isinstance(data.get("intent"), str)
    assert isinstance(data.get("meta"), dict)


def test_structured_response_meta_is_dict_even_on_simple_commands(chat2):
    r = chat2("lista")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("meta"), dict)


def test_structured_response_validation_error_shape(client):
    """When request body is invalid, we should still get JSON with FastAPI validation details."""
    r = client.post("/v1/chat", json={"text": ""})  # missing required fields
    assert r.status_code in (400, 422)
    data = r.json()
    assert isinstance(data, dict)

    # In this project we wrap validation errors into a stable envelope.
    # Depending on the code path, we may expose either:
    # - FastAPI native: {"detail": [...]}
    # - Structured: {"details": [...], "error_code": ..., "message": ...}
    assert ("detail" in data) or ("details" in data)

    details = data.get("detail") or data.get("details")
    assert isinstance(details, list)
