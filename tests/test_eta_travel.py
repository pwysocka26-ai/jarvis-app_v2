def test_travel_mode_command_sets_mode(chat2):
    r = chat2("tryb: samochodem")
    assert r.status_code == 200
    data = r.json()
    assert data.get("intent") in (
        "set_travel_mode",
        "travel_mode",
        "set_mode",
        "set_travel",
        "set_origin_mode",
    )
    reply = (data.get("reply") or data.get("message") or "").lower()
    assert reply.strip() != ""

def test_eta_without_google_key_is_graceful(chat2):
    r1 = chat2("dodaj: dentysta dziś 18:30 Narbutta 86, Warszawa")
    assert r1.status_code == 200

    r2 = chat2("eta")
    assert r2.status_code == 200
    data = r2.json()
    reply = (data.get("reply") or data.get("message") or "")
    assert reply.strip() != ""

    low = reply.lower()
    assert (
        ("google" in low)
        or ("maps" in low)
        or ("eta" in low)
        or ("wyjdź" in low)
        or ("aby włączyć eta" in low)
        or ("skąd ruszasz" in low)
    )
