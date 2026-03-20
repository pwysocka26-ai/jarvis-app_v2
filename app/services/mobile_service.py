from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app.b2c import inbox as inbox_mod
from app.b2c import tasks as tasks_mod
from app.llm.ollama_client import OllamaClient

CATEGORY_PRIORITY = {
    "zdrowie": 1,
    "kariera": 1,
    "praca": 2,
    "administracja": 2,
    "dom": 3,
    "zakupy": 4,
    "inne": 5,
}

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip() or "llama3.1:8b"
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "90"))


def _to_min(hhmm: str) -> int:
    hh, mm = hhmm.split(":")
    return int(hh) * 60 + int(mm)


def _fmt_hhmm(minutes: int) -> str:
    minutes = max(0, int(minutes))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).strip()


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
    if any(x in low for x in ["sprząt", "sprzat", "dom", "napraw", "pranie", "przegląd auta", "przeglad auta"]):
        return "dom"
    if any(x in low for x in ["zakupy", "sklep", "kupi", "apteka"]):
        return "zakupy"
    return "inne"


def _event_rows(target_date: str) -> List[Dict[str, Any]]:
    try:
        from app.b2c.v34_brain import _load_events
        items = _load_events()
    except Exception:
        return []
    rows: List[Dict[str, Any]] = []
    for idx, e in enumerate(items, start=1):
        if str(e.get("date") or "") != target_date:
            continue
        t = str(e.get("time") or "")
        if not t:
            continue
        try:
            start = _to_min(t)
        except Exception:
            continue
        title = str(e.get("title") or "wydarzenie")
        category = _classify_title(title)
        rows.append({
            "id": f"event-{idx}",
            "kind": "event",
            "title": title,
            "start_min": start,
            "end_min": start + 60,
            "start": t,
            "end": _fmt_hhmm(start + 60),
            "location": str(e.get("location") or "").strip() or None,
            "category": category,
            "priority": CATEGORY_PRIORITY.get(category, 5),
            "task_id": None,
            "deletable": False,
            "checklist_count": 0,
        })
    return rows


def _task_rows(target_date: str) -> List[Dict[str, Any]]:
    try:
        tasks = tasks_mod.list_tasks_for_date(target_date) or []
    except Exception:
        return []
    rows: List[Dict[str, Any]] = []
    for t in tasks:
        due = str(t.get("due_at") or "")
        task_id = t.get("id")
        if "T" in due:
            time_s = due.split("T", 1)[1][:5]
        else:
            time_s = "09:00"
        try:
            start = _to_min(time_s)
        except Exception:
            continue
        try:
            duration = max(5, int(t.get("duration_min") or 30))
        except Exception:
            duration = 30
        title = str(t.get("title") or t.get("text") or "zadanie").strip()
        category = str(t.get("category") or _classify_title(title))
        checklist = t.get("checklist") if isinstance(t.get("checklist"), dict) else None
        checklist_items = checklist.get("items") if isinstance(checklist, dict) else []
        rows.append({
            "id": f"task-{task_id}",
            "kind": "task",
            "title": title,
            "start_min": start,
            "end_min": start + duration,
            "start": time_s,
            "end": _fmt_hhmm(start + duration),
            "location": str(t.get("location") or "").strip() or None,
            "category": category,
            "priority": CATEGORY_PRIORITY.get(category, 5),
            "task_id": int(task_id) if isinstance(task_id, int) or str(task_id).isdigit() else None,
            "deletable": True,
            "checklist_count": len(checklist_items) if isinstance(checklist_items, list) else 0,
        })
    return rows


def _free_windows(rows: List[Dict[str, Any]], day_start: int = 8 * 60, day_end: int = 20 * 60) -> List[Dict[str, str]]:
    ordered = sorted(rows, key=lambda r: (r["start_min"], r["end_min"], r["title"]))
    if not ordered:
        return [{"start": _fmt_hhmm(day_start), "end": _fmt_hhmm(day_end)}]
    out: List[Dict[str, str]] = []
    cur = day_start
    for row in ordered:
        if row["start_min"] > cur:
            out.append({"start": _fmt_hhmm(cur), "end": _fmt_hhmm(row["start_min"])})
        cur = max(cur, row["end_min"])
    if cur < day_end:
        out.append({"start": _fmt_hhmm(cur), "end": _fmt_hhmm(day_end)})
    return out


def _time_blocks(free_windows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    blocks: List[Dict[str, str]] = []
    lunch_added = False
    for win in free_windows:
        s = _to_min(win["start"])
        e = _to_min(win["end"])
        if not lunch_added:
            lunch_start = max(s, 12 * 60)
            lunch_end = min(e, 14 * 60)
            if lunch_end - lunch_start >= 30:
                blocks.append({"start": _fmt_hhmm(lunch_start), "end": _fmt_hhmm(lunch_start + 30), "label": "lunch"})
                lunch_added = True
        if e - s >= 45:
            focus_end = min(e, s + 90)
            blocks.append({"start": _fmt_hhmm(s), "end": _fmt_hhmm(focus_end), "label": "focus"})
    return blocks[:6]


def _priorities(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    base = []
    for row in rows:
        if row["kind"] not in {"event", "task"}:
            continue
        base.append({
            "title": row["title"],
            "category": row.get("category") or "inne",
            "priority": int(row.get("priority") or 5),
            "time": row["start"],
            "kind": row["kind"],
        })
    base.sort(key=lambda x: (x["priority"], x.get("time") or "99:99", x["title"]))
    return base


def build_day_payload(day_offset: int = 0) -> Dict[str, Any]:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows = _event_rows(target) + _task_rows(target)
    rows.sort(key=lambda r: (r["start_min"], r["end_min"], r["title"]))
    free_windows = _free_windows(rows)
    blocks = _time_blocks(free_windows)
    priorities = _priorities(rows)
    summary = {"status": "empty", "next_item": None, "next_time": None}
    if rows:
        summary = {"status": "ok", "next_item": rows[0]["title"], "next_time": rows[0]["start"]}
    timeline = []
    for row in rows:
        timeline.append({
            "id": row["id"],
            "kind": row["kind"],
            "title": row["title"],
            "start": row["start"],
            "end": row["end"],
            "location": row.get("location"),
            "category": row.get("category"),
            "priority": row.get("priority"),
            "task_id": row.get("task_id"),
            "deletable": row.get("deletable", False),
            "checklist_count": row.get("checklist_count", 0),
        })
    for idx, block in enumerate(blocks, start=1):
        timeline.append({
            "id": f"block-{idx}",
            "kind": block["label"],
            "title": "Lunch" if block["label"] == "lunch" else "Focus",
            "start": block["start"],
            "end": block["end"],
            "location": None,
            "category": block["label"],
            "priority": None,
            "task_id": None,
            "deletable": False,
            "checklist_count": 0,
        })
    timeline.sort(key=lambda r: (r["start"], r["end"], r["title"]))
    return {
        "date": target,
        "summary": summary,
        "timeline": timeline,
        "free_windows": free_windows,
        "time_blocks": blocks,
        "priorities": priorities,
    }


def _normalize_auto_task_text(text: str) -> str:
    out = _normalize_spaces(text)
    replacements = [
        (r"\bjutro rano\b", "jutro 09:00"),
        (r"\bdziś rano\b", "dziś 09:00"),
        (r"\bdzis rano\b", "dzis 09:00"),
        (r"\bjutro wieczorem\b", "jutro 20:00"),
        (r"\bdziś wieczorem\b", "dziś 20:00"),
        (r"\bdzis wieczorem\b", "dzis 20:00"),
        (r"\bjutro po pracy\b", "jutro 18:00"),
        (r"\bdziś po pracy\b", "dziś 18:00"),
        (r"\bdzis po pracy\b", "dzis 18:00"),
        (r"\bpo pracy\b", "dziś 18:00"),
        (r"\bwieczorem\b", "20:00"),
        (r"\brano\b", "09:00"),
        (r"\bpopo[łl]udniu\b", "15:00"),
    ]
    for pat, repl in replacements:
        out = re.sub(pat, repl, out, flags=re.I)
    return _normalize_spaces(out)


def _normalize_shopping_event_text(text: str) -> str:
    out = _normalize_auto_task_text(text)
    out = re.sub(r"\b(o\s+)?robi[eę]\s+zakupy\b", "zakupy", out, flags=re.I)
    out = re.sub(r"\b(jad[eę]|jade|id[eę]|ide)\s+(na\s+)?zakupy\b", "zakupy", out, flags=re.I)
    out = re.sub(r"\b(jad[eę]|jade|id[eę]|ide)\s+do\s+sklepu\b", "zakupy", out, flags=re.I)
    out = re.sub(r"\bjad[eę]\s+zrobi[ćc]\s+zakupy\b", "zakupy", out, flags=re.I)
    if "zakupy" not in out.lower():
        out = f"{out} zakupy"
    return _normalize_spaces(out)


def _has_schedule(text: str) -> bool:
    low = (text or "").strip().lower()
    patterns = [
        r"\bdziś\b", r"\bdzis\b", r"\bjutro\b", r"\bpojutrze\b",
        r"\bponiedzia[łl]ek\b", r"\bwtorek\b", r"\bśroda\b", r"\bsroda\b",
        r"\bczwartek\b", r"\bpi[aą]tek\b", r"\bsobota\b", r"\bniedziela\b",
        r"\b\d{1,2}[:.]\d{2}\b",
        r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b",
    ]
    return any(re.search(p, low) for p in patterns)


def _looks_like_question(text: str) -> bool:
    low = (text or "").strip().lower()
    return ("?" in low) or low.startswith(("co ", "jak ", "kiedy ", "czy ", "ile ", "pokaż ", "pokaz "))


def _normalize_shopping_noun_phrase(text: str) -> str:
    out = _normalize_spaces(text)
    if not out:
        return out
    replacements = {
        "pastę do zębów": "pasta do zębów",
        "paste do zębów": "pasta do zębów",
        "paste do zebow": "pasta do zębów",
        "pastę do zebow": "pasta do zębów",
        "wodę": "woda",
        "colę": "cola",
        "pietruszkę": "pietruszka",
        "marchewkę": "marchewka",
        "bułkę": "bułka",
        "kajzerkę": "kajzerka",
        "cebulę": "cebula",
        "paprykę": "papryka",
        "sałatę": "sałata",
    }
    low = out.lower()
    if low in replacements:
        return replacements[low]
    if low.endswith(" do zębów"):
        first = out.split(" ", 1)[0]
        if first.lower().endswith("ę"):
            return first[:-1] + "a do zębów"
    parts = out.split(" ", 1)
    first = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    if first.lower().endswith("ę") and len(first) > 2:
        first = first[:-1] + "a"
    return (first + (" " + rest if rest else "")).strip()


def _extract_shopping_item(text: str) -> str:
    cleaned = _normalize_spaces(text)
    cleaned = re.sub(r"^(tak[,! ]*)?", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(dodaj\s+do\s+listy\s+zakup[óo]w\s+)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(dodaj\s+do\s+zadania\s+(z\s+list[ąa]\s+)?zakup[óo]w\s+)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(dodaj\s+do\s+zakup[óo]w\s+)", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(kup(ić)?|kupi[ćc]|dokup|weź|wez)\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(muszę|musze)\s+kup(ić)?\s+", "", cleaned, flags=re.I)
    cleaned = cleaned.strip(" .,")
    return _normalize_shopping_noun_phrase(cleaned)


def _extract_shopping_items_from_reply(text: str) -> List[str]:
    raw = _normalize_spaces(text)
    if not raw:
        return []
    lowered = raw.lower()
    if lowered in {"nie", "nic", "nic więcej", "nic wiecej", "to wszystko", "gotowe", "ok", "okej"}:
        return []
    cleaned = raw
    cleaned = re.sub(r"^(tak[,! ]*)?", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(jeszcze\s+)?dodaj\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^doł[oó]ż\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^dopis[zsz]\s+", "", cleaned, flags=re.I)
    if not cleaned:
        return []
    parts = [p.strip() for p in re.split(r",|;|\s+i\s+", cleaned) if p.strip()]
    out: List[str] = []
    seen = set()
    for part in parts:
        item = _normalize_shopping_noun_phrase(part)
        key = item.lower()
        if item and key not in seen:
            out.append(item)
            seen.add(key)
    return out


def _is_shopping_item(text: str) -> bool:
    low = (text or "").strip().lower()
    if _has_schedule(low):
        return False
    return low.startswith(("kup ", "kupić ", "kupic ", "dokup ", "muszę kupić ", "musze kupic ", "dodaj do listy zakupów ", "dodaj do listy zakupow "))


def _is_add_to_existing_shopping_task(text: str) -> bool:
    low = (text or "").strip().lower()
    return low.startswith((
        "dodaj do zadania zakupów ",
        "dodaj do zadania zakupow ",
        "dodaj do zadania z listą zakupów ",
        "dodaj do zadania z lista zakupow ",
        "dodaj do zakupów ",
        "dodaj do zakupow ",
    ))


def _is_shopping_event(text: str) -> bool:
    low = (text or "").strip().lower()
    return _has_schedule(low) and any(x in low for x in ["zakupy", "na zakupy", "do sklepu", "robię zakupy", "robie zakupy"])


def _is_scheduled_task(text: str) -> bool:
    low = (text or "").strip().lower()
    if _is_shopping_event(low):
        return False
    return _has_schedule(low) and not _looks_like_question(low)


def _classify_message(text: str) -> str:
    if _looks_like_question(text):
        return "question"
    if _is_add_to_existing_shopping_task(text):
        return "shopping_task_add"
    if _is_shopping_event(text):
        return "shopping_event"
    if _is_shopping_item(text):
        return "shopping_item"
    if _is_scheduled_task(text):
        return "scheduled_task"
    return "unscheduled_item"


def _load_raw_inbox() -> List[Dict[str, Any]]:
    data = inbox_mod._read_json(inbox_mod.INBOX_FILE, default=[])
    return data if isinstance(data, list) else []


def _save_raw_inbox(items: List[Dict[str, Any]]) -> None:
    inbox_mod._write_json(inbox_mod.INBOX_FILE, items)


def _append_inbox_item(text: str, kind: str = "task") -> Dict[str, Any]:
    items = _load_raw_inbox()
    normalized = _normalize_spaces(text)
    for item in items:
        if _normalize_spaces(str(item.get("text") or "")).lower() == normalized.lower() and str(item.get("kind") or "task") == kind:
            return item
    record = {
        "text": normalized,
        "created_at": inbox_mod._now_iso(),
        "kind": kind,
        "source": "mobile-v9.2",
    }
    items.append(record)
    _save_raw_inbox(items)
    return record


def _inbox_rows() -> List[Dict[str, Any]]:
    items = _load_raw_inbox()
    rows = []
    for idx, item in enumerate(items, start=1):
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        kind = str(item.get("kind") or "task")
        rows.append({"id": idx, "text": text, "kind": kind})
    return rows


def _dedupe_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    seen = set()
    for row in rows:
        key = (row["kind"], _normalize_spaces(row["text"]).lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def list_inbox_items() -> Dict[str, Any]:
    rows = _dedupe_rows(_inbox_rows())
    unscheduled = []
    shopping = []
    for row in rows:
        if row["kind"] == "shopping":
            shopping.append(row)
        else:
            unscheduled.append(row)
    return {"status": "ok", "shopping": shopping, "unscheduled": unscheduled}


def create_inbox_item(text: str) -> Dict[str, Any]:
    normalized = _normalize_spaces(text)
    if _is_shopping_item(normalized):
        item_text = _extract_shopping_item(normalized)
        record = _append_inbox_item(item_text, kind="shopping")
        return {"status": "ok", "intent": "shopping_item", "message": f"Dodałem do listy zakupów: {record['text']}", "changed": True}
    record = _append_inbox_item(normalized, kind="task")
    return {"status": "ok", "intent": "inbox_add", "message": f"Dodałem do Inboxa: {record['text']}", "changed": True}


def delete_inbox_item(item_id: int) -> Dict[str, Any]:
    items = _load_raw_inbox()
    idx = int(item_id) - 1
    if idx < 0 or idx >= len(items):
        return {"status": "warning", "intent": "delete_inbox_item", "message": "Nie ma takiej pozycji w Inboxie.", "changed": False}
    removed = items.pop(idx)
    _save_raw_inbox(items)
    return {"status": "ok", "intent": "delete_inbox_item", "message": f"Usunięto z Inboxa: {removed.get('text') or 'pozycję'}", "changed": True}


def _compact_day_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    timeline = []
    for item in (payload.get("timeline") or [])[:12]:
        timeline.append({
            "title": item.get("title"),
            "start": item.get("start"),
            "end": item.get("end"),
            "kind": item.get("kind"),
            "category": item.get("category"),
            "location": item.get("location"),
        })
    return {
        "date": payload.get("date"),
        "summary": payload.get("summary"),
        "timeline": timeline,
        "free_windows": payload.get("free_windows") or [],
        "priorities": payload.get("priorities") or [],
    }


def get_memory() -> Dict[str, Any]:
    try:
        from app.b2c.router import _suggest_next_best_action
        return {"status": "ok", "message": str(_suggest_next_best_action() or "")}
    except Exception:
        return {"status": "ok", "message": ""}


def get_priorities_tomorrow() -> Dict[str, Any]:
    payload = build_day_payload(day_offset=1)
    return {"status": "ok", "date": payload["date"], "priorities": payload["priorities"]}


def _summarize_day(day_offset: int, label: str) -> str:
    payload = build_day_payload(day_offset=day_offset)
    timeline = payload.get("timeline") or []
    if not timeline:
        return f"{label} nie masz jeszcze nic konkretnego w planie."
    lines = [f"{label} masz {len(timeline)} pozycji."]
    for item in timeline[:6]:
        lines.append(f"- {item.get('start')} {item.get('title')}")
    return "\n".join(lines)


def plan_tomorrow() -> Dict[str, Any]:
    payload = build_day_payload(day_offset=1)
    return {"status": "ok", "intent": "plan_tomorrow", "message": f"Jutro masz {len(payload.get('timeline') or [])} pozycji w planie.", "changed": False}


def _normalize_json_candidate(text: str) -> Optional[Dict[str, Any]]:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    m = re.search(r"\{.*\}", raw, flags=re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _fallback_plan(message: str) -> Dict[str, Any]:
    return {"reply": "Nie udało się sparsować odpowiedzi AI.", "actions": []}


def ollama_health(model: Optional[str] = None) -> Dict[str, Any]:
    chosen_model = (model or OLLAMA_MODEL).strip() or OLLAMA_MODEL
    client = OllamaClient(OLLAMA_URL, chosen_model, timeout_s=10.0)
    available = client.ping()
    return {"status": "ok" if available else "warning", "available": available, "model": chosen_model, "base_url": OLLAMA_URL, "source": "ollama"}


def ollama_chat(message: str, model: Optional[str] = None, conversation_tail: Optional[List[Dict[str, Any]]] = None, local_brain_notes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    chosen_model = (model or OLLAMA_MODEL).strip() or OLLAMA_MODEL
    client = OllamaClient(OLLAMA_URL, chosen_model, timeout_s=OLLAMA_TIMEOUT)
    context = {
        "today": _compact_day_payload(build_day_payload(day_offset=0)),
        "tomorrow": _compact_day_payload(build_day_payload(day_offset=1)),
        "priorities_tomorrow": get_priorities_tomorrow(),
        "memory": get_memory(),
        "local_brain_notes": (local_brain_notes or [])[:8],
        "conversation_tail": (conversation_tail or [])[-8:],
    }
    system_prompt = "Jesteś Jarvisem — organizerem i plannerem dnia. Odpowiadasz po polsku, krótko i konkretnie. Zwróć WYŁĄCZNIE JSON: {\"reply\": string, \"actions\": []}."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "KONTEKST JARVISA:\n" + json.dumps(context, ensure_ascii=False)},
        {"role": "user", "content": "WIADOMOŚĆ UŻYTKOWNICZKI:\n" + (message or "")},
    ]
    raw = client.chat(messages)
    plan = _normalize_json_candidate(raw) or _fallback_plan(message)
    reply = str(plan.get("reply") or raw or "Jarvis nie zwrócił odpowiedzi.")
    actions = plan.get("actions") if isinstance(plan.get("actions"), list) else []
    return {"status": "ok", "reply": reply, "actions": actions, "model": chosen_model, "source": "ollama"}


def _task_checklist_items(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    checklist = task.get("checklist") if isinstance(task.get("checklist"), dict) else {}
    items = checklist.get("items") if isinstance(checklist, dict) else []
    out: List[Dict[str, Any]] = []
    if not isinstance(items, list):
        return out
    for idx, item in enumerate(items, start=1):
        if isinstance(item, dict):
            out.append({"index": idx, "text": str(item.get("text") or "").strip(), "done": bool(item.get("done"))})
        else:
            out.append({"index": idx, "text": str(item).strip(), "done": False})
    return out


def _is_shopping_task(task: Dict[str, Any]) -> bool:
    title = str(task.get("title") or "").lower()
    category = str(task.get("category") or "").lower()
    return category == "zakupy" or "zakupy" in title


def _upcoming_shopping_tasks() -> List[Dict[str, Any]]:
    db = tasks_mod.load_tasks_db()
    today_iso = date.today().isoformat()
    out = []
    for task in db.get("tasks", []):
        due_at = str(task.get("due_at") or "")
        due_date = due_at.split("T", 1)[0] if due_at else ""
        if due_date and due_date < today_iso:
            continue
        if _is_shopping_task(task):
            out.append(task)
    out.sort(key=lambda t: str(t.get("due_at") or "9999-99-99T99:99"))
    return out


def list_upcoming_shopping_tasks() -> Dict[str, Any]:
    tasks = _upcoming_shopping_tasks()
    return {
        "status": "ok",
        "tasks": [
            {"task_id": int(t.get("id")), "title": str(t.get("title") or "zakupy"), "due_at": str(t.get("due_at") or "")}
            for t in tasks if t.get("id") is not None
        ],
    }


def _find_target_shopping_task(message: str) -> Optional[Dict[str, Any]]:
    tasks = _upcoming_shopping_tasks()
    if not tasks:
        return None
    low = (message or "").lower()
    if "pojutrze" in low:
        wanted = (date.today() + timedelta(days=2)).isoformat()
        for task in tasks:
            if str(task.get("due_at") or "").startswith(wanted):
                return task
    if "jutro" in low:
        wanted = (date.today() + timedelta(days=1)).isoformat()
        for task in tasks:
            if str(task.get("due_at") or "").startswith(wanted):
                return task
    if "dziś" in low or "dzis" in low:
        wanted = date.today().isoformat()
        for task in tasks:
            if str(task.get("due_at") or "").startswith(wanted):
                return task
    if len(tasks) == 1:
        return tasks[0]
    return None


def _merge_unique_items(items: List[str]) -> List[str]:
    out = []
    seen = set()
    for item in items:
        norm = _normalize_shopping_noun_phrase(_normalize_spaces(item))
        key = norm.lower()
        if norm and key not in seen:
            out.append(norm)
            seen.add(key)
    return out


def add_items_to_existing_shopping_task(message: str) -> Dict[str, Any]:
    target = _find_target_shopping_task(message)
    if not target:
        return {
            "status": "warning",
            "intent": "shopping_task_add",
            "message": "Nie widzę jednego aktywnego zadania zakupów. Powiedz np. „dodaj do listy zakupów masło” albo doprecyzuj dzień, np. „dodaj do jutrzejszych zakupów masło”.",
            "actions": [],
            "changed": False,
        }
    items = _extract_shopping_items_from_reply(_extract_shopping_item(message))
    if not items:
        single = _extract_shopping_item(message)
        items = [single] if single else []
    if not items:
        return {"status": "warning", "intent": "shopping_task_add", "message": "Nie widzę produktu do dodania.", "actions": [], "changed": False}
    task_id = int(target.get("id"))
    task = tasks_mod.get_task(task_id)
    if not task:
        return {"status": "warning", "intent": "shopping_task_add", "message": "Nie udało się znaleźć zadania zakupów.", "actions": [], "changed": False}
    existing = [row["text"] for row in _task_checklist_items(task)]
    merged = _merge_unique_items(existing + items)
    checklist = {"title": "Zakupy", "items": [{"text": it, "done": False} for it in merged]}
    tasks_mod.update_task(task_id, title="zakupy", category="zakupy", checklist=checklist)
    return {
        "status": "ok",
        "intent": "shopping_task_add",
        "message": f"Dodałem do zadania „zakupy” ({str(task.get('due_at') or '')[:16]}): {', '.join(items)}",
        "actions": [],
        "changed": True,
    }


def get_plan_task_detail(task_id: int) -> Dict[str, Any]:
    task = tasks_mod.get_task(int(task_id))
    if not task:
        return {"status": "warning", "message": "Nie ma takiego zadania.", "task": None}
    return {
        "status": "ok",
        "message": "ok",
        "task": {
            "task_id": int(task.get("id")),
            "title": str(task.get("title") or "zadanie"),
            "due_at": str(task.get("due_at") or ""),
            "category": str(task.get("category") or _classify_title(str(task.get("title") or ""))),
            "checklist": _task_checklist_items(task),
        },
    }


def add_plan_task_checklist_item(task_id: int, text: str) -> Dict[str, Any]:
    item = _normalize_shopping_noun_phrase(_normalize_spaces(text))
    if not item:
        return {"status": "warning", "intent": "add_checklist_item", "message": "Podaj pozycję do dodania.", "changed": False}
    task = tasks_mod.get_task(int(task_id))
    if not task:
        return {"status": "warning", "intent": "add_checklist_item", "message": "Nie ma takiego zadania.", "changed": False}
    existing = [row["text"] for row in _task_checklist_items(task)]
    merged = _merge_unique_items(existing + [item])
    checklist = {"title": "Zakupy", "items": [{"text": it, "done": False} for it in merged]}
    tasks_mod.update_task(int(task_id), checklist=checklist, title="zakupy", category="zakupy")
    return {"status": "ok", "intent": "add_checklist_item", "message": f"Dodano: {item}", "changed": True}


def remove_plan_task_checklist_item(task_id: int, item_index: int) -> Dict[str, Any]:
    task = tasks_mod.get_task(int(task_id))
    if not task:
        return {"status": "warning", "intent": "remove_checklist_item", "message": "Nie ma takiego zadania.", "changed": False}
    checklist = task.get("checklist") if isinstance(task.get("checklist"), dict) else None
    items = checklist.get("items") if isinstance(checklist, dict) else None
    if not isinstance(items, list) or not (1 <= int(item_index) <= len(items)):
        return {"status": "warning", "intent": "remove_checklist_item", "message": "Nie ma takiej pozycji na liście.", "changed": False}
    removed = items.pop(int(item_index) - 1)
    tasks_mod.update_task(int(task_id), checklist=checklist)
    text = removed.get("text") if isinstance(removed, dict) else str(removed)
    return {"status": "ok", "intent": "remove_checklist_item", "message": f"Usunięto: {text}", "changed": True}


def _shopping_review_options() -> List[Dict[str, Any]]:
    rows = list_inbox_items().get("shopping") or []
    out = []
    seen = set()
    for row in rows:
        key = _normalize_spaces(str(row.get("text") or "")).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def chat_command(message: str, conversation_tail: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    text = _normalize_spaces(message)
    low = text.lower()
    intent = _classify_message(text)
    if "co mam dziś" in low or "co mam dzis" in low:
        return {"status": "ok", "intent": "question_today", "message": _summarize_day(0, "Dziś"), "actions": [], "changed": False}
    if "plan jutra" in low or "co mam jutro" in low:
        return {"status": "ok", "intent": "question_tomorrow", "message": _summarize_day(1, "Jutro"), "actions": [], "changed": False}
    if intent == "shopping_task_add":
        return add_items_to_existing_shopping_task(text)
    if intent == "shopping_event":
        options = _shopping_review_options()
        normalized = _normalize_shopping_event_text(text)
        if options:
            return {
                "status": "ok",
                "intent": "shopping_event_review",
                "message": "Widzę rzeczy zakupowe w Inboxie. Zaznacz, co dodać do zadania zakupów. Potem dopytam w chacie, czy chcesz coś jeszcze dopisać głosem albo tekstem.",
                "actions": [{"type": "shopping_review", "event_text": normalized, "items": options}],
                "changed": False,
            }
        out = tasks_mod.add_task(f"dodaj: {normalized}")
        return {"status": "ok", "intent": "shopping_event_empty", "message": str(out.get("reply") or "Dodałem zakupy do planu."), "actions": [], "changed": True}
    if intent == "scheduled_task":
        normalized = _normalize_auto_task_text(text)
        out = tasks_mod.add_task(f"dodaj: {normalized}")
        return {"status": "ok", "intent": "scheduled_task", "message": str(out.get("reply") or "Dodałem zadanie do planu."), "actions": [], "changed": True}
    if intent == "shopping_item":
        item_text = _extract_shopping_item(text)
        _append_inbox_item(item_text, kind="shopping")
        return {"status": "ok", "intent": "shopping_item", "message": f"Dodałem do listy zakupów: {item_text}", "actions": [], "changed": True}
    if intent == "unscheduled_item":
        _append_inbox_item(text, kind="task")
        return {"status": "ok", "intent": "unscheduled_item", "message": f"Dodałem do Inboxa bez terminu: {text}", "actions": [], "changed": True}
    ai = ollama_chat(text, conversation_tail=conversation_tail)
    return {"status": "ok", "intent": "question_ai", "message": str(ai.get("reply") or ""), "actions": ai.get("actions") or [], "changed": False}


def confirm_shopping_event(event_text: str, selected_item_ids: List[int], extra_items: List[str]) -> Dict[str, Any]:
    items = _load_raw_inbox()
    selected_texts: List[str] = []
    keep: List[Dict[str, Any]] = []
    selected = {int(x) for x in selected_item_ids}
    for idx, item in enumerate(items, start=1):
        text = str(item.get("text") or "").strip()
        if idx in selected:
            if text:
                selected_texts.append(text)
        else:
            keep.append(item)
    extras = _merge_unique_items(extra_items or [])
    all_items = _merge_unique_items(selected_texts + extras)
    normalized_event = _normalize_shopping_event_text(event_text)
    if not all_items:
        out = tasks_mod.add_task(f"dodaj: {normalized_event}")
        return {"status": "ok", "intent": "shopping_confirm", "message": str(out.get("reply") or "Dodałem zakupy do planu."), "changed": True}
    out = tasks_mod.add_task(f"dodaj: {normalized_event}")
    task = out.get("task") if isinstance(out, dict) else None
    task_id = int(task.get("id")) if isinstance(task, dict) and task.get("id") is not None else None
    due_at = str(task.get("due_at") or "") if isinstance(task, dict) else ""
    merged_with_old = list(all_items)
    if task_id is not None:
        db = tasks_mod.load_tasks_db()
        old_ids_to_remove: List[int] = []
        for row in db.get("tasks", []):
            if int(row.get("id") or -1) == task_id:
                continue
            if not _is_shopping_task(row):
                continue
            if due_at and str(row.get("due_at") or "") == due_at:
                merged_with_old.extend([it["text"] for it in _task_checklist_items(row)])
                old_ids_to_remove.append(int(row.get("id")))
        merged_with_old = _merge_unique_items(merged_with_old)
        checklist = {"title": "Zakupy", "items": [{"text": item, "done": False} for item in merged_with_old]}
        tasks_mod.update_task(task_id, title="zakupy", category="zakupy", checklist=checklist)
        for old_id in old_ids_to_remove:
            tasks_mod.delete_task_by_id(old_id)
    _save_raw_inbox(keep)
    reply = "✅ Utworzyłem zadanie „zakupy”."
    if due_at:
        reply += f" (na {due_at})"
    reply += "\nLista: " + ", ".join(merged_with_old)
    return {"status": "ok", "intent": "shopping_confirm", "message": reply, "changed": True}


def delete_plan_task(task_id: int) -> Dict[str, Any]:
    out = tasks_mod.delete_task_by_id(int(task_id))
    return {"status": "ok" if out.get("ok") else "warning", "intent": "delete_task", "message": str(out.get("reply") or "Usunięto zadanie."), "changed": bool(out.get("ok"))}


def clear_day_tasks(target_date: str) -> Dict[str, Any]:
    tasks = tasks_mod.list_tasks_for_date(target_date) or []
    removed = 0
    for task in tasks:
        due = str(task.get("due_at") or "")
        if due.startswith(target_date):
            out = tasks_mod.delete_task_by_id(int(task.get("id")))
            if out.get("ok"):
                removed += 1
    return {"status": "ok", "intent": "clear_day", "message": f"Usunięto {removed} zadań z dnia {target_date}.", "changed": removed > 0}


def health() -> Dict[str, str]:
    return {"status": "ok", "product": "Jarvis Mobile API", "version": "v9.2"}
