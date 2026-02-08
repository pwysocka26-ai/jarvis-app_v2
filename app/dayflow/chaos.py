from __future__ import annotations

from typing import Any, Dict, List

from .common import _top_tasks_today

CANONICAL = "OK. Plan się rozjechał — przejmuję stery.\nNajpierw ustalmy dwie rzeczy, których nie ruszamy:"


def chaos_brief() -> Dict[str, Any]:
    tasks = _top_tasks_today(5)
    anchors: List[str] = []

    for idx, t in enumerate(tasks[:2], start=1):
        title = t.get("title", "")
        due = t.get("due_at")
        if due and "T" in due:
            anchors.append(f"{idx}️⃣ {title} (o {due.split('T')[-1]})")
        else:
            anchors.append(f"{idx}️⃣ {title}")

    lines: List[str] = [CANONICAL]
    if anchors:
        lines.append("")
        lines.extend(anchors)
        lines.append("")
        lines.append("Resztę układam od nowa. Zaczynamy od pierwszego kroku: **potwierdź te 2 priorytety** — potwierdzasz?")
    else:
        lines.append("")
        lines.append("Nie mam dziś jeszcze zadań z godzinami. Powiedz 1 zdaniem co jest nie do ruszenia (np. „dentysta 13:00”).")

    return {"response": "\n".join(lines), "intent": "dayflow_chaos"}
