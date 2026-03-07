"""Add-task flow for a timed+location task.

Production behavior: after adding a timed+location task, Jarvis may ask:
- where you start (dom/praca/tu/adres)
- and/or travel mode
We only require that it does *not crash* and returns a reasonable follow-up.
"""


def test_add_timed_location_task_prompts_for_start_or_confirms(chat2):
    r = chat2("dodaj: dentysta dziś 18:30 Narbutta 86, Warszawa")
    assert r.status_code == 200
    reply = (r.json().get("reply") or "").lower()

    # Accept either a confirmation or a follow-up question.
    assert (
        "dodane" in reply
        or "ok" in reply
        or "skąd" in reply
        or "ruszasz" in reply
        or "jak jedziesz" in reply
        or "tryb" in reply
    )


def test_add_then_answer_start_and_travel_mode(chat2):
    # Add task -> likely prompts for start; chat2 will answer only if the prompt contains "Skąd ruszasz".
    r1 = chat2("dodaj: spotkanie dziś 19:00 Metro Politechnika")
    assert r1.status_code == 200

    # If prompt wasn't triggered, we still can set start explicitly.
    chat2("start: dom")

    # Now choose travel mode if asked later; command is always safe.
    r2 = chat2("tryb: komunikacja")
    assert r2.status_code == 200
