# Test "rano" + dojazd + przypomnienie (CLI)

Ten test jest do wykonania ręcznie w **Jarvis CLI** i ma potwierdzić, że:
- `rano` pokazuje listę + fokus dnia
- Jarvis prosi o sposób dojazdu i zapisuje go
- Jarvis proponuje godzinę wyjścia i potrafi zapisać przypomnienie

## 0) Przyspieszony tryb testowy (opcjonalnie)

Żeby nie czekać 25–40 minut na przypomnienie, uruchom serwer z flagą:

- Windows PowerShell:
  - `$env:JARVIS_FAST_TEST="1"; python -m uvicorn app.main:app --reload`

W tym trybie Jarvis liczy dojazd jako **1 minuta**, a bufor jako **0 minut**.

## 1) Czyszczenie

1. Uruchom Jarvis CLI.
2. Wpisz: `lista`
3. Jeśli są stare zadania testowe, usuń je: `usuń 1`, `usuń 2`, ...

## 2) Dodanie zadania z godziną i adresem

1. Dodaj zadanie na **dziś**, np. za 3–5 minut:

   `dodaj: dentysta, dziś 21:40, Niemcewicza 25, Warszawa, p1, 30m`

   (możesz zmienić godzinę na aktualną + kilka minut)

2. Sprawdź: `lista` — zadanie powinno się pojawić.

## 3) Flow "rano"

1. Wpisz: `rano`
2. Jarvis powinien:
   - wypisać listę na dziś
   - pokazać **Fokus dnia**
   - poprosić o sposób dojazdu

3. Wpisz np.: `samochodem` (albo `komunikacją` / `rowerem` / `pieszo`)

4. Jarvis powinien:
   - potwierdzić ustawienie
   - pokazać proponowaną godzinę wyjścia
   - zapytać czy ustawić przypomnienie

5. Wpisz: `tak`

6. Wpisz: `/diag`
   - w diagnostyce powinno być widać, że `tasks.json` istnieje
   - jeśli masz podgląd plików, sprawdź też `data/memory/pending_reminder.json`

## 4) Oczekiwany efekt przypomnienia

Gdy nadejdzie godzina wyjścia, w CLI powinno pojawić się powiadomienie w stylu:

`⏰ Przypomnienie: wyjdź teraz – żeby zdążyć na: dentysta (Niemcewicza 25, Warszawa)`
