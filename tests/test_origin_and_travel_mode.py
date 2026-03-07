"""Tests around origin/start selection and travel mode switching.

These tests are intentionally *flow-aware*:
- If the system asks follow-up questions, we answer them.
- Assertions are about stable behavior, not brittle exact wording.
"""


def test_set_origin_home_then_rano(chat2):
    # Explicitly set home origin (command should be accepted even if already set)
    r1 = chat2("ustaw dom: Narbutta 86, Warszawa")
    assert r1.status_code == 200

    # Rano should now work without forcing an origin prompt.
    r2 = chat2("rano")
    assert r2.status_code == 200
    data = r2.json()
    assert isinstance(data.get("reply", ""), str)


def test_travel_mode_command_sets_mode(chat2):
    # If system asks where you are, chat2 fixture will answer automatically.
    r1 = chat2("tryb: rower")
    assert r1.status_code == 200
    reply1 = (r1.json().get("reply") or "").lower()
    assert "ustawiono" in reply1 or "tryb" in reply1

    # Toggle to car
    r2 = chat2("tryb: samochodem")
    assert r2.status_code == 200
    reply2 = (r2.json().get("reply") or "").lower()
    assert "ustawiono" in reply2 or "tryb" in reply2
