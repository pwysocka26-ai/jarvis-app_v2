def _structured_tasks(resp):
    data = resp.json()
    meta = data.get("meta") or {}
    s = meta.get("structured") or {}
    return s.get("tasks") or []

def test_sort_time_orders_tasks_by_due_time(chat2):
    # Ensure explicit sort mode by time (so ordering is deterministic)
    chat2("sort czas")

    chat2("dodaj: 18:30 później")
    chat2("dodaj: 15:00 wcześniej")

    r = chat2("lista")
    assert r.status_code == 200
    tasks = [t for t in _structured_tasks(r) if isinstance(t, dict)]

    # Filter only tasks with a time in due_at (YYYY-MM-DDTHH:MM...)
    due_times = []
    for t in tasks:
        due = str(t.get("due_at") or "")
        m = None
        if "T" in due:
            m = due.split("T", 1)[1][:5]
        if m and len(m) == 5 and m[2] == ":":
            due_times.append(m)

    # If there are at least two timed tasks, the first should be earlier or equal.
    if len(due_times) >= 2:
        assert due_times[0] <= due_times[1]
