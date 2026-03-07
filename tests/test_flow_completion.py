def test_rano_flow_can_be_completed(chat_flow):
    # "rano" can trigger a small interactive flow (origin / travel mode).
    r = chat_flow("rano")
    assert r.status_code == 200
    data = r.json()
    assert data.get("intent") in ("morning", "rano", "morning_flow", "plan_day", "set_travel_mode", "set_origin_mode")
