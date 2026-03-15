
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Dict, Optional


CONV_PREFIXES = (
    "muszę ", "musze ", "mam ", "powinnam ", "powinienem ",
    "chcę ", "chce ", "potrzebuję ", "potrzebuje ", "trzeba "
)


def _normalize_hhmm(value: str) -> str:
    value = (value or "").strip()
    if ":" in value:
        hh, mm = value.split(":", 1)
        return f"{int(hh):02d}:{int(mm):02d}"
    return f"{int(value):02d}:00"


def _day_to_date(day_word: str) -> str:
    low = (day_word or "").strip().lower()
    if low in {"jutro"}:
        return (date.today() + timedelta(days=1)).isoformat()
    return date.today().isoformat()


def _clean_prefix(text: str) -> str:
    out = (text or "").strip()
    low = out.lower()
    for pref in CONV_PREFIXES:
        if low.startswith(pref):
            out = out[len(pref):].strip()
            break
        low = out.lower()
    return out


def _normalize_title(title: str) -> str:
    t = _clean_prefix(title).strip(" ,.")
    low = t.lower()

    replacements = {
        "do dentysty": "dentysta",
        "dentystę": "dentysta",
        "dentyste": "dentysta",
        "na spotkanie": "spotkanie",
        "na trening": "trening",
    }
    for src, dst in replacements.items():
        if low.startswith(src):
            t = dst + t[len(src):]
            break

    t = re.sub(r"^i\s+", "", t, flags=re.I).strip(" ,.")
    return t or "(bez tytułu)"


def _split_title_location(rest: str) -> tuple[str, Optional[str]]:
    text = _normalize_title(rest)
    if "," in text:
        first, second = text.split(",", 1)
        return first.strip(), second.strip() or None
    return text, None


def _add_synthetic(tasks_mod, synthetic: str) -> Dict[str, Any]:
    out = tasks_mod.add_task(synthetic)
    reply = None
    if isinstance(out, dict):
        reply = out.get("reply") or out.get("response")
    reply = str(reply or "OK")
    return {"intent": "conversational_add", "reply": reply}


def maybe_handle_conversational(message: str, tasks_mod) -> Optional[Dict[str, Any]]:
    raw = (message or "").strip()
    low = raw.lower()

    # Conversational dashboard / day overview
    if low in {
        "co mam dzisiaj zrobić", "co mam dzisiaj zrobic", "co mam dziś zrobić", "co mam dzis zrobic",
        "jak wygląda mój dzień", "jak wyglada moj dzien", "jak wygląda dzisiaj mój dzień", "jak wyglada dzisiaj moj dzien",
        "pokaż mój dzień", "pokaz moj dzien"
    }:
        return {"intent": "conversational_redirect", "command": "centrum dowodzenia"}

    # "muszę jutro o 14 do dentysty"
    patterns = [
        r"^(?P<prefix>muszę|musze|mam|powinnam|powinienem|chcę|chce|potrzebuję|potrzebuje|trzeba)\s+(?P<day>jutro|dziś|dzis|dzisiaj)\s+(?:o\s*)?(?P<time>\d{1,2}(?::\d{2})?)\s+(?P<rest>.+)$",
        r"^(?P<prefix>muszę|musze|mam|powinnam|powinienem|chcę|chce|potrzebuję|potrzebuje|trzeba)\s+(?P<rest>.+?)\s+(?P<day>jutro|dziś|dzis|dzisiaj)\s+(?:o\s*)?(?P<time>\d{1,2}(?::\d{2})?)$",
        r"^(?P<prefix>muszę|musze|mam|powinnam|powinienem|chcę|chce|potrzebuję|potrzebuje|trzeba)\s+(?P<rest>.+?)\s+o\s+(?P<time>\d{1,2}(?::\d{2})?)\s+(?P<day>jutro|dziś|dzis|dzisiaj)$",
        r"^(?P<day>jutro|dziś|dzis|dzisiaj)\s+(?:o\s*)?(?P<time>\d{1,2}(?::\d{2})?)\s+(?P<rest>.+)$",
        r"^(?P<rest>.+?)\s+(?P<day>jutro|dziś|dzis|dzisiaj)\s+(?:o\s*)?(?P<time>\d{1,2}(?::\d{2})?)$",
    ]
    for pat in patterns:
        m = re.match(pat, raw, flags=re.I)
        if not m:
            continue
        due_date = _day_to_date(m.group("day"))
        due_time = _normalize_hhmm(m.group("time"))
        title, location = _split_title_location(m.group("rest"))
        synthetic = f"dodaj: {due_date} {due_time} {title}"
        if location:
            synthetic += f", {location}"
        return _add_synthetic(tasks_mod, synthetic)

    # "muszę do dentysty o 14" -> today
    m_today = re.match(
        r"^(?P<prefix>muszę|musze|mam|powinnam|powinienem|chcę|chce|potrzebuję|potrzebuje|trzeba)\s+(?P<rest>.+?)\s+o\s+(?P<time>\d{1,2}(?::\d{2})?)$",
        raw,
        flags=re.I,
    )
    if m_today:
        due_date = date.today().isoformat()
        due_time = _normalize_hhmm(m_today.group("time"))
        title, location = _split_title_location(m_today.group("rest"))
        synthetic = f"dodaj: {due_date} {due_time} {title}"
        if location:
            synthetic += f", {location}"
        return _add_synthetic(tasks_mod, synthetic)

    return None
