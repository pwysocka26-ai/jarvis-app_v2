PATCH: MemoryStore.load_facts()

Co naprawia:
- 500 Internal Server Error: AttributeError: 'MemoryStore' object has no attribute 'load_facts'
- kompatybilność wstecz: jeśli w pamięci jest stary format (lista) -> nie wywali serwera

Jak wdrożyć:
1) Rozpakuj ZIP w dowolnym miejscu
2) Skopiuj plik:
   app/memory/store.py
   do Twojego projektu (nadpisz istniejący)
3) Zrestartuj serwer Jarvisa

Uwaga:
- Ten MemoryStore trzyma dane w JSON:
  { "history": [...], "facts": {...} }
- Jeżeli masz stary plik jako listę, zostanie automatycznie potraktowany jako "history".
