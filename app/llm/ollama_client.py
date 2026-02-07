from __future__ import annotations

import json
import urllib.request
import urllib.error
import socket
import time
from typing import Any, Dict, List, Optional

class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_s: float = 60.0):
        self.base_url = (base_url or "").rstrip("/")
        self.model = model
        self.timeout_s = float(timeout_s)

    def ping(self) -> bool:
        # Ollama exposes GET /api/tags typically; simplest is to try open it.
        try:
            req = urllib.request.Request(self.base_url + "/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False

    def chat(self, messages: List[Dict[str, Any]]) -> str:
        url = self.base_url + "/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        # Local models may take a while on first request (model load / warm-up).
        # Add a couple of retries with small backoff to reduce flaky timeouts.
        last_exc: Optional[Exception] = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    raw = resp.read().decode("utf-8", errors="ignore")
                last_exc = None
                break
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                raise RuntimeError(f"Ollama HTTPError {e.code}: {body or e.reason}")
            except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
                last_exc = e
                # quick backoff then retry
                time.sleep(0.5 * (2 ** attempt))
            except Exception as e:
                last_exc = e
                time.sleep(0.5 * (2 ** attempt))

        if last_exc is not None:
            raise RuntimeError(
                "Ollama error: timed out or unreachable. "
                "Upewnij się, że Ollama działa oraz model jest pobrany. "
                f"(base_url={self.base_url!r}, model={self.model!r}, timeout_s={self.timeout_s}) "
                f"Original: {last_exc}"
            )

        try:
            obj = json.loads(raw)
        except Exception:
            return raw.strip()

        # Expected: {"message":{"role":"assistant","content":"..."}, ...}
        msg = obj.get("message") or {}
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        # fallback
        return str(obj).strip()
