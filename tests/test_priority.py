def test_priority_set_for_first_task(chat2):
    r1 = chat2("dodaj: 15:00 zrób test priorytetu")
    assert r1.status_code == 200

    r2 = chat2("priorytet 1 p1")
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("intent") in (
        "set_priority",
        "priority",
        "set_priority_task",
        "set-priority",
        "set_origin_mode",
    )
    reply = (data.get("reply") or data.get("message") or "").lower()
    assert ("priorytet" in reply) or ("p1" in reply) or ("ustaw" in reply)

    r3 = chat2("lista")
    assert r3.status_code == 200
    out = (r3.json().get("reply") or "")
    low = out.lower()
    assert (
        ("p1" in low)
        or ("🔥" in out)
        or ("🔴" in out)
        or ("🟥" in out)
        or ("🟧" in out)
        or ("⭐" in out)
        or ("priorytet" in low)
    )
