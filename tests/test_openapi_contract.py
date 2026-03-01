import yaml
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_openapi_yaml_loads():
    with open("openapi.yaml", "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    assert spec.get("openapi", "").startswith("3.")
    assert "/v1/chat" in spec.get("paths", {})
    assert "/v1/health" in spec.get("paths", {})

def test_runtime_has_minimum_contract_routes():
    runtime = app.openapi()
    runtime_paths = runtime.get("paths", {})
    assert "/v1/chat" in runtime_paths
    assert "/v1/health" in runtime_paths
