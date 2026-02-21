import importlib
from pathlib import Path
import json
import pytest

def _patch_storage(tasks_mod, tmp_path: Path):
    # Redirect storage to temp directory
    tasks_mod.DATA_DIR = tmp_path
    tasks_mod.TASKS_FILE = tmp_path / "tasks.json"
    tasks_mod.PENDING_TRAVEL_FILE = tmp_path / "pending_travel.json"
    tasks_mod.PENDING_REMINDER_FILE = tmp_path / "pending_reminder.json"
    # Deterministic "today"
    tasks_mod._today_iso = lambda: "2026-02-16"
    tasks_mod._ensure_dirs()

@pytest.fixture()
def tasks_mod(tmp_path):
    import app.b2c.tasks as tasks_mod
    _patch_storage(tasks_mod, tmp_path)
    return tasks_mod

@pytest.fixture()
def router(tasks_mod, monkeypatch):
    import app.intent.router as router_mod
    # Make sure router uses the patched tasks module
    monkeypatch.setattr(router_mod, "tasks_mod", tasks_mod, raising=False)

    # Stub morning_brief to avoid dependency on travel_mode implementation in unit tests.
    def fake_morning_brief():
        tasks = tasks_mod.list_tasks_for_date("2026-02-16")
        if not tasks:
            return {"intent": "dayflow_morning", "reply": "Brak zadań na dziś.", "response": "Brak zadań na dziś."}
        # For test we always prompt for transport on the first task
        first = tasks[0]
        tasks_mod.set_pending_travel(int(first["id"]))
        return {
            "intent": "dayflow_morning",
            "reply": "OK\nJak jedziesz?",
            "response": "OK\nJak jedziesz?"
        }

    monkeypatch.setattr(router_mod, "morning_brief", fake_morning_brief, raising=False)
    return router_mod

def test_add_task_parses_datetime_and_lists(tasks_mod):
    out = tasks_mod.add_task("dodaj: test, dziś 21:40, Niemcewicza 25, Warszawa")
    assert isinstance(out, dict)
    assert out["id"] == 1
    # list for today should include it
    tasks = tasks_mod.list_tasks_for_date("2026-02-16")
    assert len(tasks) == 1
    assert tasks[0]["time"] == "21:40"

def test_router_delete_task(router, tasks_mod):
    tasks_mod.add_task("dodaj: test, dziś 21:40, Niemcewicza 25, Warszawa")
    r = router.route_intent("usuń 1")
    assert r["intent"] == "delete_task"
    tasks = tasks_mod.list_tasks_for_date("2026-02-16")
    assert tasks == []

def test_transport_flow_does_not_500(router, tasks_mod):
    tasks_mod.add_task("dodaj: test, dziś 21:40, Niemcewicza 25, Warszawa")
    r1 = router.route_intent("rano")
    assert "Jak jedziesz" in (r1.get("reply") or "")
    # User picks transport
    r2 = router.route_intent("samochodem")
    # We just need a valid reply and cleared pending travel
    assert isinstance(r2.get("reply"), str)
    pending = tasks_mod.get_pending_travel()
    assert pending is None

def test_reminder_yes_sets_once_and_clears(router, tasks_mod):
    # Simulate pending reminder question from morning
    tasks_mod.add_task("dodaj: test, dziś 21:40, Niemcewicza 25, Warszawa")
    tasks_mod.set_pending_reminder(task_id=1, reminder_at_iso="2026-02-16T19:05:00")
    r = router.route_intent("tak")
    assert "przypomnienie" in r.get("reply","").lower() or "ustaw" in r.get("reply","").lower()
    assert tasks_mod.get_pending_reminder() is None
