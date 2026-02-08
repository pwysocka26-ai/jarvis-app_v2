import os
import json
import requests
from typing import List, Dict, Optional

Message = Dict[str, str]


def _env(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    return v if v is not None else ""


def _safe_str(x) -> str:
    if isinstance(x, str):
        return x
    return str(x)


def _history_to_prompt(history: List[Message]) -> str:
    # Proste i stabilne: trzymamy się krótkiej historii, żeby nie zapychać kontekstu.
    lines: List[str] = []
    for m in history[-20:]:
        role = _safe_str(m.get("role", "user")).upper()
        content = _safe_str(m.get("content", ""))
        lines.append(f"{role}: {content}")
    lines.append("ASSISTANT:")
    return "\n".join(lines)


def ask_llm(history: List[Message]) -> str:
    """
    Stabilny router providerów LLM.
    Zasada: NIGDY nie wywalaj serwera – zawsze fallback do stub.
    """
    provider = _env("LLM_PROVIDER", "ollama").lower().strip()

    try:
        if provider == "ollama":
            return _ask_ollama(history)
        if provider == "openai":
            return _ask_openai(history)

        return _ask_stub(history)

    except Exception as e:
        return f"(fallback:stub) Wystąpił błąd LLM: {type(e).__name__}: {e}"


def _ask_stub(history: List[Message]) -> str:
    last = history[-1].get("content", "") if history else ""
    return f"Jarvis (stub): dostałem: {last}"


def _ask_ollama(history: List[Message]) -> str:
    base = _env("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    model = _env("OLLAMA_MODEL", "llama3.1:8b").strip() or "llama3.1:8b"
    timeout_s = float(_env("LLM_TIMEOUT", "20"))

    prompt = _history_to_prompt(history)

    url = f"{base}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    r = requests.post(url, json=payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()

    resp = data.get("response")
    if not isinstance(resp, str) or not resp.strip():
        return "(fallback:stub) Ollama zwróciła pustą odpowiedź."
    return resp.strip()


def _ask_openai(history: List[Message]) -> str:
    # Opcjonalnie – jeśli kiedyś zechcesz przełączyć na OpenAI przez ENV.
    api_key = _env("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "(fallback:stub) Brak OPENAI_API_KEY."

    model = _env("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    timeout_s = float(_env("LLM_TIMEOUT", "20"))

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    messages = history[-20:]
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.4,
    }

    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout_s)
    r.raise_for_status()
    data = r.json()

    try:
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, str) and content.strip():
            return content.strip()
        return "(fallback:stub) OpenAI zwróciło pustą odpowiedź."
    except Exception:
        return "(fallback:stub) OpenAI: nieoczekiwany format odpowiedzi."
