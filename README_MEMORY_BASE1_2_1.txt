JARVIS – Memory Base 1.2.1 (gotowiec)

Co zawiera:
- app/orchestrator/memory.py – stabilny moduł pamięci (Base1) + doprecyzowanie dla LLM:
  pierwsza linia faktów zawiera zasadę, że fakty z pamięci mają pierwszeństwo przed domysłami.

Jak zastosować:
1) W Twoim projekcie podmień plik:
   Jarvis4\app\orchestrator\memory.py
2) Uruchom ponownie serwer (Ctrl+C i start jeszcze raz).
3) Testy szybkie:
   - "Mam na imię Paulina" -> zapamięta
   - "Lubię czytać książki, biegać i góry" -> zapamięta
   - "Pracuję nad Jarvisem" -> zapamięta
   - "Jak mam na imię?" / "Co lubię robić?" / "Nad czym pracuję?" -> odpowie na podstawie pamięci

Uwagi:
- Plik pamięci trzyma się w data/memory_base1/*.json (zależnie od konfiguracji).
