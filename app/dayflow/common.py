from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.b2c.tasks import list_tasks, _load  # internal but ok for MVP


def _now() -> datetime:
    return datetime.now()


def _parse_iso(dt_str: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


def _top_tasks_today(limit: int = 3) -> List[Dict[str, Any]]:
    out = list_tasks("today").get("tasks") or []
    if not out:
        out = list_tasks("all").get("tasks") or []
    def key(t: Dict[str, Any]):
        due = t.get("due_at") or "9999-12-31T23:59"
        return (due, int(t.get("id", 0)))
    out = sorted(out, key=key)
    return out[:limit]


def _risks(tasks: List[Dict[str, Any]]) -> List[str]:
    now = _now()
    risks: List[str] = []
    for t in tasks:
        due = t.get("due_at")
        if not due:
            continue
        dt = _parse_iso(due)
        if not dt:
            continue
        delta_min = int((dt - now).total_seconds() // 60)
        if 0 <= delta_min <= 90:
            risks.append(f"Masz mało czasu: **{t.get('title','')}** za ~{delta_min} min (o {dt.strftime('%H:%M')}).")
    return risks[:2]


def _checklist(tasks: List[Dict[str, Any]]) -> List[str]:
    checks: List[str] = []
    joined = " ".join([str(t.get("title","")) for t in tasks]).lower()
    if "dentyst" in joined:
        checks += ["dokumenty / karta", "telefon", "wyjście z zapasem czasu"]
    if "zakup" in joined or "sklep" in joined:
        checks += ["lista zakupów", "portfel / płatność"]
    if "szkoł" in joined or "odebra" in joined:
        checks += ["godzina odbioru", "trasa / dojazd"]

    seen=set()
    out=[]
    for c in checks:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out[:5]
