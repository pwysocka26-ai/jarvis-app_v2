from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path("data/memory")
HISTORY_FILE = DATA_DIR / "history.json"


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_history() -> List[Dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_history(data: List[Dict[str, Any]]) -> None:
    _ensure_dir()
    HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def log_memory_event(kind: str, payload: Dict[str, Any] | None = None) -> None:
    history = _load_history()
    history.append({
        "kind": kind,
        "payload": payload or {},
        "ts": datetime.now().isoformat(timespec="seconds"),
    })
    history = history[-500:]
    _save_history(history)


def energy_level() -> str:
    h = datetime.now().hour
    if 6 <= h < 11:
        return "high"
    if 11 <= h < 16:
        return "medium"
    return "low"


def energy_advice(tasks_today: List[Dict[str, Any]] | None = None) -> str:
    level = energy_level()
    if level == "high":
        return "⚡ Masz teraz wysoką energię. To dobry moment na trudniejsze rzeczy, planowanie albo domknięcie ważnego zadania."
    if level == "medium":
        return "🔋 Masz teraz średnią energię. Najlepiej wejdą zadania organizacyjne, komunikacja i krótsze bloki pracy."
    return "🌙 Masz teraz niższą energię. Lepiej robić lekkie zadania, inbox, porządkowanie albo przygotowanie jutra."


def memory_summary(tasks_today: List[Dict[str, Any]] | None = None) -> str:
    history = _load_history()
    tasks_today = tasks_today or []
    kinds: Dict[str, int] = {}
    for ev in history:
        kind = str(ev.get("kind") or "inne")
        kinds[kind] = kinds.get(kind, 0) + 1
    lines = ["MEMORY BRAIN", "", f"Zapisane zdarzenia pamięci: **{len(history)}**."]
    if tasks_today:
        lines.append(f"Otwarte zadania na dziś: **{len(tasks_today)}**.")
    if kinds:
        lines.append("")
        lines.append("Najczęstsze ślady pamięci:")
        for kind, count in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0]))[:5]:
            lines.append(f"• {kind}: {count}")
    else:
        lines.append("Na razie pamięć dnia jest jeszcze pusta.")
    lines.append("")
    lines.append("To jest początek warstwy pamięci — Jarvis zaczyna pamiętać, jak używasz dnia i planowania.")
    return "\n".join(lines)
