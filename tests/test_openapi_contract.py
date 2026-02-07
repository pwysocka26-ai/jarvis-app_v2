import yaml
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_openapi_yaml_is_valid_and_matches_routes():
    # Load external contract
    with open("openapi.yaml", "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    assert spec.get("openapi", "").startswith("3.")
    paths = spec.get("paths", {})
    assert "/v1/health" in paths
    assert "/v1/chat" in paths
    assert "/v1/approvals/{approval_id}" in paths
    assert "/v1/approvals/{approval_id}/decision" in paths
    assert "/v1/admin/audit" in paths
    assert "/v1/admin/audit/{event_id}" in paths

    # Compare with runtime schema (FastAPI generated)
    runtime = app.openapi()
    runtime_paths = runtime.get("paths", {})
    for p in paths.keys():
        assert p in runtime_paths, f"Missing runtime route for {p}"

    # Spot-check methods
    assert "get" in runtime_paths["/v1/health"]
    assert "post" in runtime_paths["/v1/chat"]
    assert "get" in runtime_paths["/v1/approvals/{approval_id}"]
    assert "post" in runtime_paths["/v1/approvals/{approval_id}/decision"]
    assert "get" in runtime_paths["/v1/admin/audit"]
    assert "get" in runtime_paths["/v1/admin/audit/{event_id}"]
