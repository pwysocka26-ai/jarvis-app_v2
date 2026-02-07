"""Ollama LLM adapter (stable baseline)

This module contains a single responsibility:
- send a prompt to Ollama /api/generate and return the response text.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import requests


# Default Ollama endpoint (local)
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3:latest")


class OllamaError(RuntimeError):
    pass


def ask_ollama(prompt: str, *, model: str | None = None, timeout_s: int = 120) -> str:
    """Send prompt to Ollama and return the generated text.

    Args:
        prompt: User prompt text.
        model: Optional model override. Default: env OLLAMA_MODEL or llama3:latest.
        timeout_s: Request timeout.

    Returns:
        Response text (field: 'response').

    Raises:
        OllamaError: for network / HTTP / JSON issues.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        return ""

    payload: Dict[str, Any] = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise OllamaError(f"Ollama request failed: {e}") from e

    if not isinstance(data, dict) or "response" not in data:
        raise OllamaError(f"Unexpected Ollama response: {data!r}")

    return str(data.get("response", ""))
