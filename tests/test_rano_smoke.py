# tests/test_rano_smoke.py
# Smoke test: dodawanie zadania -> rano -> ustawienie transportu -> propozycja wyjścia/reminder prompt
#
# Uruchamiane przez tools/run_tests.(ps1|cmd)
#
# Wymaga: fastapi + starlette testclient (już w projekcie), brak potrzeby odpalania serwera.

from datetime import datetime, timedelta
import re

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def chat(msg: str, mode: str = "b2c"):
    r = client.post("/v1/chat", json={"message": msg, "mode": mode})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "reply" in data
    return data


def test_add_task_today_and_rano_flow():
    # Dodaj zadanie "dziś" z godziną (ważne dla porannego flow)
    # Uwaga: parser w projekcie mapuje "dziś HH:MM" -> dzisiejsza data.
    data_add = chat("dodaj: test przypomnienia, dziś 21:40, Niemcewicza 25, Warszawa")
    assert data_add.get("intent") in ("add_task", "add"), data_add

    # 'rano' powinno znaleźć zadanie na dziś i wypisać je
    data_rano = chat("rano")
    txt = data_rano["reply"]

    assert "Najważniejsze dziś" in txt
    # musi być 21:40 w treści (nie 20:40)
    assert "21:40" in txt, txt

    # powinno zapytać o transport (pierwsze zadanie)
    assert "Jak jedziesz" in txt

    # ustawiamy transport
    data_transport = chat("samochodem")
    assert "Ustawiono dojazd" in data_transport["reply"] or "Ustawiono" in data_transport["reply"]
