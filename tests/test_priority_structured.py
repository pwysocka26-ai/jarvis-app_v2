def _structured(resp):
    data = resp.json()
    meta = data.get("meta") or {}
    return meta.get("structured") or {}

def test_priority_is_reflected_in_structured_meta(chat2):
    chat2("dodaj: 15:00 zrób test priorytetu")

    r2 = chat2("priorytet 1 p1")
    assert r2.status_code == 200

    r3 = chat2("lista")
    assert r3.status_code == 200

    tasks = (_structured(r3).get("tasks") or [])
    # find our task
    found = None
    for t in tasks:
        if not isinstance(t, dict):
            continue
        if "priorytetu" in str(t.get("title") or "").lower():
            found = t
            break

    assert found is not None
    assert int(found.get("priority") or 0) == 1
    assert bool(found.get("priority_explicit")) is True
