def _tasks(resp):
    data = resp.json()
    meta = data.get("meta") or {}
    s = meta.get("structured") or {}
    return s.get("tasks") or []

def test_delete_removes_task_from_structured_list(chat2):
    chat2("dodaj: 15:00 do usunięcia")

    # delete first item using live numbering
    r2 = chat2("usuń 1")
    assert r2.status_code == 200

    r3 = chat2("lista")
    assert r3.status_code == 200
    titles = [str(t.get("title") or "").lower() for t in _tasks(r3) if isinstance(t, dict)]
    assert all("do usunięcia" not in t for t in titles)
