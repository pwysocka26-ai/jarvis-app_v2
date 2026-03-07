# Smoke test: dodawanie zadania -> rano -> ustawienie transportu


def test_add_task_today_and_rano_flow(client):
    def chat(msg: str, mode: str = "b2c"):
        r = client.post("/v1/chat", json={"message": msg, "mode": mode})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "reply" in data
        return data

    data_add = chat("dodaj: test przypomnienia, dziś 21:40, Niemcewicza 25, Warszawa")
    assert data_add.get("intent") in ("add_task", "add"), data_add

    data_rano = chat("rano")
    txt = data_rano["reply"]

    assert "Najważniejsze dziś" in txt
    assert "21:40" in txt, txt
    assert "Jak jedziesz" in txt

    data_transport = chat("samochodem")
    assert "Ustawiono" in data_transport["reply"]
