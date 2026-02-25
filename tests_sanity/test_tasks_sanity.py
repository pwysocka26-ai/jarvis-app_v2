import os
import json
from datetime import datetime

def test_tasks_file_exists():
    # This sanity test checks that tasks file exists (or at least directory does)
    assert os.path.isdir(os.path.join("data", "memory"))

def test_import_router_module():
    # Basic import check (does not start server)
    import app.intent.router  # noqa: F401

def test_tasks_module_has_expected_symbols():
    import app.b2c.tasks as t
    # These are the symbols that should exist based on the current Jarvis flow.
    # If any is missing, we want a clean failure message.
    required = [
        "load_tasks",
        "save_tasks",
        "parse_add_command",
        "add_task",
        "list_tasks_for_date",
        "delete_task_by_id",
        "set_task_transport",
        "set_pending_reminder",
        "pop_pending_reminder",
    ]
    missing = [name for name in required if not hasattr(t, name)]
    assert not missing, f"Missing in app.b2c.tasks: {missing}"
