from __future__ import annotations

import os
import requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:8010/v1/chat")

def main():
    print(f"Jarvis CLI. API: {API_URL}")
    print("Wyjdź: Ctrl+C lub /exit")
    while True:
        msg = input("Ty> ").strip()
        if not msg:
            continue
        if msg.lower() in ("/exit", "exit", "quit"):
            print("Jarvis> Pa!")
            break

        try:
            r = requests.post(API_URL, json={"message": msg}, timeout=60)
            r.raise_for_status()
            data = r.json()

            # FIX: czasem ktoś zmienia backend i zwraca string – zabezpieczenie
            if isinstance(data, str):
                print(f"Jarvis> {data}")
                continue

            reply = data.get("reply") or data.get("response") or ""
            if not isinstance(reply, str):
                reply = str(reply)
            print(f"Jarvis> {reply}")

        except requests.RequestException as e:
            print(f"[ERR] {e}")

if __name__ == "__main__":
    main()
