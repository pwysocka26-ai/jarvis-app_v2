def _structured(data: dict) -> dict:
    meta = data.get("meta") or {}
    return meta.get("structured") or {}

def test_list_returns_structured_meta(chat2):
    # Add two timed tasks
    r1 = chat2("dodaj: 15:00 zrób test A")
    assert r1.status_code == 200
    r2 = chat2("dodaj: 18:30 zrób test B")
    assert r2.status_code == 200

    # List tasks and check structured shape is present
    r3 = chat2("lista")
    assert r3.status_code == 200
    data = r3.json()
    s = _structured(data)

    assert isinstance(s, dict)
    assert s.get("type") in ("task_list", "list", "tasks")
    tasks = s.get("tasks") or []
    assert isinstance(tasks, list)
    # At least our two tasks should be represented
    titles = [str(t.get("title") or "").lower() for t in tasks if isinstance(t, dict)]
    assert any("test a" in t for t in titles)
    assert any("test b" in t for t in titles)
