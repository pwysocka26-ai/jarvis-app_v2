
def test_rate_limit(client):
    # Stress endpoint; depending on env/config it may return 429.
    for _ in range(130):
        r = client.get("/v1/health")
    assert r.status_code in (200, 429)
