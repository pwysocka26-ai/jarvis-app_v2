"""
Jarvis Orchestrator - Compatibility Memory Layer (Base1)

Goal: provide a stable API surface for the rest of the codebase.
This module intentionally defines a broad set of functions/constants that
older/newer parts of the app may import, even if some features are no-ops.

Storage: SQLite (stdlib), default ./data/jarvis_memory.sqlite
Disable: set env JARVIS_MEMORY=0 (or "false")
"""

from __future__ import annotations

import os
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------
# Public constants (imported elsewhere)
# ---------------------------

def _env_flag(name: str, default: str = "1") -> bool:
    v = os.getenv(name, default).strip().lower()
    return v not in ("0", "false", "no", "off", "")

ENABLED: bool = _env_flag("JARVIS_MEMORY", "1")

DEFAULT_DB_PATH = os.path.join(os.getcwd(), "data", "jarvis_memory.sqlite")
DB_PATH: str = os.getenv("JARVIS_MEMORY_DB", DEFAULT_DB_PATH)

# How many recent turns we keep when formatting context
MAX_TURNS_CONTEXT = int(os.getenv("JARVIS_MEMORY_MAX_TURNS", "20"))
MAX_CHARS_CONTEXT = int(os.getenv("JARVIS_MEMORY_MAX_CHARS", "6000"))

# ---------------------------
# Internal helpers
# ---------------------------

def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _connect() -> sqlite3.Connection:
    _ensure_dir(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;

        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            ts INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_turns_user_ts ON turns(user_id, ts);

        CREATE TABLE IF NOT EXISTS kv (
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS profiles (
            user_id TEXT PRIMARY KEY,
            json TEXT NOT NULL,
            updated_ts INTEGER NOT NULL
        );
        """
    )
    conn.commit()

def _safe_json_load(s: str, default: Any) -> Any:
    try:
        return json.loads(s)
    except Exception:
        return default

def _now_ts() -> int:
    return int(time.time())

def _normalize_user_id(user_id: Optional[str]) -> str:
    return (user_id or "default").strip() or "default"

# ---------------------------
# Minimal public data structures (optional)
# ---------------------------

@dataclass
class MemoryTurn:
    role: str
    content: str
    ts: int

# ---------------------------
# Public API: persistence primitives
# ---------------------------

def get_db() -> sqlite3.Connection:
    """
    Some parts of the code may import get_db(). We return an initialized connection.
    """
    conn = _connect()
    _init_db(conn)
    return conn

def append_turn(user_id: str, role: str, content: str, ts: Optional[int] = None) -> None:
    """
    Persist one message turn.
    """
    if not ENABLED:
        return
    uid = _normalize_user_id(user_id)
    t = int(ts or _now_ts())
    conn = get_db()
    with conn:
        conn.execute(
            "INSERT INTO turns(user_id, ts, role, content) VALUES(?, ?, ?, ?)",
            (uid, t, role, content),
        )

def load_history(user_id: str, limit: int = 50) -> List[Dict[str, str]]:
    """
    Returns list of dicts: {"role": ..., "content": ...}
    """
    if not ENABLED:
        return []
    uid = _normalize_user_id(user_id)
    conn = get_db()
    cur = conn.execute(
        "SELECT role, content, ts FROM turns WHERE user_id=? ORDER BY ts DESC, id DESC LIMIT ?",
        (uid, int(limit)),
    )
    rows = cur.fetchall()
    rows.reverse()
    return [{"role": r["role"], "content": r["content"]} for r in rows]

def load_summary(user_id: str) -> str:
    """
    Optional summary string stored in kv as 'summary:<user_id>'.
    """
    if not ENABLED:
        return ""
    uid = _normalize_user_id(user_id)
    conn = get_db()
    cur = conn.execute("SELECT v FROM kv WHERE k=?", (f"summary:{uid}",))
    row = cur.fetchone()
    return row["v"] if row else ""

def save_summary(user_id: str, summary: str) -> None:
    if not ENABLED:
        return
    uid = _normalize_user_id(user_id)
    conn = get_db()
    with conn:
        conn.execute(
            "INSERT INTO kv(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (f"summary:{uid}", summary or ""),
        )

def compact_history_if_needed(user_id: str, max_turns: int = 500) -> None:
    """
    Simple compaction: keep last max_turns turns.
    (Real summarization can be added later.)
    """
    if not ENABLED:
        return
    uid = _normalize_user_id(user_id)
    conn = get_db()
    # delete older than the newest max_turns
    cur = conn.execute(
        "SELECT id FROM turns WHERE user_id=? ORDER BY ts DESC, id DESC LIMIT 1 OFFSET ?",
        (uid, int(max_turns)),
    )
    row = cur.fetchone()
    if not row:
        return
    cutoff_id = int(row["id"])
    with conn:
        conn.execute("DELETE FROM turns WHERE user_id=? AND id<?", (uid, cutoff_id))

# ---------------------------
# Public API: profile (structured memory)
# ---------------------------

def load_profile(user_id: str) -> Dict[str, Any]:
    if not ENABLED:
        return {}
    uid = _normalize_user_id(user_id)
    conn = get_db()
    cur = conn.execute("SELECT json FROM profiles WHERE user_id=?", (uid,))
    row = cur.fetchone()
    if not row:
        return {}
    return _safe_json_load(row["json"], {})

def save_profile(user_id: str, profile: Dict[str, Any]) -> None:
    if not ENABLED:
        return
    uid = _normalize_user_id(user_id)
    conn = get_db()
    payload = json.dumps(profile or {}, ensure_ascii=False)
    with conn:
        conn.execute(
            """
            INSERT INTO profiles(user_id, json, updated_ts)
            VALUES(?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET json=excluded.json, updated_ts=excluded.updated_ts
            """,
            (uid, payload, _now_ts()),
        )

_NAME_RE = re.compile(r"\b(mam na imię|nazywam się)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)", re.IGNORECASE)

def update_profile_from_text(user_id: str, text: str) -> Dict[str, Any]:
    """
    Very lightweight extractor. Can be replaced with LLM-based extractor later.
    Must exist because other modules import it.
    """
    if not ENABLED:
        return {}
    uid = _normalize_user_id(user_id)
    profile = load_profile(uid) or {}

    if not isinstance(text, str):
        text = str(text)

    m = _NAME_RE.search(text)
    if m:
        profile["name"] = m.group(2)

    # store a small set of user "facts" as list of strings
    facts = profile.get("facts")
    if not isinstance(facts, list):
        facts = []
    # add canonical fact: "User said: <...>" (shortened)
    snippet = text.strip().replace("\n", " ")
    if len(snippet) > 200:
        snippet = snippet[:200] + "…"
    fact = f"Użytkownik powiedział: {snippet}"
    if fact not in facts:
        facts.append(fact)
    # keep facts bounded
    facts = facts[-50:]
    profile["facts"] = facts

    save_profile(uid, profile)
    return profile

def build_system_facts(user_id: str) -> str:
    """
    Returns a short system string derived from profile & summary.
    Imported by some versions of the orchestrator.
    """
    if not ENABLED:
        return ""
    uid = _normalize_user_id(user_id)
    p = load_profile(uid) or {}
    parts: List[str] = []
    if "name" in p:
        parts.append(f"Imię użytkownika: {p['name']}.")
    facts = p.get("facts")
    if isinstance(facts, list) and facts:
        # last 5 facts
        parts.append("Ostatnie fakty o użytkowniku:")
        for f in facts[-5:]:
            parts.append(f"- {f}")
    s = load_summary(uid)
    if s:
        parts.append("Streszczenie rozmów:")
        parts.append(s)
    return "\n".join(parts).strip()

# ---------------------------
# Public API: context formatting
# ---------------------------

def format_memory_context(user_id: str, max_turns: int = MAX_TURNS_CONTEXT, max_chars: int = MAX_CHARS_CONTEXT) -> str:
    """
    Build a compact string for prompt injection/context.
    """
    if not ENABLED:
        return ""
    uid = _normalize_user_id(user_id)

    history = load_history(uid, limit=max_turns)
    summary = load_summary(uid)
    facts = build_system_facts(uid)

    chunks: List[str] = []
    if facts:
        chunks.append("[FACTS]\n" + facts)
    if summary:
        chunks.append("[SUMMARY]\n" + summary)

    if history:
        lines = []
        for t in history:
            role = t.get("role", "user")
            content = (t.get("content") or "").strip()
            lines.append(f"{role}: {content}")
        chunks.append("[HISTORY]\n" + "\n".join(lines))

    out = "\n\n".join([c for c in chunks if c]).strip()
    if len(out) > max_chars:
        out = out[-max_chars:]
    return out

# ---------------------------
# Backwards-compat shim names
# ---------------------------

def plan_from_text(*args: Any, **kwargs: Any) -> Any:
    """
    Placeholder for legacy imports; real implementation lives elsewhere.
    """
    raise NotImplementedError("plan_from_text is not part of memory.py")

def needs_approval_for(*args: Any, **kwargs: Any) -> Any:
    raise NotImplementedError("needs_approval_for is not part of memory.py")

# convenience aliases some branches used
def load_profile_from_text(user_id: str, text: str) -> Dict[str, Any]:
    return update_profile_from_text(user_id, text)

