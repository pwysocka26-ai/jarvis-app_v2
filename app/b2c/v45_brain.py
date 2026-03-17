
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple


CATEGORY_PRIORITY = {
    "zdrowie": 1,
    "kariera": 1,
    "praca": 2,
    "administracja": 2,
    "dom": 3,
    "zakupy": 4,
    "inne": 5,
}


def _classify_title(title: str) -> str:
    low = (title or "").strip().lower()
    if any(x in low for x in ["dentyst", "lekarz", "badanie", "wizyta", "zdrow"]):
        return "zdrowie"
    if any(x in low for x in ["rozmowa o prac", "rekrut", "cv", "karier", "oferta pracy"]):
        return "kariera"
    if any(x in low for x in ["spotkanie", "call", "meeting", "projekt", "prezentacja"]):
        return "praca"
    if any(x in low for x in ["urząd", "urzad", "bank", "opłata", "oplata", "rachunek", "podatek"]):
        return "administracja"
    if any(x in low for x in ["sprząt", "sprzat", "dom", "napraw", "pranie"]):
        return "dom"
    if any(x in low for x in ["zakupy", "sklep", "kupi", "apteka"]):
        return "zakupy"
    return "inne"


def contextual_priorities(tasks_mod, day_offset: int = 0) -> str:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows: List[Dict[str, Any]] = []

    try:
        from app.b2c.v34_brain import _load_events
        for e in _load_events():
            if str(e.get("date") or "") != target:
                continue
            title = str(e.get("title") or "wydarzenie")
            category = _classify_title(title)
            rows.append({
                "kind": "event",
                "title": title,
                "time": str(e.get("time") or ""),
                "category": category,
                "priority": CATEGORY_PRIORITY.get(category, 5),
            })
    except Exception:
        pass

    try:
        tasks = tasks_mod.list_tasks_for_date(target) or []
        for t in tasks:
            due = str(t.get("due_at") or "")
            title = str(t.get("title") or t.get("text") or "zadanie")
            category = _classify_title(title)
            time_s = due.split("T", 1)[1][:5] if "T" in due else ""
            rows.append({
                "kind": "task",
                "title": title,
                "time": time_s,
                "category": category,
                "priority": CATEGORY_PRIORITY.get(category, 5),
            })
    except Exception:
        pass

    rows.sort(key=lambda r: (r["priority"], r["time"] or "99:99", r["title"]))

    title = "CONTEXTUAL PRIORITIES"
    if day_offset == 1:
        title += " — JUTRO"
    lines = [f"{title} — {target}", ""]
    if not rows:
        lines.append("Brak punktów na ten dzień.")
        return "\n".join(lines)

    lines.append("Priorytety kontekstowe:")
    for r in rows:
        icon = "📅" if r["kind"] == "event" else "✅"
        when = f"{r['time']} " if r["time"] else ""
        lines.append(f"• {icon} {when}{r['title']} → {r['category']} (p{r['priority']})")

    lines.extend(["", "Najważniejsze teraz:"])
    for r in rows[:3]:
        when = f"{r['time']} " if r["time"] else ""
        lines.append(f"• {when}{r['title']}")

    return "\n".join(lines)
