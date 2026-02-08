import os, httpx
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

async def ollama_generate(prompt):
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False})
        return r.json()["response"]
