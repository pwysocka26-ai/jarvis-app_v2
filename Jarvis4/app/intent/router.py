from __future__ import annotations

import re
from typing import Dict, Any, List

from app.config import settings
from app.pro_mode import is_pro_enabled, set_pro_enabled
from app.llm.ollama_client import OllamaClient
from app.memory.factory import get_memory_store
from app.pro.pm_tools import handle_pro_command


def _normalize(s: str) -> str:
    return (s or "").strip()


def _norm_lower(s: str) -> str:
    return _normalize(s).lower()


def _format_profile(profile: Dict[str, Any]) -> str:
    if not profile:
        return "Nie mam jeszcze Twojego profilu. Ustaw go np.: profil: city=Warszawa; job=PM"
    lines = ["Twój profil:"]
    for k, v in profile.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def _format_goals(goals: List[str]) -> str:
    if not goals:
        return "Nie mam jeszcze celu. Ustaw go np.: cel: Zbudować Jarvisa B2C"
    if len(goals) == 1:
        return f"Twój cel: {goals[0]}"
    out = ["Twoje cele:"] + [f"{i+1}. {g}" for i, g in enumerate(goals)]
    return "\n".join(out)


def _build_system_prompt(
    profile: Dict[str, Any],
    goals: List[str],
    facts: List[str],
    persona: str,
) -> str:
    """Build a compact system prompt.

    Persona:
      - b2c: bardziej ludzki / przyjacielski, ale nadal normalnie (bez przesady)
      - pro: rzeczowy, zadaniowy, mniej small talk
    """

    persona = (persona or "b2c").lower().strip()

    if persona == "pro":
        style = (
            "Tryb PRO (ukryty): bądź maksymalnie rzeczowy, techniczny i zadaniowy. "
            "Minimum small talk. Gdy brakuje danych — dopytaj 1 pytaniem."
        )
    else:
        # Default: B2C-friendly
        style = (
            "Tryb B2C: mów jak przyjazny pomocnik (naturalnie, bez sztucznej egzaltacji). "
            "Używaj prostego języka, dbaj o ciepły ton. "
            "Emoji najwyżej sporadycznie (0–1 w wiadomości) i tylko gdy pasuje. "
            "Na końcu możesz zadać 1 krótkie pytanie, jeśli to pomaga."
        )

    parts = [
        "Jesteś Jarvis — osobisty asystent użytkownika.",
        "Odpowiadaj po polsku.",
        style,
    ]
    if profile:
        parts.append("Profil użytkownika: " + ", ".join([f"{k}={v}" for k, v in profile.items()]))
    if goals:
        parts.append("Cel(e) użytkownika: " + "; ".join(goals))
    if facts:
        # keep small to avoid prompt bloat
        parts.append("Fakty do pamiętania: " + "; ".join(facts[-25:]))
    return "\n".join(parts)


def route_intent(message: str, *, mode: str | None = None) -> Dict[str, str]:
    """Rule-based router:
    - obsługuje komendy pamięci/profilu/celu/statusu
    - inaczej: LLM (Ollama) lub echo fallback
    """

    msg = _normalize(message)
    low = msg.lower()

    store = get_memory_store()
    # MemoryStore (file) ma KV; DB store może nie mieć — zabezpieczamy się getattr
    get_kv = getattr(store, "get_kv", None)
    set_kv = getattr(store, "set_kv", None)

    profile = (get_kv("profile", {}) if callable(get_kv) else {})
    if not isinstance(profile, dict):
        profile = {}

    goals = (get_kv("goals", []) if callable(get_kv) else [])
    if isinstance(goals, str):
        goals = [goals]
    if not isinstance(goals, list):
        goals = []

    # ---------- MODE / PERSONA ----------
    # New architecture: client selects mode per-session and sends it with each request.
    # Backward compatible: if mode is not provided, we fall back to KV/settings.
    persona = (mode or (get_kv("persona", settings.persona) if callable(get_kv) else settings.persona))
    persona = (persona or "b2c").lower().strip()
    if persona in {"a", "tryb a", "tryb: a"}:
        persona = "b2c"
    if persona in {"b", "tryb b", "tryb: b"}:
        persona = "pro"
    if persona not in {"b2c", "pro"}:
        persona = "b2c"

    # NOTE: Mode switching is now handled by the CLI (/mode b2c | /mode pro).
    # We keep these commands for backward compatibility.
    if low in {"/b2c", "b2c", "tryb b2c", "tryb: b2c", "tryb a", "tryb: a", "a"}:
        if callable(set_kv):
            set_kv("persona", "b2c")
        return {"response": "✅ Ustawione: Tryb B2C. (Tip: w CLI używaj /mode b2c)"}

    # PRO: hidden by default, but can be enabled either:
    # 1) env var at server startup (JARVIS_PRO_ENABLED=1/true)
    # 2) runtime override: /pro on | /pro off (no server restart needed)
    if low in {"/pro on", "/pro: on", "pro on", "tryb pro on"}:
        set_pro_enabled(True)
        if callable(set_kv):
            set_kv("persona", "pro")
        return {"response": "✅ PRO włączony (tymczasowo, bez restartu)."}

    if low in {"/pro off", "/pro: off", "pro off", "tryb pro off"}:
        set_pro_enabled(False)
        if callable(set_kv):
            set_kv("persona", "b2c")
        return {"response": "✅ PRO wyłączony (wracam do B2C)."}

    if low in {"/pro", "pro", "tryb pro", "tryb: pro", "tryb b", "tryb: b", "b"}:
        if not is_pro_enabled():
            return {
                "response": (
                    "Tryb PRO jest ukryty/wyłączony. "
                    "Możesz go włączyć na 2 sposoby:\n"
                    "1) Bez restartu: wpisz /pro on\n"
                    "2) Na stałe przy starcie serwera: uruchom serwer z env (trzeba zrestartować serwer):\n"
                    "   PowerShell: $env:JARVIS_PRO_ENABLED=1; python -m uvicorn app.main:app --host 127.0.0.1 --port 8010\n"
                    "   CMD: set JARVIS_PRO_ENABLED=1 && python -m uvicorn app.main:app --host 127.0.0.1 --port 8010\n"
                    "   Uwaga: samo wpisanie `JARVIS_PRO_ENABLED=1` w PowerShell nie działa (musi być $env:...)\n"
                    "   (albo użyj start_local.ps1)"
                )
            }
        if callable(set_kv):
            set_kv("persona", "pro")
        return {"response": "✅ Ustawione: Tryb PRO. (Tip: w CLI używaj /mode pro)"}

    # ---------- PRO: lokalne narzędzia PM / pliki ----------
    # Komendy działają tylko w trybie PRO.
    if persona == "pro":
        # pro command handler currently accepts only the raw message.
        # keep the orchestrator/settings access inside pro layer.
        handled = handle_pro_command(msg)

        # handle_pro_command returns a tuple (handled: bool, reply: str)
        # or (legacy) a plain string/None.
        if isinstance(handled, tuple) and len(handled) >= 2:
            was_handled = bool(handled[0])
            reply = "" if handled[1] is None else str(handled[1])
            if was_handled:
                return {"response": reply}
        else:
            if handled is not None:
                # already a user-facing reply
                return {"response": str(handled)}

    # ---------- STATUS ----------
    if low in {"/status", "status", "stan", "jak stoi status"}:
        goal_txt = goals[0] if goals else None
        city = profile.get("city") or profile.get("miasto")
        job = profile.get("job") or profile.get("rola")
        parts = []
        if goal_txt:
            parts.append(f"Cel: {goal_txt}")
        if city or job:
            parts.append(f"Profil: {city or '-'}; {job or '-'}")
        if not parts:
            return {"response": "Status: brak ustawionego profilu i celu. Możesz dodać: profil: city=Warszawa; job=PM oraz cel: ..."}
        return {"response": "Status Jarvisa: " + " | ".join(parts)}

    # ---------- PROFIL ----------
    if low.startswith("profil:") or low.startswith("profile:"):
        payload = msg.split(":", 1)[1].strip()
        # format: key=value; key=value
        pairs = [p.strip() for p in re.split(r"[;\n]", payload) if p.strip()]
        updated = dict(profile)
        for p in pairs:
            if "=" in p:
                k, v = p.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k:
                    updated[k] = v
        if callable(set_kv):
            set_kv("profile", updated)
        return {"response": "✅ Profil zapisany\n" + _format_profile(updated)}

    if low in {"pokaż profil", "pokaz profil", "show profile", "profil"}:
        return {"response": _format_profile(profile)}

    # ---------- CELE ----------
    if low.startswith("cel:") or low.startswith("goal:"):
        goal = msg.split(":", 1)[1].strip()
        if goal:
            # utrzymuj listę celów + pole główne
            new_goals = list(goals)
            new_goals.append(goal)
            if callable(set_kv):
                set_kv("goal", goal)
                set_kv("goals", new_goals)
            return {"response": f"✅ Cel dodany: {goal}\n" + _format_goals(new_goals)}
        return {"response": "Podaj cel po dwukropku, np.: cel: Zbudować Jarvisa B2C"}

    if low in {"pokaż cel", "pokaz cel", "pokaż cele", "pokaz cele", "cele", "cel"}:
        # jeśli goals puste, spróbuj goal
        if not goals and callable(get_kv):
            g = get_kv("goal", "")
            if g:
                goals = [g]
        return {"response": _format_goals(goals)}

    # ---------- PAMIĘĆ (FAKTY LISTA) ----------
    if low.startswith("zapamiętaj:") or low.startswith("zapamietaj:"):
        fact = msg.split(":", 1)[1].strip()
        if fact:
            store.remember_fact(fact)
            return {"response": f"✅ Zapamiętane: {fact}"}
        return {"response": "Podaj co mam zapamiętać po dwukropku, np.: zapamiętaj: Lubię Tatry"}

    if low.startswith("zapomnij:") or low.startswith("zapomnij :") or low.startswith("zapomnij ") or low.startswith("forget:"):
        fact = msg.split(":", 1)[1].strip() if ":" in msg else msg.replace("zapomnij", "", 1).strip()
        if fact:
            store.forget_fact(fact)
            return {"response": f"✅ Zapomniane: {fact}"}
        return {"response": "Podaj co mam zapomnieć, np.: zapomnij: Tatry"}

    if low in {"pamięć", "pamiec", "memory"}:
        facts = store.list_facts()
        if not facts:
            return {"response": "Nie mam jeszcze zapisanych faktów. Użyj: zapamiętaj: ..."}
        out = ["Twoja pamięć:"] + [f"{i+1}. {x}" for i, x in enumerate(facts)]
        return {"response": "\n".join(out)}

    # ---------- ZWYKŁA ROZMOWA ----------
    if not settings.use_ollama:
        return {"response": f"Jarvis odpowiada: {msg}"}

    facts = store.list_facts()
    system_prompt = _build_system_prompt(profile, goals, facts, persona)
    llm = OllamaClient(settings.ollama_base_url, settings.ollama_model, timeout_s=settings.ollama_timeout_s)

    history = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": msg},
    ]
    answer = llm.chat(history)
    return {"response": answer}


# --- B2C lightweight intent routing ---
def b2c_light_intent(message: str):
    low = message.lower().strip()
    if low in {'cześć','czesc','hej','hello','hi'}:
        return 'Hej! 😊 Jak mogę pomóc?'
    if low in {'pomoc','help'}:
        return 'Mogę odpowiadać na pytania, pomagać i zapamiętywać informacje.'
    return None
