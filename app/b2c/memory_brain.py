
# memory_brain.py (patched)
memory_store = []

def remember(text):
    memory_store.append(text)
    return f"Zapamiętałem: {text}"

def recall(name):
    results = [m for m in memory_store if name.lower() in m.lower()]
    if not results:
        return f"Nie mam jeszcze nic konkretnego o {name}."
    return "Pamiętam:\n" + "\n".join(results)

def memory_day():
    if not memory_store:
        return "MEMORY BRAIN: brak zapisanych wspomnień."
    return "MEMORY BRAIN\n" + "\n".join(memory_store)
