Podmień plik:
Jarvis4/app/b2c/tasks.py

ZIP zawiera docelową ścieżkę:
app/b2c/tasks.py

Nowość:
- duplicate protection w add_task()
- bez ruszania routera
- nie dodaje drugiego identycznego taska jeśli istnieje aktywny task z tym samym tytułem, terminem, lokalizacją i trybem dojazdu
