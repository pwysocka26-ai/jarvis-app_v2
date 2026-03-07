def _chat(chat2, text: str):
    return chat2(text, mode="b2c")

def test_intent_add_task_smoke(chat2):
    r = _chat(chat2, "dodaj: 15:00 zrób test")
    assert r.status_code == 200
    data = r.json()
    assert data.get("intent") in (
        "add_task",
        "add",
        "set_origin_mode",
        "set_travel_mode",
        "set_reminder",
    )

def test_rano_smoke(chat2):
    r = _chat(chat2, "rano")
    assert r.status_code == 200
    data = r.json()
    # In your production flow, "rano" can immediately trigger travel-mode prompt.
    assert data.get("intent") in (
        "morning",
        "rano",
        "morning_flow",
        "plan_day",
        "set_origin_mode",
        "set_travel_mode",
    )

def test_samochodem_smoke(chat2):
    r = _chat(chat2, "samochodem")
    assert r.status_code == 200
    data = r.json()
    assert "reply" in data or "message" in data
