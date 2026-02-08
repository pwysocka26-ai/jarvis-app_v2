from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error

API_URL = os.getenv("API_URL", "http://127.0.0.1:8010/v1/chat").strip()

def _clean_token(token: str | None) -> str:
    if not token:
        return ""
    t = token.strip()
    # handle accidental quotes pasted from PowerShell / docs
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()
    return t


# Accept both env names.
API_TOKEN = _clean_token(os.getenv("JARVIS_API_TOKEN") or os.getenv("API_TOKEN") or "dev-token")
CLI_TIMEOUT_S = float(os.getenv("CLI_TIMEOUT_S", "180"))

# Session mode (only choice the user has): b2c | pro
CURRENT_MODE = (os.getenv("JARVIS_MODE") or "b2c").strip().lower()
if CURRENT_MODE not in {"b2c", "pro"}:
    CURRENT_MODE = "b2c"


def _extract_text(raw: str) -> str:
    """Return a human-friendly response from API output.

    The server may return:
      - plain text
      - JSON with "reply"
      - JSON with "meta.response" (used by the intent router)
    """
    try:
        obj = json.loads(raw)
    except Exception:
        return raw

    # Common shape: {"reply": "..."}
    if isinstance(obj, dict):
        reply = obj.get("reply")
        if isinstance(reply, str) and reply.strip():
            return reply.strip()

        # Intent router shape: {"reply":"", "meta": {"response": "..."}}
        meta = obj.get("meta")
        if isinstance(meta, dict):
            meta_resp = meta.get("response")
            if isinstance(meta_resp, str) and meta_resp.strip():
                return meta_resp.strip()

    # Fallback: pretty-print JSON for debugging
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return raw

def _post(message: str) -> str:
    payload_obj = {"message": message, "mode": CURRENT_MODE}
    payload = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Token": API_TOKEN,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=CLI_TIMEOUT_S) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        return f"[ERR] {e.code}: {body or e.reason}"
    except Exception as e:
        return f"[ERR] {e}"

    return _extract_text(raw)

def main():
    global CURRENT_MODE
    print(f"Jarvis CLI. API: {API_URL}")
    print("Wyjdź: Ctrl+C lub /exit")
    print("Tryb: /mode b2c  |  /mode pro")
    print(f"Aktualny tryb: {CURRENT_MODE}")
    while True:
        try:
            msg = input("Ty> ").strip()
        except KeyboardInterrupt:
            print("\nJarvis> Pa!")
            return
        if not msg:
            continue
        low = msg.lower()
        if low in ("/exit","exit","quit"):
            print("Jarvis> Pa!")
            return
        if low.startswith("/mode"):
            parts = msg.split(maxsplit=1)
            if len(parts) < 2:
                print(f"Jarvis> Aktualny tryb: {CURRENT_MODE} (użyj: /mode b2c albo /mode pro)")
                continue
            new_mode = parts[1].strip().lower()
            if new_mode not in {"b2c", "pro"}:
                print("Jarvis> Nieznany tryb. Dostępne: b2c, pro")
                continue
            CURRENT_MODE = new_mode
            print(f"Jarvis> ✅ Ustawiono tryb: {CURRENT_MODE}")
            continue
        reply = _post(msg)
        print(f"Jarvis> {reply}")

if __name__ == "__main__":
    main()
