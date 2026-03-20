from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app.b2c import inbox as inbox_mod
from app.intent.router import tasks_mod
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
        category = _classify_title(title)
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
        summary = {
            "status": "ok",
            "next_item": rows[0]["title"],
            "next_time": rows[0]["start"],
        }

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
        })

    for idx, block in enumerate(blocks, start=1):
        timeline.append({
            "id": f"block-{idx}",
            "kind": block["label"],
            "title": "Lunch" if block["label"] == "lunch" else "Focus",
            "start": block["start"],
            "end": block["end"],
            "location": None,
            "category": None,
            "priority": None,
            "task_id": None,
            "deletable": False,
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


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).strip()


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


def _has_schedule(text: str) -> bool:
    low = (text or "").strip().lower()
    schedule_patterns = [
        r"\bdziś\b", r"\bdzis\b", r"\bjutro\b", r"\bpojutrze\b",
        r"\bponiedzia[łl]ek\b", r"\bwtorek\b", r"\bśroda\b", r"\bsroda\b",
        r"\bczwartek\b", r"\bpi[aą]tek\b", r"\bsobota\b", r"\bniedziela\b",
        r"\b\d{1,2}[:.]\d{2}\b",
        r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b",
    ]
    return any(re.search(p, low) for p in schedule_patterns)


def _looks_like_question(text: str) -> bool:
    low = (text or "").strip().lower()
    return ("?" in low) or low.startswith(("co ", "jak ", "kiedy ", "czy ", "ile ", "pokaż ", "pokaz "))


def _extract_shopping_item(text: str) -> str:
    cleaned = _normalize_spaces(text)
    cleaned = re.sub(r"^(kup(ić)?|kupi[ćc]|dokup|weź|wez)\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(muszę|musze)\s+kup(ić)?\s+", "", cleaned, flags=re.I)
    return cleaned.strip(" .,")


def _is_shopping_item(text: str) -> bool:
    low = (text or "").strip().lower()
    if _has_schedule(low):
        return False
    return low.startswith(("kup ", "kupić ", "kupic ", "dokup ", "muszę kupić ", "musze kupic "))


def _is_shopping_event(text: str) -> bool:
    low = (text or "").strip().lower()
    return _has_schedule(low) and any(x in low for x in ["zakupy", "na zakupy", "do sklepu", "jadę do sklepu", "jade do sklepu"])


def _is_scheduled_task(text: str) -> bool:
    low = (text or "").strip().lower()
    if _is_shopping_event(low):
        return False
    return _has_schedule(low) and not _looks_like_question(low)


def _classify_message(text: str) -> str:
    if _looks_like_question(text):
        return "question"
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
    record = {
        "text": _normalize_spaces(text),
        "created_at": inbox_mod._now_iso(),
        "kind": kind,
        "source": "mobile-v9",
    }
    items.append(record)
    _save_raw_inbox(items)
    return record


def _shopping_items() -> List[Dict[str, Any]]:
    items = _load_raw_inbox()
    out: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        kind = str(item.get("kind") or "")
        is_shopping = kind == "shopping" or _is_shopping_item(text) or "kup " in text.lower()
        if is_shopping:
            out.append({"id": idx, "text": text, "kind": "shopping"})
    return out


def list_inbox_items() -> Dict[str, Any]:
    items = _load_raw_inbox()
    unscheduled: List[Dict[str, Any]] = []
    shopping: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        kind = str(item.get("kind") or "task")
        row = {"id": idx, "text": text, "kind": kind}
        if kind == "shopping" or _is_shopping_item(text) or text.lower().startswith("kup "):
            shopping.append(row)
        else:
            unscheduled.append(row)
    return {"status": "ok", "shopping": shopping, "unscheduled": unscheduled}


def create_inbox_item(text: str) -> Dict[str, Any]:
    kind = "shopping" if _is_shopping_item(text) else "task"
    record = _append_inbox_item(_extract_shopping_item(text) if kind == "shopping" else text, kind=kind)
    label = "listy zakupów" if kind == "shopping" else "Inboxa"
    return {
        "status": "ok",
        "intent": "inbox_add",
        "message": f"Dodałem do {label}: {record['text']}",
        "changed": True,
    }


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


def plan_tomorrow() -> Dict[str, Any]:
    payload = build_day_payload(day_offset=1)
    return {
        "status": "ok",
        "intent": "plan_tomorrow",
        "message": f"Jutro masz {len(payload.get('timeline') or [])} pozycji w planie.",
        "changed": False,
    }


def get_memory() -> Dict[str, Any]:
    try:
        from app.b2c.router import _suggest_next_best_action
        return {"status": "ok", "message": str(_suggest_next_best_action() or "")}
    except Exception:
        return {"status": "ok", "message": ""}


def get_priorities_tomorrow() -> Dict[str, Any]:
    payload = build_day_payload(day_offset=1)
    return {
        "status": "ok",
        "date": payload["date"],
        "priorities": payload["priorities"],
    }


def _summarize_today() -> str:
    payload = build_day_payload(day_offset=0)
    timeline = payload.get("timeline") or []
    if not timeline:
        return "Dziś nie masz jeszcze nic konkretnego w planie."
    lines = [f"Dziś masz {len(timeline)} pozycji."]
    for item in timeline[:6]:
        lines.append(f"- {item.get('start')} {item.get('title')}")
    return "\n".join(lines)


def _summarize_tomorrow() -> str:
    payload = build_day_payload(day_offset=1)
    timeline = payload.get("timeline") or []
    if not timeline:
        return "Jutro nie masz jeszcze nic konkretnego w planie."
    lines = [f"Jutro masz {len(timeline)} pozycji."]
    for item in timeline[:6]:
        lines.append(f"- {item.get('start')} {item.get('title')}")
    return "\n".join(lines)


def chat_command(message: str, conversation_tail: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    text = _normalize_spaces(message)
    low = text.lower()
    intent = _classify_message(text)

    if "co mam dziś" in low or "co mam dzis" in low:
        return {
            "status": "ok",
            "intent": "question_today",
            "reply": _summarize_today(),
            "actions": [],
            "changed": False,
        }

    if "plan jutra" in low or "co mam jutro" in low:
        return {
            "status": "ok",
            "intent": "question_tomorrow",
            "reply": _summarize_tomorrow(),
            "actions": [],
            "changed": False,
        }

    if intent == "shopping_event":
        options = _shopping_items()
        normalized = _normalize_auto_task_text(text)
        if options:
            return {
                "status": "ok",
                "intent": "shopping_event_review",
                "reply": "Widzę rzeczy zakupowe w Inboxie. Zaznacz, co dodać do zadania zakupów, a potem możesz jeszcze coś dopisać ręcznie.",
                "actions": [{
                    "type": "shopping_review",
                    "event_text": normalized,
                    "items": options,
                }],
                "changed": False,
            }
        out = tasks_mod.add_task(f"dodaj: {normalized} zakupy")
        return {
            "status": "ok",
            "intent": "shopping_event_empty",
            "reply": str(out.get("reply") or "Dodałem zakupy do planu."),
            "actions": [],
            "changed": True,
        }

    if intent == "scheduled_task":
        normalized = _normalize_auto_task_text(text)
        out = tasks_mod.add_task(f"dodaj: {normalized}")
        return {
            "status": "ok",
            "intent": "scheduled_task",
            "reply": str(out.get("reply") or "Dodałem zadanie do planu."),
            "actions": [],
            "changed": True,
        }

    if intent == "shopping_item":
        item_text = _extract_shopping_item(text)
        _append_inbox_item(item_text, kind="shopping")
        return {
            "status": "ok",
            "intent": "shopping_item",
            "reply": f"Dodałem do listy zakupów w Inboxie: {item_text}",
            "actions": [],
            "changed": True,
        }

    if intent == "unscheduled_item":
        _append_inbox_item(text, kind="task")
        return {
            "status": "ok",
            "intent": "unscheduled_item",
            "reply": f"Dodałem do Inboxa bez terminu: {text}",
            "actions": [],
            "changed": True,
        }

    ai = ollama_chat(text, conversation_tail=conversation_tail)
    return {
        "status": "ok",
        "intent": "question_ai",
        "reply": str(ai.get("reply") or ""),
        "actions": ai.get("actions") or [],
        "changed": False,
    }


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

    extras = [_normalize_spaces(x) for x in (extra_items or []) if _normalize_spaces(x)]
    all_items = selected_texts + extras
    if not all_items:
        return {
            "status": "warning",
            "intent": "shopping_confirm",
            "message": "Nie zaznaczono żadnych pozycji. Nic nie zostało utworzone.",
            "changed": False,
        }

    normalized_event = _normalize_auto_task_text(event_text)
    synthetic = f"dodaj: {normalized_event} zakupy: " + ", ".join(all_items)
    out = tasks_mod.add_task(synthetic)
    _save_raw_inbox(keep)
    return {
        "status": "ok",
        "intent": "shopping_confirm",
        "message": str(out.get("reply") or "Utworzyłem zadanie zakupów."),
        "changed": True,
    }


def delete_plan_task(task_id: int) -> Dict[str, Any]:
    out = tasks_mod.delete_task_by_id(int(task_id))
    return {
        "status": "ok" if out.get("ok") else "warning",
        "intent": "delete_task",
        "message": str(out.get("reply") or "Usunięto zadanie."),
        "changed": bool(out.get("ok")),
    }


def clear_day_tasks(target_date: str) -> Dict[str, Any]:
    tasks = tasks_mod.list_tasks_for_date(target_date) or []
    removed = 0
    for task in tasks:
        due = str(task.get("due_at") or "")
        if due.startswith(target_date):
            out = tasks_mod.delete_task_by_id(int(task.get("id")))
            if out.get("ok"):
                removed += 1
    return {
        "status": "ok",
        "intent": "clear_day",
        "message": f"Usunięto {removed} zadań z dnia {target_date}.",
        "changed": removed > 0,
    }


def ollama_health(model: Optional[str] = None) -> Dict[str, Any]:
    chosen_model = (model or OLLAMA_MODEL).strip() or OLLAMA_MODEL
    client = OllamaClient(OLLAMA_URL, chosen_model, timeout_s=10.0)
    available = client.ping()
    return {
        "status": "ok" if available else "warning",
        "available": available,
        "model": chosen_model,
        "base_url": OLLAMA_URL,
        "source": "ollama",
    }


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

    system_prompt = (
        "Jesteś Jarvisem — organizerem i plannerem dnia. "
        "Odpowiadasz po polsku, krótko i konkretnie. "
        "Zwróć WYŁĄCZNIE JSON: "
        '{"reply": string, "actions": []}.'
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "KONTEKST JARVISA:\n" + json.dumps(context, ensure_ascii=False)},
        {"role": "user", "content": "WIADOMOŚĆ UŻYTKOWNICZKI:\n" + (message or "")},
    ]

    raw = client.chat(messages)
    plan = _normalize_json_candidate(raw) or _fallback_plan(message)
    reply = str(plan.get("reply") or raw or "Jarvis nie zwrócił odpowiedzi.")
    actions = plan.get("actions") if isinstance(plan.get("actions"), list) else []
    return {
        "status": "ok",
        "reply": reply,
        "actions": actions,
        "model": chosen_model,
        "source": "ollama",
    }


def health() -> Dict[str, str]:
    return {"status": "ok", "product": "Jarvis Mobile API", "version": "v9"}
