# Memory Base 1.2.2 + 1.3 (C - Hybrid, Autosave A)

## Co to robi
- Pamięć trwała: zapis profilu + historii do `./data/memory/`
- Hybrid: pamięć zawsze trafia do system promptu
- Autosave (A): fakty z wiadomości użytkownika zapisują się automatycznie (deterministycznie, bez LLM)

## Pliki w paczce
- app/orchestrator/memory.py
- app/orchestrator/core.py
- app/orchestrator/llm.py

## Ustawienia ENV (opcjonalne)
- MEMORY_ENABLED=true
- MEMORY_AUTOSAVE=true
- MEMORY_DIR=./data/memory
- MEMORY_MAX_HISTORY_CHARS=12000
- LLM_PROVIDER=stub   (jeśli nie masz podpiętego LLM; w praktyce ustawiasz swój)

## Test
1) uruchom serwer
2) w CLI:
   - "Mam na imię Paulina"
   - restart CLI
   - "Jak mam na imię?"
Powinno odpowiedzieć z pamięci.
