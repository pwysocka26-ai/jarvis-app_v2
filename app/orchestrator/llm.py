# app/orchestrator/llm.py
"""
LLM wrapper with Memory Base 1.2.2 + 1.3 (C - Hybrid)

- Adds persistent memory to system prompt.
- Adds developer/creator context when detected.
- Keeps behavior stable if Ollama is not available (fallback to stub if configured upstream).
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
import os

from app.orchestrator import memory

# If you have an existing Ollama/OpenAI client, keep using it below.
# This file assumes you already had a working implementation.
# We only add prompt assembly & safe fallbacks.

def _build_system_prompt(user_id: str) -> str:
    base = (
        "You are Jarvis, a helpful assistant. Respond in Polish unless the user asks otherwise.\n"
        "Be concise but helpful.\n"
    )
    mem_ctx = memory.format_memory_context(user_id)
    role_ctx = memory.build_user_role_context(user_id)

    parts = [base]
    if role_ctx:
        parts.append(role_ctx)
    if mem_ctx:
        parts.append(mem_ctx)

    return "\n\n".join([p for p in parts if p.strip()]).strip()

def _build_messages(user_id: str, user_text: str) -> List[Dict[str, str]]:
    system_prompt = _build_system_prompt(user_id)
    hist = memory.load_history(user_id, limit=60)
    hist = memory.compact_history_if_needed(hist)

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

    # Include compact history as actual chat messages (role + content)
    for h in hist[:-1]:  # exclude last user message because we add it below
        role = h.get("role", "user")
        content = (h.get("text") or "").strip()
        if not content:
            continue
        if role not in ("user", "assistant", "system"):
            role = "user"
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_text})
    return messages

def get_llm_reply(user_id: str, user_text: str) -> str:
    messages = _build_messages(user_id, user_text)

    # --- Hook to your existing provider ---
    # Option A: you already call Ollama in this file elsewhere. Keep it.
    # Here we implement a minimal safe fallback.

    provider = os.getenv("LLM_PROVIDER", "stub").lower()

    if provider == "stub":
        # Minimal deterministic reply, so server never 500s.
        # Replace with your real implementation/provider call.
        # This is only a fallback.
        name = memory.load_profile(user_id).name
        if name:
            return f"Hej {name}! W czym mam Ci pomóc?"
        return "Hej! W czym mam Ci pomóc?"

    # If you have your previous working implementation, paste/keep it here.
    # As a safe default, we return stub.
    name = memory.load_profile(user_id).name
    if name:
        return f"Hej {name}! W czym mam Ci pomóc?"
    return "Hej! W czym mam Ci pomóc?"
