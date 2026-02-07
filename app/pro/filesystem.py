from __future__ import annotations

"""Filesystem helpers used by PRO mode.

This module is intentionally small and conservative: it only allows reading/writing
within a configured project root, and it keeps text operations safe by limiting
extensions and size.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Set
import os


# -----------------------------
# Policy / path safety
# -----------------------------

@dataclass(frozen=True)
class FsPolicy:
    """Rules for filesystem access.

    root: directory that acts as a sandbox for all operations.
    allow_read / allow_write / allow_delete: capability flags.
    """
    root: Path
    allow_read: bool = True
    allow_write: bool = False
    allow_delete: bool = False


def _normcase(p: str) -> str:
    # Windows paths are case-insensitive; normcase also normalizes slashes.
    return os.path.normcase(os.path.abspath(p))


def safe_resolve(root_or_policy: "FsPolicy | str | Path", user_path: str | Path) -> Path:
    """Resolve user_path inside root (or policy.root). Raises ValueError if outside."""
    root = root_or_policy.root if isinstance(root_or_policy, FsPolicy) else Path(root_or_policy)
    root = root.expanduser()
    up = Path(user_path).expanduser()

    if not up.is_absolute():
        up = root / up

    resolved = up.resolve()
    root_resolved = root.resolve()

    # Ensure resolved is within root_resolved (case-insensitive on Windows)
    if os.path.commonpath([_normcase(str(resolved)), _normcase(str(root_resolved))]) != _normcase(str(root_resolved)):
        raise ValueError(f"Path escapes root sandbox: {user_path}")

    return resolved


# -----------------------------
# Text file helpers
# -----------------------------

_ALLOWED_TEXT_EXT: Set[str] = {
    ".txt", ".md", ".markdown", ".log",
    ".json", ".yaml", ".yml",
    ".csv", ".tsv",
    ".py", ".js", ".ts", ".html", ".css",
    ".ini", ".cfg", ".toml",
}


def allowed_text_extension(path: str | Path) -> bool:
    return Path(path).suffix.lower() in _ALLOWED_TEXT_EXT


def read_text_file(policy: FsPolicy, rel_or_abs: str | Path, *, max_chars: int = 200_000) -> str:
    """Read a text file (UTF-8) within policy.root."""
    if not policy.allow_read:
        raise PermissionError("Reading files is disabled by policy")

    p = safe_resolve(policy, rel_or_abs)
    if not allowed_text_extension(p):
        raise PermissionError(f"Extension not allowed for text read: {p.suffix}")

    data = p.read_text(encoding="utf-8", errors="replace")
    if len(data) > max_chars:
        return data[:max_chars] + "\n...<truncated>..."
    return data


def write_text_file(policy: FsPolicy, rel_or_abs: str | Path, text: str, *, overwrite: bool = True) -> str:
    """Write UTF-8 text file within policy.root. Returns final path as string."""
    if not policy.allow_write:
        raise PermissionError("Writing files is disabled by policy")

    p = safe_resolve(policy, rel_or_abs)
    if not allowed_text_extension(p):
        raise PermissionError(f"Extension not allowed for text write: {p.suffix}")

    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists() and not overwrite:
        raise FileExistsError(f"File exists: {p}")
    p.write_text(text, encoding="utf-8")
    return str(p)


# -----------------------------
# Simple command parsing helpers
# -----------------------------

def extract_action_lines(text: str) -> list[str]:
    """Extract command-like lines from LLM output."""
    out: list[str] = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        # Accept bullet-like commands
        if s.startswith("-") or s.startswith("*") or s[:1].isdigit():
            out.append(s.lstrip("-*0123456789.). ").strip())
    return out
