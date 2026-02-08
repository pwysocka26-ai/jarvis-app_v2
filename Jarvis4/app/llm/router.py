"""
Zachowujemy kompatybilność: reszta aplikacji importuje `ask_llm` z app.llm.router.
Ten plik tylko deleguje do stabilnego routera providerów.
"""

from app.llm.providers import ask_llm  # re-export


# --- B2C lightweight intent routing ---
def b2c_light_intent(message: str):
    low = message.lower().strip()
    if low in {'cześć','czesc','hej','hello','hi'}:
        return 'Hej! 😊 Jak mogę pomóc?'
    if low in {'pomoc','help'}:
        return 'Mogę odpowiadać na pytania, pomagać i zapamiętywać informacje.'
    return None
