
from __future__ import annotations

import json
from pathlib import Path
from datetime import date
from typing import Any, Dict, List, Tuple

PERSONAL_MEMORY_FILE = Path("data/memory/personal_memory.json")


def _load_personal_facts() -> List[str]:
    if not PERSONAL_MEMORY_FILE.exists():
        return []
    try:
        data = json.loads(PERSONAL_MEMORY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("facts"), list):
            return [str(x).strip() for x in data["facts"] if str(x).strip()]
    except Exception:
        pass
    return []


def _normalize(text: str) -> str:
    text = (text or "").strip().lower()
    repl = {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
        "ó": "o", "ś": "s", "ż": "z", "ź": "z",
    }
    for a, b in repl.items():
        text = text.replace(a, b)
    return " ".join(text.split())


def _infer_preferences(facts: List[str]) -> List[str]:
    prefs: List[str] = []
    all_norm = [_normalize(f) for f in facts]

    if any("lubie pracowac rano" in f or "najlepiej pracuje rano" in f or "najlepiej pracowac rano" in f for f in all_norm):
        prefs.append("Najważniejsze zadania planuj rano.")
    if any("lubie pracowac wieczorem" in f or "najlepiej pracuje wieczorem" in f for f in all_norm):
        prefs.append("Deep work planuj wieczorem.")
    if any("mieszkam przy " in f or "mieszkam w " in f for f in all_norm):
        prefs.append("Uwzględniaj stały punkt startu przy planowaniu dojazdów.")
    if any("lubie krotkie zadania" in f or "wole krotkie zadania" in f for f in all_norm):
        prefs.append("Wolne okna wypełniaj krótkimi zadaniami.")
    if any("nie lubie rano" in f or "rano mam malo energii" in f for f in all_norm):
        prefs.append("Rano planuj lżejsze zadania, cięższe bloki później.")
    return prefs


def cognitive_brief() -> str:
    facts = _load_personal_facts()
    lines = ["COGNITIVE BRAIN", ""]
    lines.append(f"Zapamiętane fakty osobiste: {len(facts)}")
    prefs = _infer_preferences(facts)
    if prefs:
        lines.extend(["", "Wnioski poznawcze:"])
        lines.extend(f"• {p}" for p in prefs)
    else:
        lines.extend(["", "Nie mam jeszcze wystarczających preferencji do wnioskowania."])
    if facts:
        lines.extend(["", "Podstawa pamięci:"])
        lines.extend(f"• {f}" for f in facts[:8])
    return "\n".join(lines)


def cognitive_day_plan(tasks_mod, origin: str | None, default_mode: str | None, buffer_min: int = 10) -> str:
    facts = _load_personal_facts()
    prefs = _infer_preferences(facts)

    try:
        from app.b2c.context_ai import auto_plan_day
        plan = auto_plan_day(tasks_mod, origin, default_mode, buffer_min=buffer_min)
    except Exception:
        plan = "Nie mogę teraz przygotować planu dnia."

    lines = [f"COGNITIVE PLAN — {date.today().isoformat()}", ""]
    if prefs:
        lines.append("Uwzględnione preferencje:")
        lines.extend(f"• {p}" for p in prefs[:6])
        lines.append("")
    else:
        lines.append("Nie mam jeszcze silnych preferencji użytkownika — plan bazuje głównie na zadaniach i czasie.")
        lines.append("")
    lines.append("Plan dnia:")
    lines.append(plan)
    return "\n".join(lines)


def cognitive_next_step(tasks_mod, origin: str | None, default_mode: str | None, buffer_min: int = 10) -> str:
    facts = _load_personal_facts()
    prefs = _infer_preferences(facts)

    try:
        from app.b2c.context_ai import daily_next_step
        next_step = daily_next_step(tasks_mod, origin, default_mode, buffer_min=buffer_min)
    except Exception:
        next_step = "Nie mogę teraz wskazać kolejnego kroku."

    if prefs:
        return next_step + "\n\nKontekst poznawczy: " + prefs[0]
    return next_step
