
from __future__ import annotations

import json
from pathlib import Path
from datetime import date, datetime
from typing import Any, Dict, List, Optional

STATE_FILE = Path("data/memory/learning_brain.json")


def _ensure_dir() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {"sessions": [], "stats": {}}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("sessions", [])
            data.setdefault("stats", {})
            return data
    except Exception:
        pass
    return {"sessions": [], "stats": {}}


def _save_state(data: Dict[str, Any]) -> None:
    _ensure_dir()
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _today_tasks(tasks_mod) -> List[Dict[str, Any]]:
    try:
        tasks = tasks_mod.list_tasks_for_date(date.today()) or []
    except Exception:
        tasks = []
    return [t for t in tasks if isinstance(t, dict)]


def _task_title(task: Dict[str, Any]) -> str:
    title = str(task.get("title") or task.get("text") or "").strip()
    if title.lower().startswith("bez godziny "):
        title = title[len("bez godziny "):].strip()
    return title or "(bez tytułu)"


def _priority(task: Dict[str, Any]) -> int:
    try:
        return int(task.get("priority") or 2)
    except Exception:
        return 2


def _duration(task: Dict[str, Any]) -> int:
    try:
        return max(5, int(task.get("duration_min") or 30))
    except Exception:
        return 30


def _due_min(task: Dict[str, Any]) -> Optional[int]:
    due = str(task.get("due_at") or "")
    if "T" not in due:
        return None
    try:
        hhmm = due.split("T", 1)[1][:5]
        hh, mm = hhmm.split(":")
        return int(hh) * 60 + int(mm)
    except Exception:
        return None


def _time_bucket(dt: Optional[datetime] = None) -> str:
    now = (dt or datetime.now()).hour
    if now < 11:
        return "rano"
    if now < 16:
        return "dzień"
    if now < 20:
        return "popołudnie"
    return "wieczór"


def log_focus_result(title: str, planned_min: int, actual_min: int, completed: bool = True, started_at: Optional[str] = None) -> str:
    data = _load_state()
    sessions = data["sessions"]
    stats = data["stats"]
    title_key = title.strip().lower()

    dt = None
    try:
        if started_at:
            dt = datetime.fromisoformat(str(started_at))
    except Exception:
        dt = None

    session = {
        "title": title,
        "planned_min": int(planned_min),
        "actual_min": int(actual_min),
        "completed": bool(completed),
        "time_bucket": _time_bucket(dt),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    sessions.append(session)

    s = stats.get(title_key, {
        "title": title,
        "count": 0,
        "completed_count": 0,
        "total_planned_min": 0,
        "total_actual_min": 0,
        "buckets": {}
    })
    s["count"] += 1
    if completed:
        s["completed_count"] += 1
    s["total_planned_min"] += int(planned_min)
    s["total_actual_min"] += int(actual_min)
    bucket = _time_bucket(dt)
    s["buckets"][bucket] = int(s["buckets"].get(bucket, 0)) + 1
    stats[title_key] = s

    _save_state(data)
    return f"🧠 Zapisałam naukę dla: {title}"


def learning_summary() -> str:
    data = _load_state()
    sessions = data.get("sessions", [])
    stats = data.get("stats", {})
    lines = ["LEARNING BRAIN", "", f"Sesje: {len(sessions)}"]
    if not stats:
        lines.append("Brak danych do nauki.")
        lines.append("Uruchom fokus i kończ zadania, żeby Jarvis zaczął się uczyć.")
        return "\n".join(lines)

    lines.extend(["", "Najczęściej powtarzające się zadania:"])
    top = sorted(stats.values(), key=lambda s: (-int(s.get("count", 0)), str(s.get("title") or "")))[:5]
    for s in top:
        count = int(s.get("count", 0))
        actual = int(s.get("total_actual_min", 0))
        avg = round(actual / count) if count else 0
        comp = int(s.get("completed_count", 0))
        ratio = round((comp / count) * 100) if count else 0
        lines.append(f"• {s.get('title')}: {count}×, średnio {avg} min, ukończone {ratio}%")
    return "\n".join(lines)


def smart_learning_plan(tasks_mod) -> str:
    tasks = [t for t in _today_tasks(tasks_mod) if not bool(t.get("done"))]
    data = _load_state()
    stats = data.get("stats", {})

    if not tasks:
        return "Nie masz dziś aktywnych zadań do inteligentnego planowania."

    def score(task: Dict[str, Any]):
        title = _task_title(task)
        st = stats.get(title.lower(), {})
        count = int(st.get("count", 0))
        completed = int(st.get("completed_count", 0))
        completion_ratio = (completed / count) if count else 0.5
        due = _due_min(task)
        due_rank = 0 if due is not None else 1
        bucket = _time_bucket()
        buckets = st.get("buckets", {}) if isinstance(st, dict) else {}
        bucket_bonus = -int(buckets.get(bucket, 0))
        return (due_rank, _priority(task), bucket_bonus, -completion_ratio, due if due is not None else 10**9, int(task.get("id") or 0))

    ordered = sorted(tasks, key=score)

    lines = [f"LEARNING PLAN — {date.today().isoformat()}", "", "Proponowana kolejność na podstawie historii:"]
    for idx, t in enumerate(ordered[:8], start=1):
        title = _task_title(t)
        st = stats.get(title.lower(), {})
        count = int(st.get("count", 0))
        avg = round(int(st.get("total_actual_min", 0)) / count) if count else _duration(t)
        due = _due_min(t)
        if due is not None:
            hh = due // 60
            mm = due % 60
            lines.append(f"{idx}. {hh:02d}:{mm:02d} — {title} (est. {avg} min)")
        else:
            lines.append(f"{idx}. {title} (est. {avg} min)")
    return "\n".join(lines)
