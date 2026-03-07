"""Priority & delete behaviors: end-to-end with list rendering."""


def test_priority_visible_in_list(chat2):
    # Add a timed task so it appears on today's list.
    r1 = chat2("dodaj: 15:00 zrób test priorytetu")
    assert r1.status_code == 200

    # Set priority on first task.
    r2 = chat2("priorytet 1 p1")
    assert r2.status_code == 200

    # List should show some priority marker (emoji or p1).
    r3 = chat2("lista")
    assert r3.status_code == 200
    reply = (r3.json().get("reply") or "")

    # Output format may vary (emoji markers vs. literal "p1").
    # Make it robust by locating our task line and checking for a marker there.
    task_line = None
    for line in reply.splitlines():
        if "zrób test priorytetu" in line.lower() or "zrob test priorytetu" in line.lower():
            task_line = line
            break
    assert task_line is not None, f"Expected task to be present in list output. Reply was:\n{reply}"

    assert (
        "p1" in task_line.lower()
        or "🔴" in task_line
        or "🟡" in task_line
        or "🟢" in task_line
        or "🔥" in task_line
        or "⭐" in task_line
        or "!" in task_line
    ), f"Expected a visible priority marker on task line. Line was: {task_line}"


def test_delete_by_live_number(chat2):
    # Add two tasks and delete first.
    chat2("dodaj: 10:00 test usuwania A")
    chat2("dodaj: 11:00 test usuwania B")

    r_del = chat2("usuń 1")
    assert r_del.status_code == 200
    rep = (r_del.json().get("reply") or "").lower()
    assert "usuni" in rep or "usun" in rep or "ok" in rep

    # Remaining list should still be valid (no crash)
    r_list = chat2("lista")
    assert r_list.status_code == 200
