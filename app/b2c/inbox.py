from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import re

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "memory"
INBOX_FILE = DATA_DIR / "inbox.json"
IDEAS_FILE = DATA_DIR / "ideas.json"
NOTES_FILE = DATA_DIR / "notes.json"
REMINDERS_FILE = DATA_DIR / "reminders.json"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _append_record(path: Path, record: Dict[str, Any]) -> None:
    data = _read_json(path, default=[])
    if not isinstance(data, list):
        data = []
    data.append(record)
    _write_json(path, data)






def _bucket_label(kind: str, locative: bool = False, plural: bool = False) -> str:
    k = (kind or '').strip().lower()
    if k == 'idea':
        if locative:
            return 'pomysłach'
        if plural:
            return 'pomysły'
        return 'pomysł'
    if k == 'note':
        if locative:
            return 'notatkach'
        if plural:
            return 'notatki'
        return 'notatkę'
    if k == 'reminder':
        if locative or plural:
            return 'reminders'
        return 'reminder'
    if locative:
        return 'wpisach'
    if plural:
        return 'wpisy'
    return 'wpis'


def _bucket_path(kind: str) -> Path:
    k = (kind or '').strip().lower()
    if k == 'idea':
        return IDEAS_FILE
    if k == 'note':
        return NOTES_FILE
    if k == 'reminder':
        return REMINDERS_FILE
    raise ValueError(f'Unsupported bucket kind: {kind}')


def _load_bucket(kind: str) -> List[Dict[str, Any]]:
    data = _read_json(_bucket_path(kind), default=[])
    if not isinstance(data, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = str(item.get('text') or '').strip()
        if not text:
            continue
        fixed = dict(item)
        fixed['text'] = text
        fixed['kind'] = kind
        out.append(fixed)
    return out


def _save_bucket(kind: str, data: List[Dict[str, Any]]) -> None:
    _write_json(_bucket_path(kind), data)


def _bucket_duplicate_index(kind: str, text: str, *, ignore_index: Optional[int] = None) -> Optional[int]:
    canon = _canonical_key(text)
    for idx, item in enumerate(_load_bucket(kind), start=1):
        if ignore_index is not None and idx == ignore_index:
            continue
        existing = str(item.get('text') or '').strip()
        if existing and _canonical_key(existing) == canon:
            return idx
    return None

def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).strip()


def _normalize_auto_task_text(text: str) -> str:
    out = _normalize_spaces(text)
    replacements = [
        (r"\bjutro rano\b", "jutro 09:00"),
        (r"\bdziś rano\b", "dziś 09:00"),
        (r"\bdzis rano\b", "dzis 09:00"),
        (r"\bjutro wieczorem\b", "jutro 19:00"),
        (r"\bdziś wieczorem\b", "dziś 19:00"),
        (r"\bdzis wieczorem\b", "dzis 19:00"),
        (r"\bjutro po pracy\b", "jutro 18:00"),
        (r"\bdziś po pracy\b", "dziś 18:00"),
        (r"\bdzis po pracy\b", "dzis 18:00"),
        (r"\bpo pracy\b", "dziś 18:00"),
        (r"\bwieczorem\b", "19:00"),
        (r"\brano\b", "09:00"),
        (r"\bpo[ -]?po[łl]udniu\b", "15:00"),
        (r"\bpopo[łl]udniu\b", "15:00"),
        (r"\bw sobotę rano\b", "sobota 09:00"),
        (r"\bw sobote rano\b", "sobota 09:00"),
        (r"\bw sobotę\b", "sobota 10:00"),
        (r"\bw sobote\b", "sobota 10:00"),
        (r"\bw niedzielę rano\b", "niedziela 09:00"),
        (r"\bw niedziele rano\b", "niedziela 09:00"),
        (r"\bw niedzielę\b", "niedziela 10:00"),
        (r"\bw niedziele\b", "niedziela 10:00"),
    ]
    for pat, repl in replacements:
        out = re.sub(pat, repl, out, flags=re.I)
    return _normalize_spaces(out)


def _canonical_key(text: str) -> str:
    text = _normalize_auto_task_text(text).lower()
    text = re.sub(r"[^\w\s:.-]", "", text, flags=re.UNICODE)
    return _normalize_spaces(text)


def _find_duplicate_inbox(items: List[Dict[str, Any]], text: str) -> Optional[Dict[str, Any]]:
    key = _canonical_key(text)
    for item in items:
        existing = str(item.get("text") or "").strip()
        if existing and _canonical_key(existing) == key:
            return item
    return None

def _has_schedule(text: str) -> bool:
    low = (text or "").strip().lower()
    schedule_patterns = [
        r"\bdziś\b", r"\bdzis\b", r"\bjutro\b", r"\bpojutrze\b",
        r"\bza tydzie[nń]\b",
        r"\bponiedzia[łl]ek\b", r"\bwtorek\b", r"\bśroda\b", r"\bsroda\b",
        r"\bczwartek\b", r"\bpi[aą]tek\b", r"\bsobota\b", r"\bniedziela\b",
        r"\b\d{1,2}[:.]\d{2}\b",
        r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b",
        r"\b\d{1,2}\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|wrze[sś]nia|pa[zź]dziernika|listopada|grudnia)\b",
    ]
    return any(re.search(p, low) for p in schedule_patterns)


def _looks_like_task(text: str) -> bool:
    low = (text or "").strip().lower()
    task_patterns = [
        r"^kup\b",
        r"^zrobi[ćc]\b",
        r"^sprawdzi[ćc]\b",
        r"^zadzwoni[ćc]\b",
        r"^napisa[ćc]\b",
        r"^wys[łl]a[ćc]\b",
        r"^odebra[ćc]\b",
        r"^um[oó]wi[ćc]\b",
        r"^zam[oó]wi[ćc]\b",
        r"^ogarn[aą][ćc]\b",
        r"^przygotowa[ćc]\b",
        r"^doda[ćc]\b",
        r"^musz[eę]\b",
        r"^trzeba\b",
    ]
    return any(re.search(p, low) for p in task_patterns)


def _classify_inbox_text(text: str) -> str:
    low = (text or "").strip().lower()

    note_patterns = [
        r"^notatka\b",
        r"^notatki\b",
        r"^notatka ze\b",
        r"^notatka z\b",
        r"^zapisac\b",
        r"^zapisać\b",
        r"^zapamietac\b",
        r"^zapamiętać\b",
    ]
    if any(re.search(p, low) for p in note_patterns):
        return "note"

    idea_patterns = [
        r"^pomys[łl]\b",
        r"^idea\b",
        r"^brainstorm\b",
        r"^koncepcja\b",
        r"^wizja\b",
        r"^inspiracja\b",
        r"^mo[żz]na by\b",
        r"^fajnie by by[łl]o\b",
    ]
    if any(re.search(p, low) for p in idea_patterns):
        return "idea"

    # v5.1 fix:
    # if it's action-oriented and has time/date, treat it as a task FIRST
    if _looks_like_task(low) and _has_schedule(low):
        return "task"

    reminder_patterns = [
        r"\burodzin",
        r"\bimienin",
        r"\brocznic",
        r"\bspotkani",
        r"\bwizyta",
        r"\bdentyst",
        r"\blekarz",
        r"\bjutro\b",
        r"\bdziś\b",
        r"\bdzis\b",
        r"\bpojutrze\b",
        r"\bza tydzie[nń]\b",
        r"\bponiedzia[łl]ek\b",
        r"\bwtorek\b",
        r"\bśroda\b",
        r"\bsroda\b",
        r"\bczwartek\b",
        r"\bpi[aą]tek\b",
        r"\bsobota\b",
        r"\bniedziela\b",
        r"\b\d{1,2}[:.]\d{2}\b",
        r"\b\d{1,2}\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|wrze[sś]nia|pa[zź]dziernika|listopada|grudnia)\b",
        r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b",
    ]
    if any(re.search(p, low) for p in reminder_patterns):
        return "reminder"

    if _looks_like_task(low):
        return "task"

    return "note"


def _kind_label(kind: str) -> str:
    return {
        "task": "task",
        "idea": "idea",
        "reminder": "reminder",
        "note": "note",
    }.get((kind or "").strip().lower(), "note")


def is_auto_task_candidate(text: str) -> bool:
    low = (text or "").strip().lower()
    return _classify_inbox_text(low) == "task" and _has_schedule(low)


def load_inbox() -> List[Dict[str, Any]]:
    data = _read_json(INBOX_FILE, default=[])
    if not isinstance(data, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        kind = str(item.get("kind") or "").strip().lower() or _classify_inbox_text(text)
        out.append(
            {
                "id": int(item.get("id") or 0),
                "text": text,
                "created_at": str(item.get("created_at") or _now_iso()),
                "kind": _kind_label(kind),
            }
        )
    return out


def save_inbox(items: List[Dict[str, Any]]) -> None:
    _write_json(INBOX_FILE, items)


def _next_id(items: List[Dict[str, Any]]) -> int:
    max_id = 0
    for it in items:
        try:
            max_id = max(max_id, int(it.get("id") or 0))
        except Exception:
            continue
    return max_id + 1


def _reply_from_task_add(out: Any) -> str:
    if isinstance(out, dict):
        reply = out.get("reply")
        if isinstance(reply, str) and reply.strip():
            return reply.strip()
        task = out.get("task")
        if isinstance(task, dict):
            title = str(task.get("title") or task.get("text") or "zadanie").strip()
            return f"✅ Dodane zadanie: {title}"
    if isinstance(out, str) and out.strip():
        return out.strip()
    return "✅ Dodane zadanie."


def add_inbox(text: str, *, kind: str = "") -> Dict[str, Any]:
    clean = _normalize_spaces(text)
    if not clean:
        return {"ok": False, "reply": "Nie mam czego zapisać do Inbox."}

    normalized = _normalize_auto_task_text(clean)
    final_kind = _kind_label(kind or _classify_inbox_text(clean))

    # 1) task + time/date -> create task directly
    if is_auto_task_candidate(normalized):
        try:
            from app.b2c import tasks as tasks_mod
            out = tasks_mod.add_task(f"dodaj: {normalized}")
            if isinstance(out, dict) and out.get("task"):
                return {
                    "ok": True,
                    "auto_task": True,
                    "reply": f"⚡ Automatycznie utworzyłam zadanie: {_reply_from_task_add(out)}",
                    "task": out.get("task"),
                }
        except Exception:
            pass

    # 2) ideas / notes / reminders -> direct buckets
    if final_kind in {"idea", "note", "reminder"}:
        dup_idx = _bucket_duplicate_index(final_kind, clean)
        if dup_idx is not None:
            label = _bucket_label(final_kind, locative=True)
            existing = _load_bucket(final_kind)[dup_idx - 1]
            return {
                "ok": True,
                "duplicate": True,
                "reply": f"⚠️ To już jest w {label} #{dup_idx}: {existing['text']}",
                "item": existing,
            }

        record = {
            "text": clean,
            "created_at": _now_iso(),
            "source": "capture",
            "kind": final_kind,
        }
        data = _load_bucket(final_kind)
        data.append(record)
        _save_bucket(final_kind, data)

        if final_kind == "idea":
            reply = f"💡 Zapisałam do pomysłów: {clean}"
        elif final_kind == "note":
            reply = f"📝 Zapisałam do notatek: {clean}"
        else:
            reply = f"⏰ Zapisałam do reminders: {clean}"

        return {"ok": True, "direct_bucket": True, "reply": reply, "item": record}

    # 3) task without schedule -> stays in inbox
    items = load_inbox()
    dup = _find_duplicate_inbox(items, clean)
    if dup:
        return {
            "ok": True,
            "duplicate": True,
            "reply": f"⚠️ To już jest w Inbox #{dup['id']}: {dup['text']}",
            "item": dup,
        }

    item = {
        "id": _next_id(items),
        "text": clean,
        "created_at": _now_iso(),
        "kind": final_kind,
    }
    items.append(item)
    save_inbox(items)
    return {
        "ok": True,
        "item": item,
        "reply": f"🧠 Zapisano do Inbox #{item['id']} [{item['kind']}]: {item['text']}",
    }
def list_inbox() -> Dict[str, Any]:
    items = load_inbox()
    if not items:
        return {"ok": True, "items": [], "reply": "Inbox jest pusty."}
    lines = ["INBOX", ""]
    for idx, item in enumerate(items, start=1):
        lines.append(f"{idx}. [{item['kind']}] {item['text']}")
    return {"ok": True, "items": items, "reply": "\n".join(lines)}


def delete_inbox_by_live_number(n: int) -> Dict[str, Any]:
    items = load_inbox()
    if n < 1 or n > len(items):
        return {"ok": False, "reply": f"Nie ma wpisu #{n} w Inbox."}
    removed = items.pop(n - 1)
    save_inbox(items)
    return {"ok": True, "removed": removed, "reply": f"🗑 Usunięto z Inbox #{n}: {removed['text']}"}


def get_inbox_by_live_number(n: int) -> Optional[Dict[str, Any]]:
    items = load_inbox()
    if n < 1 or n > len(items):
        return None
    return items[n - 1]


def pop_inbox_by_live_number(n: int) -> Optional[Dict[str, Any]]:
    items = load_inbox()
    if n < 1 or n > len(items):
        return None
    item = items.pop(n - 1)
    save_inbox(items)
    return item


def clear_inbox() -> Dict[str, Any]:
    items = load_inbox()
    count = len(items)
    save_inbox([])
    return {"ok": True, "reply": f"🧹 Wyczyszczono Inbox ({count}).", "count": count}


def list_bucket(path: Path, title: str) -> Dict[str, Any]:
    data = _read_json(path, default=[])
    empty_reply = {
        "POMYSŁY": "Pomysły są puste.",
        "NOTATKI": "Notatki są puste.",
        "REMINDERS": "Reminders są puste.",
    }.get((title or "").upper(), f"{title} są puste.")
    if not isinstance(data, list) or not data:
        return {"ok": True, "reply": empty_reply}
    lines = [title.upper(), ""]
    for idx, item in enumerate(data, start=1):
        text = str(item.get("text") or "").strip()
        if text:
            lines.append(f"{idx}. {text}")
    return {"ok": True, "reply": "\n".join(lines) if len(lines) > 2 else empty_reply}



def list_ideas() -> Dict[str, Any]:
    return list_bucket(IDEAS_FILE, "POMYSŁY")


def list_notes() -> Dict[str, Any]:
    return list_bucket(NOTES_FILE, "NOTATKI")


def list_reminders() -> Dict[str, Any]:
    return list_bucket(REMINDERS_FILE, "REMINDERS")

def process_inbox_item(n: int) -> Dict[str, Any]:
    items = load_inbox()
    if n < 1 or n > len(items):
        return {"ok": False, "reply": f"Nie ma wpisu #{n} w Inbox."}

    item = items[n - 1]
    kind = _kind_label(item.get("kind") or _classify_inbox_text(item.get("text", "")))

    if kind == "task":
        return {
            "ok": True,
            "kind": "task",
            "reply": f"📌 To wpis typu task: {item['text']}\nUżyj: `utwórz zadanie z inbox {n} dziś 15:00` albo `utwórz zadanie z inbox {n} jutro`.",
            "item": item,
        }

    item = items.pop(n - 1)
    save_inbox(items)

    record = {
        "text": item["text"],
        "created_at": item.get("created_at") or _now_iso(),
        "processed_at": _now_iso(),
        "source": "inbox",
        "kind": kind,
    }

    if kind == "idea":
        _append_record(IDEAS_FILE, record)
        return {"ok": True, "reply": f"💡 Przeniesiono do pomysłów: {record['text']}", "item": record}
    if kind == "note":
        _append_record(NOTES_FILE, record)
        return {"ok": True, "reply": f"📝 Przeniesiono do notatek: {record['text']}", "item": record}
    if kind == "reminder":
        _append_record(REMINDERS_FILE, record)
        return {"ok": True, "reply": f"⏰ Przeniesiono do reminders: {record['text']}", "item": record}

    return {"ok": False, "reply": "Nie udało się przetworzyć wpisu."}


def preview_processing() -> Dict[str, Any]:
    items = load_inbox()
    if not items:
        return {"ok": True, "reply": "Inbox jest pusty."}
    lines = ["PRZETWARZANIE INBOX", ""]
    for idx, item in enumerate(items, start=1):
        kind = _kind_label(item.get("kind") or _classify_inbox_text(item.get("text", "")))
        action = {
            "task": "→ utwórz zadanie przez komendę",
            "idea": "→ pomysły",
            "reminder": "→ reminders",
            "note": "→ notatki",
        }.get(kind, "→ notatki")
        lines.append(f"{idx}. [{kind}] {item['text']}")
        lines.append(f"   {action}")
    return {"ok": True, "reply": "\n".join(lines)}


def delete_bucket_item(kind: str, n: int) -> Dict[str, Any]:
    data = _load_bucket(kind)
    if n < 1 or n > len(data):
        return {"ok": False, "reply": f"Nie ma wpisu #{n} w bucketcie."}
    removed = data.pop(n - 1)
    _save_bucket(kind, data)
    return {"ok": True, "removed": removed, "reply": f"🗑 Usunięto {_bucket_label(kind)} #{n}: {removed['text']}"}


def clear_bucket(kind: str) -> Dict[str, Any]:
    data = _load_bucket(kind)
    count = len(data)
    _save_bucket(kind, [])
    return {
        "ok": True,
        "count": count,
        "reply": f"🧹 Wyczyszczono {_bucket_label(kind, plural=True)} ({count}).",
    }


def move_all_bucket_to_task(kind: str, suffix: str = '') -> Dict[str, Any]:
    data = _load_bucket(kind)
    if not data:
        return {"ok": True, "count": 0, "reply": f"{_bucket_label(kind, plural=True).capitalize()} są puste."}

    moved = []
    failed = []
    left = []

    try:
        from app.b2c import tasks as tasks_mod
    except Exception:
        return {"ok": False, "reply": "Nie udało się utworzyć zadań."}

    for idx, item in enumerate(data, start=1):
        text = str(item.get('text') or '').strip()
        final_text = text if not suffix.strip() else f"{text} {suffix.strip()}"
        try:
            out = tasks_mod.add_task(f"dodaj: {final_text}")
        except Exception:
            out = None

        if isinstance(out, dict) and out.get('task'):
            moved.append(text)
        else:
            failed.append((idx, text, _reply_from_task_add(out)))
            left.append(item)

    _save_bucket(kind, left)

    base = f"📌 Przeniesiono {_bucket_label(kind, plural=True)} do zadań: {len(moved)}"
    if failed:
        base += f". Nie udało się: {len(failed)}"
    return {
        "ok": len(failed) == 0,
        "count": len(moved),
        "failed": failed,
        "reply": base,
    }


def edit_bucket_item(kind: str, n: int, new_text: str) -> Dict[str, Any]:
    clean = _normalize_spaces(new_text)
    if not clean:
        return {"ok": False, "reply": "Podaj nową treść po numerze."}
    data = _load_bucket(kind)
    if n < 1 or n > len(data):
        return {"ok": False, "reply": f"Nie ma wpisu #{n} w bucketcie."}
    dup_idx = _bucket_duplicate_index(kind, clean, ignore_index=n)
    if dup_idx is not None:
        existing = data[dup_idx - 1]
        label = _bucket_label(kind, locative=True)
        return {"ok": False, "duplicate": True, "reply": f"⚠️ Taki wpis już jest w {label} #{dup_idx}: {existing['text']}"}
    before = str(data[n - 1].get('text') or '').strip()
    data[n - 1]['text'] = clean
    data[n - 1]['updated_at'] = _now_iso()
    _save_bucket(kind, data)
    return {"ok": True, "item": data[n - 1], "reply": f"✏️ Zmieniono {_bucket_label(kind)} #{n}: {before} → {clean}"}


def move_bucket_item_to_task(kind: str, n: int, suffix: str = '') -> Dict[str, Any]:
    data = _load_bucket(kind)
    if n < 1 or n > len(data):
        return {"ok": False, "reply": f"Nie ma wpisu #{n} w bucketcie."}
    item = data[n - 1]
    text = str(item.get('text') or '').strip()
    final_text = text if not suffix.strip() else f"{text} {suffix.strip()}"
    try:
        from app.b2c import tasks as tasks_mod
        out = tasks_mod.add_task(f"dodaj: {final_text}")
    except Exception:
        return {"ok": False, "reply": "Nie udało się utworzyć zadania."}
    if isinstance(out, dict) and out.get('task'):
        removed = data.pop(n - 1)
        _save_bucket(kind, data)
        return {
            "ok": True,
            "removed": removed,
            "task": out.get('task'),
            "reply": f"📌 Przeniesiono {_bucket_label(kind)} #{n} do zadania: {_reply_from_task_add(out)}",
        }
    reply = _reply_from_task_add(out)
    return {"ok": False, "reply": reply}
