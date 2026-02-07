import json, os, time
from pathlib import Path

MEM_DIR = Path(os.getenv("JARVIS_MEM_DIR", "memory"))
CHAT_LOG = MEM_DIR / "chat.jsonl"
MEM_DIR.mkdir(exist_ok=True)

def append_log(role, content):
    with CHAT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": int(time.time()), "role": role, "content": content}, ensure_ascii=False) + "\n")

def build_prompt(text):
    return f"Jesteś Jarvisem. Odpowiadaj po polsku.\nUżytkownik: {text}\nJarvis:"
