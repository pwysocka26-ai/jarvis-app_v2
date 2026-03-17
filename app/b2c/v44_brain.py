
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional


def autonomous_day_manager(tasks_mod, origin: Optional[str], default_mode: Optional[str], day_offset: int = 0) -> str:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    title = "AUTONOMOUS DAY MANAGER"
    if day_offset == 1:
        title += " — JUTRO"
    lines = [f"{title} — {target}", ""]

    # 1) Rebuild day
    try:
        from app.b2c.v42_brain import apply_day_rebuild
        rebuild = apply_day_rebuild(tasks_mod, origin, default_mode, day_offset=day_offset)
        lines.append("KROK 1 — przebudowa dnia")
        lines.append(rebuild)
        lines.append("")
    except Exception:
        lines.append("KROK 1 — przebudowa dnia")
        lines.append("Nie udało się przebudować dnia.")
        lines.append("")

    # 2) Global optimization
    try:
        from app.b2c.v41_brain import apply_global_optimization
        global_opt = apply_global_optimization(tasks_mod, origin, default_mode, day_offset=day_offset, buffer_min=10)
        lines.append("KROK 2 — globalna optymalizacja")
        lines.append(global_opt)
        lines.append("")
    except Exception:
        lines.append("KROK 2 — globalna optymalizacja")
        lines.append("Nie udało się wykonać globalnej optymalizacji.")
        lines.append("")

    # 3) Travel repair
    try:
        from app.b2c.v40_brain import auto_repair_travel_plan
        travel = auto_repair_travel_plan(tasks_mod, origin, default_mode, day_offset=day_offset, buffer_min=10)
        lines.append("KROK 3 — logistyka i dojazdy")
        lines.append(travel)
        lines.append("")
    except Exception:
        lines.append("KROK 3 — logistyka i dojazdy")
        lines.append("Nie udało się sprawdzić logistyki.")
        lines.append("")

    # 4) Smart time blocks
    try:
        from app.b2c.v43_brain import smart_time_blocks
        blocks = smart_time_blocks(tasks_mod, day_offset=day_offset)
        lines.append("KROK 4 — bloki czasu")
        lines.append(blocks)
        lines.append("")
    except Exception:
        lines.append("KROK 4 — bloki czasu")
        lines.append("Nie udało się zbudować bloków czasu.")
        lines.append("")

    # 5) Final plan
    try:
        from app.b2c.v36_brain import true_daily_planner
        final_plan = true_daily_planner(tasks_mod, origin, default_mode, day_offset=day_offset)
        lines.append("KROK 5 — finalny plan")
        lines.append(final_plan)
    except Exception:
        lines.append("KROK 5 — finalny plan")
        lines.append("Nie udało się zbudować finalnego planu dnia.")

    return "\n".join(lines)
