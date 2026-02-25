warning: in the working copy of 'app/b2c/tasks.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/b2c/travel_mode.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/diagnostics/runtime.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/intent/router.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tools/chat_cli.py', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/app/b2c/tasks.py b/app/b2c/tasks.py[m
[1mindex 4a7c496..b97a3f7 100644[m
[1m--- a/app/b2c/tasks.py[m
[1m+++ b/app/b2c/tasks.py[m
[36m@@ -107,9 +107,108 @@[m [mdef load_tasks_db() -> Dict[str, Any]:[m
 def save_tasks_db(db: Dict[str, Any]) -> None:[m
     _save_json(TASKS_FILE, db)[m
 [m
[32m+[m
[32m+[m[32m# --- Backwards-compatible API aliases (older parts of Jarvis import these names) ---[m
[32m+[m
[32m+[m[32mdef load_tasks():[m
[32m+[m[32m    """Compatibility wrapper.[m
[32m+[m
[32m+[m[32m    Historically many parts of Jarvis treated the tasks store as a *list*.[m
[32m+[m[32m    Newer code stores a JSON object: {"tasks": [...]}. This function always[m
[32m+[m[32m    returns the list to avoid subtle bugs (e.g. iterating dict keys).[m
[32m+[m[32m    """[m
[32m+[m[32m    db = load_tasks_db()[m
[32m+[m[32m    tasks = db.get("tasks", [])[m
[32m+[m[32m    return tasks if isinstance(tasks, list) else [][m
[32m+[m
[32m+[m[32mdef save_tasks(db):[m
[32m+[m[32m    """Compatibility wrapper.[m
[32m+[m
[32m+[m[32m    Accepts either a list of tasks or a full db dict.[m
[32m+[m[32m    """[m
[32m+[m[32m    if isinstance(db, dict):[m
[32m+[m[32m        return save_tasks_db(db)[m
[32m+[m[32m    if isinstance(db, list):[m
[32m+[m[32m        return save_tasks_db({"tasks": db})[m
[32m+[m[32m    # Defensive fallback[m
[32m+[m[32m    return save_tasks_db({"tasks": []})[m
[32m+[m
[32m+[m[32mdef pop_pending_reminder():[m
[32m+[m[32m    """Return and clear pending reminder (compat helper)."""[m
[32m+[m[32m    pending = get_pending_reminder()[m
[32m+[m[32m    if pending:[m
[32m+[m[32m        clear_pending_reminder()[m
[32m+[m[32m    return pending[m
[32m+[m
 def _next_id(tasks: List[Dict[str, Any]]) -> int:[m
[31m-    ids = [t.get("id") for t in tasks if isinstance(t.get("id"), int)][m
[31m-    return (max(ids) + 1) if ids else 1[m
[32m+[m[32m    """Smallest free positive integer id.[m
[32m+[m
[32m+[m[32m    Re-uses gaps after deletions so the user sees ids 1..N whenever possible.[m
[32m+[m[32m    """[m
[32m+[m[32m    used = set()[m
[32m+[m[32m    for t in tasks:[m
[32m+[m[32m        try:[m
[32m+[m[32m            used.add(int(t.get("id")))[m
[32m+[m[32m        except Exception:[m
[32m+[m[32m            continue[m
[32m+[m[32m    i = 1[m
[32m+[m[32m    while i in used:[m
[32m+[m[32m        i += 1[m
[32m+[m[32m    return i[m
[32m+[m
[32m+[m
[32m+[m[32m_PR_RE = re.compile(r"^p\s*([1-5])$", re.IGNORECASE)[m
[32m+[m
[32m+[m
[32m+[m[32mdef _parse_priority(token: str):[m
[32m+[m[32m    token = (token or "").strip().lower()[m
[32m+[m[32m    m = _PR_RE.match(token)[m
[32m+[m[32m    if not m:[m
[32m+[m[32m        return None[m
[32m+[m[32m    try:[m
[32m+[m[32m        return int(m.group(1))[m
[32m+[m[32m    except Exception:[m
[32m+[m[32m        return None[m
[32m+[m
[32m+[m
[32m+[m[32mdef _parse_duration_minutes(token: str):[m
[32m+[m[32m    """Parse durations like: 30m, 90m, 1h, 1h30m, 1h 30m, 45min."""[m
[32m+[m[32m    tok = (token or "").strip().lower().replace("minutes", "min").replace("mins", "min")[m
[32m+[m[32m    tok = re.sub(r"\s+", "", tok)[m
[32m+[m[32m    if not tok:[m
[32m+[m[32m        return None[m
[32m+[m[32m    m = re.match(r"^(\d+)(?:m|min)$", tok)[m
[32m+[m[32m    if m:[m
[32m+[m[32m        return int(m.group(1))[m
[32m+[m[32m    m = re.match(r"^(\d+)h(?:(\d+)(?:m|min)?)?$", tok)[m
[32m+[m[32m    if m:[m
[32m+[m[32m        h = int(m.group(1))[m
[32m+[m[32m        mm = int(m.group(2) or 0)[m
[32m+[m[32m        return h * 60 + mm[m
[32m+[m[32m    return None[m
[32m+[m
[32m+[m
[32m+[m[32mdef _strip_meta_tokens_from_title(title: str):[m
[32m+[m[32m    """Allow 'dentysta p1 30m' (no commas) and strip meta tokens from the end."""[m
[32m+[m[32m    if not title:[m
[32m+[m[32m        return "", None, None[m
[32m+[m[32m    words = title.strip().split()[m
[32m+[m[32m    pr = None[m
[32m+[m[32m    dur = None[m
[32m+[m[32m    while words:[m
[32m+[m[32m        w = words[-1][m
[32m+[m[32m        p = _parse_priority(w)[m
[32m+[m[32m        if p is not None and pr is None:[m
[32m+[m[32m            pr = p[m
[32m+[m[32m            words.pop()[m
[32m+[m[32m            continue[m
[32m+[m[32m        d = _parse_duration_minutes(w)[m
[32m+[m[32m        if d is not None and dur is None:[m
[32m+[m[32m            dur = d[m
[32m+[m[32m            words.pop()[m
[32m+[m[32m            continue[m
[32m+[m[32m        break[m
[32m+[m[32m    return " ".join(words).strip(), pr, dur[m
 [m
 def add_task(raw: str) -> Dict[str, Any]:[m
     """Adds a task. Accepts optional travel mode anywhere in text."""[m
[36m@@ -121,18 +220,37 @@[m [mdef add_task(raw: str) -> Dict[str, Any]:[m
     # normalize separators[m
     title = re.sub(r"\s+", " ", title).strip(" ,")[m
 [m
[32m+[m[32m    # Allow meta tokens even without commas: "... p1 30m"[m
[32m+[m[32m    title, pr_from_title, dur_from_title = _strip_meta_tokens_from_title(title)[m
[32m+[m
     # if user wrote "... , samochodem" treat as travel mode and remove from title[m
     if travel:[m
         title = re.sub(rf"(?:,|\s)+{re.escape(travel)}\s*$", "", title, flags=re.IGNORECASE).strip(" ,")[m
 [m
[31m-    # Optional location parsing: if user uses comma-separated format[m
[31m-    # e.g. "dentysta, Niemcewicza 25, Warszawa" -> title="dentysta", location="Niemcewicza 25, Warszawa"[m
[32m+[m[32m    # Optional parsing: title, location..., p1, 30m[m
     location = None[m
[32m+[m[32m    priority = pr_from_title[m
[32m+[m[32m    duration_min = dur_from_title[m
     if "," in title:[m
         parts = [p.strip() for p in title.split(",") if p.strip()][m
[31m-        if len(parts) >= 2:[m
[32m+[m[32m        if parts:[m
             title = parts[0][m
[31m-            location = ", ".join(parts[1:])[m
[32m+[m[32m            loc_parts = [][m
[32m+[m[32m            for tok in parts[1:]:[m
[32m+[m[32m                p = _parse_priority(tok)[m
[32m+[m[32m                if p is not None and priority is None:[m
[32m+[m[32m                    priority = p[m
[32m+[m[32m                    continue[m
[32m+[m[32m                d = _parse_duration_minutes(tok)[m
[32m+[m[32m                if d is not None and duration_min is None:[m
[32m+[m[32m                    duration_min = d[m
[32m+[m[32m                    continue[m
[32m+[m[32m                loc_parts.append(tok)[m
[32m+[m[32m            if loc_parts:[m
[32m+[m[32m                location = ", ".join(loc_parts)[m
[32m+[m
[32m+[m[32m    if priority is None:[m
[32m+[m[32m        priority = 2[m
 [m
     db = load_tasks_db()[m
     tasks = db["tasks"][m
[36m@@ -151,7 +269,9 @@[m [mdef add_task(raw: str) -> Dict[str, Any]:[m
         "due_at": due_at,[m
         "done": False,[m
         "tags": [],[m
[31m-        "priority": None,[m
[32m+[m[32m        # normalized meta[m
[32m+[m[32m        "priority": int(priority) if priority is not None else 2,[m
[32m+[m[32m        "duration_min": int(duration_min) if duration_min is not None else None,[m
         "location": location,[m
         "reminder_at": None,[m
         "reminder_enabled": False,[m
[36m@@ -167,18 +287,29 @@[m [mdef add_task(raw: str) -> Dict[str, Any]: