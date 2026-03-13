from datetime import datetime

def autoplan_day(tasks):
    timed = []
    flexible = []

    for t in tasks:
        if t.get("time"):
            timed.append(t)
        else:
            flexible.append(t)

    timed.sort(key=lambda x: x["time"])

    if not timed and not flexible:
        return "Brak zadań do zaplanowania."

    plan = []
    plan.extend(timed)

    # JEŚLI SĄ FLEXIBLE — zawsze spróbuj je gdzieś wcisnąć
    if flexible:
        for f in flexible:
            plan.append({
                "title": f["title"],
                "time": None,
                "estimated": f.get("estimated", 30)
            })

    return plan
