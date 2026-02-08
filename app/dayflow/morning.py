from __future__ import annotations

from typing import Any, Dict, List

from .common import _top_tasks_today, _risks, _checklist


def morning_brief() -> Dict[str, Any]:
    tasks = _top_tasks_today(3)

    priorities: List[str] = []
    for t in tasks:
        title = t.get("title", "")
        due = t.get("due_at")
        if due and "T" in due:
            hhmm = due.split("T")[-1]
            priorities.append(f"• {hhmm} – {title}")
        elif due:
            priorities.append(f"• {due} – {title}")
        else:
            priorities.append(f"• {title}")

    risks = _risks(tasks)
    checklist = _checklist(tasks)

    lines: List[str] = []
    lines.append("Dzień dobry 🙂 Sprawdźmy spokojnie, co dziś jest najważniejsze.")
    lines.append("")

    if priorities:
        lines.append("**Najważniejsze dziś:**")
        lines.extend(priorities)
    else:
        lines.append("Na dziś nie widzę jeszcze konkretnych zadań. Dodaj np.: `Dodaj: dentysta dziś 13:00`")

    if risks:
        lines.append("")
        lines.append("⚠️ **Uwaga:**")
        for r in risks:
            lines.append(f"• {r}")

    if checklist:
        lines.append("")
        lines.append("**Checklisty:**")
        for c in checklist:
            lines.append(f"☐ {c}")

    lines.append("")
    lines.append("Zaczynamy od pierwszego kroku: **ustalamy godzinę wyjścia na pierwsze zadanie** — potwierdzasz?")

    return {"response": "\n".join(lines), "intent": "dayflow_morning"}
