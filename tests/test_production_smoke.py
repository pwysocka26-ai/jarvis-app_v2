def _chat(client, text: str):
    return client.post("/v1/chat", json={"message": text, "mode": "b2c"})

def test_intent_add_task_smoke(client):
    r = _chat(client, "dodaj: 15:00 zrób test")
    assert r.status_code == 200
    data = r.json()
    assert data.get("intent") in ("add_task", "add")

def test_rano_smoke(client):
    r = _chat(client, "rano")
    assert r.status_code == 200
    data = r.json()
    assert data.get("intent") in ("morning", "rano", "morning_flow", "plan_day")

def test_samochodem_smoke(client):
    r = _chat(client, "samochodem")
    assert r.status_code == 200
    data = r.json()
    assert "reply" in data or "message" in data
