from datetime import timedelta, datetime

def apply_delay(tasks, delay_minutes):

    for t in tasks:
        if not t.get("time"):
            continue

        dt = datetime.strptime(t["time"], "%H:%M")
        dt += timedelta(minutes=delay_minutes)

        t["time"] = dt.strftime("%H:%M")

    return tasks
