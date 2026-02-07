"""Local chat stub.

This repo is an MVP orchestrator. In enterprise deployments you'll plug in:
- Azure OpenAI / OpenAI API
- RAG (vector DB)
- Conversation memory (DB)

For local demos (and for Paul's first run on Windows) we provide a tiny
deterministic responder so /v1/chat "talks" back.
"""

from __future__ import annotations

from datetime import datetime


def _now_pl() -> str:
    # ISO-ish, easy to read
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def reply(text: str, user_id: str | None = None) -> str:
    t = (text or "").strip()
    u = (user_id or "").strip() or "użytkowniczko"
    low = t.lower()

    if not t:
        return f"Hej {u}! Napisz mi, w czym pomóc 🙂"

    # Tiny intent heuristics
    if any(k in low for k in ["hej", "cześć", "czesc", "siema", "halo"]):
        return f"Cześć {u}! Jestem online ({_now_pl()}). Co robimy?"

    if any(k in low for k in ["jak się masz", "co u ciebie", "co u ciebie?", "co tam"]):
        return (
            f"U mnie stabilnie ✅ (MVP tryb lokalny). "
            f"Nie mam jeszcze podpiętego LLM-a, ale mogę odpowiadać na proste pytania "
            f"i uruchamiać narzędzia. Co chcesz zrobić?"
        )

    if any(k in low for k in ["pomóż", "help", "jak", "instrukcja"]):
        return (
            "Jasne. Napisz 1 zdaniem, co dokładnie chcesz osiągnąć (np. 'wyślij maila', "
            "'dodaj wydarzenie do kalendarza', 'podsumuj plik')."
        )

    # Default: echo + next-step
    return (
        f"Słyszę: '{t}'.\n"
        "(MVP) Teraz umiem: health-check, planowanie (stub) i endpointy demonstracyjne. "
        "Jeśli chcesz prawdziwe odpowiedzi jak ChatGPT — musimy podpiąć provider LLM."
    )
