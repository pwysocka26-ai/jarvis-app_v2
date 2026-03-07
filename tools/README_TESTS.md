# Jarvis – jak uruchamiać testy (stabilnie)

## Najważniejsze
`pytest` trzeba uruchamiać **z katalogu projektu** (tam gdzie jest `pytest.ini` i folder `tests/`).
Jeśli odpalisz `pytest` np. z `C:\Users\...`, to PyTest zacznie skanować cały katalog użytkownika
i może wpaść w `AppData` → PermissionError.

## Gotowe komendy (PowerShell)
Z repo root:

- Same testy:
  - `powershell -ExecutionPolicy Bypass -File .\tools\run_tests.ps1`

- Testy + coverage:
  - `powershell -ExecutionPolicy Bypass -File .\tools\run_cov.ps1`

## Manualnie (jeśli wolisz)
1. `cd $env:USERPROFILE\Desktop\Jarvis4`
2. `.\.venv\Scripts\Activate.ps1`
3. `python -m pytest`
