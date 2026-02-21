from __future__ import annotations

import hashlib
import json
import os
import sys
import inspect
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.diagnostics.instance import get_or_create_instance_id

def _sha256_of_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def _file_info(path: Path) -> Dict[str, Any]:
    try:
        st = path.stat()
        return {
            "exists": True,
            "abs_path": str(path.resolve()),
            "size_bytes": int(st.st_size),
            "mtime_iso": datetime.utcfromtimestamp(st.st_mtime).isoformat() + "Z",
            "sha256": _sha256_of_file(path),
        }
    except Exception:
        return {
            "exists": False,
            "abs_path": str(path.resolve()),
            "size_bytes": None,
            "mtime_iso": None,
            "sha256": None,
        }

def _safe_read_json(path: Path) -> Tuple[Optional[Any], Optional[str]]:
    try:
        if not path.exists():
            return None, "file_missing"
        data = json.loads(path.read_text(encoding="utf-8"))
        return data, None
    except Exception as e:
        return None, f"json_error: {e!r}"

def collect_runtime_diagnostics() -> Dict[str, Any]:
    """Safe diagnostics: avoids importing extra routers (prevents circular import crashes)."""
    import app.orchestrator.core as core_mod

    route_intent = getattr(core_mod, "route_intent", None)
    route_mod = getattr(route_intent, "__module__", None) if route_intent else None
    try:
        route_file = inspect.getsourcefile(route_intent) if route_intent else None
    except Exception:
        route_file = None

    tasks_path = Path("data/memory/tasks.json")
    pending_travel_path = Path("data/memory/pending_travel.json")

    tasks_data, tasks_err = _safe_read_json(tasks_path)
    tasks_count = len(tasks_data) if isinstance(tasks_data, list) else None

    return {
        "instance_id": get_or_create_instance_id(),
        # Diagnostics should reflect the *local* timezone (with offset).
        # Using UTC with a trailing `Z` was confusing (e.g. Warsaw is typically +01:00/+02:00).
        "server_time_iso": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pid": os.getpid(),
        "cwd": os.getcwd(),
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "orchestrator": {
            "module": core_mod.__name__,
            "file": getattr(core_mod, "__file__", None),
        },
        "route_intent": {
            "module": route_mod,
            "file": route_file,
            "name": getattr(route_intent, "__name__", None),
        },
        "data_files": {
            "tasks_json": _file_info(tasks_path),
            "pending_travel_json": _file_info(pending_travel_path),
        },
        "tasks_count": tasks_count,
        "tasks_read_error": tasks_err,
    }
