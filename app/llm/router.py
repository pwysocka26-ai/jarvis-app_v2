"""
Zachowujemy kompatybilność: reszta aplikacji importuje `ask_llm` z app.llm.router.
Ten plik tylko deleguje do stabilnego routera providerów.
"""

from app.llm.providers import ask_llm  # re-export
