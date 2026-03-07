import yaml

from app.main import app


def test_openapi_yaml_is_valid_and_matches_routes():
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

    runtime = app.openapi()
    runtime_paths = runtime.get("paths", {})
    for p in paths.keys():
        assert p in runtime_paths, f"Missing runtime route for {p}"

    assert "get" in runtime_paths["/v1/health"]
    assert "post" in runtime_paths["/v1/chat"]
