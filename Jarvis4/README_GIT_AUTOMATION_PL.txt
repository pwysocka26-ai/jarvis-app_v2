JARVIS4 – Git + Start (ściąga)

CODZIENNY FLOW (bez stresu)
1) Praca zawsze na branchu work:
   git checkout work

2) Po zmianach (opcjonalnie w trakcie dnia):
   git add .
   git commit -m "co zrobiłam"

3) Koniec etapu/dnia = RELEASE (automatycznie tag z datą):
   .\release.ps1
   -> robi merge work -> main + tag vYYYY-MM-DD (lub vYYYY-MM-DD-1)

COFANIE (ratunek)
- powrót do konkretnej wersji (tagu) bez psucia bieżącej pracy:
  git checkout -b ratunek v2026-02-07

SZYBKI START JARVISA (2 okna: serwer + CLI)
- w katalogu Jarvis4:
  .\start_jarvis.ps1

W CLI:
  /mode b2c
  /mode pro

UWAGA
- main = stabilne
- work = robocze
- nie wrzucamy .env ani .venv do repo (gitignore).
