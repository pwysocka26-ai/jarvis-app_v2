def route(message: str) -> dict:
    msg = message.lower().strip()

    if msg in ["exit", "/exit", "quit"]:
        return {"type": "system", "reply": "Do zobaczenia 👋"}

    if msg in ["status", "jak działasz", "czy żyjesz"]:
        return {"type": "status", "reply": "Działam stabilnie i bez crashy 💪"}

    if msg.startswith(("hej", "cześć")):
        return {"type": "chat", "reply": "Hej! Co robimy?"}

    if msg.startswith("zapamiętaj"):
        return {
            "type": "memory_add",
            "content": msg.replace("zapamiętaj", "").strip()
        }

    return {"type": "llm"}