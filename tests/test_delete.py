import re

def test_delete_first_task(chat):
    # Add task
    r1 = chat("dodaj: 14:00 usuń mnie")
    assert r1.status_code == 200

    # Delete by live number
    r2 = chat("usuń 1")
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("intent") in ("delete_task", "remove_task", "delete", "remove")
    reply = (data.get("reply") or data.get("message") or "").lower()
    assert ("usuni" in reply) or ("skas" in reply) or ("deleted" in reply)

    # List should not contain that title anymore
    r3 = chat("lista")
    assert r3.status_code == 200
    out = (r3.json().get("reply") or "").lower()
    assert "usuń mnie" not in out
