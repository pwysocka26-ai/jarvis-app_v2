from __future__ import annotations

"""Tiny file index for Jarvis PRO mode.

Stores a lightweight index of files under a chosen root in a local sqlite DB.
Used by /scan and helpers in PRO mode.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Dict, Any
import os
import sqlite3
import time

from .filesystem import FsPolicy, safe_resolve, allowed_text_extension


DB_DEFAULT_REL = ".jarvis/jarvis_index.sqlite"


@dataclass
class BuildResult:
    root: str
    files: int
    dirs: int


def open_db(db_path: str | Path | None = None) -> Path:
    """Return absolute path to sqlite DB (create parent dirs if needed)."""
    if db_path is None:
        # keep DB next to project (cwd) by default
        db_path = Path(os.getenv("JARVIS_INDEX_DB", DB_DEFAULT_REL))
    p = Path(db_path)
    if not p.is_absolute():
        p = (Path(os.getcwd()) / p).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS files(
            path TEXT PRIMARY KEY,
            ext TEXT,
            size INTEGER,
            mtime REAL,
            indexed_at REAL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_files_ext ON files(ext)")
    return conn


def build_index(path: str | Path, *, policy: FsPolicy, db: Path | str | None = None) -> BuildResult:
    """Scan path (file or folder) and store index in db."""
    dbp = open_db(db)
    root = safe_resolve(policy, path)
    files = 0
    dirs = 0
    now = time.time()

    conn = _connect(dbp)
    try:
        if root.is_file():
            dirs = 0
            files = 1
            _upsert(conn, root, now)
        else:
            for dp, dnames, fnames in os.walk(root):
                dirs += 1
                for fn in fnames:
                    fp = Path(dp) / fn
                    try:
                        _upsert(conn, fp, now)
                        files += 1
                    except Exception:
                        # ignore unreadable paths
                        continue
        conn.commit()
    finally:
        conn.close()

    return BuildResult(root=str(root), files=files, dirs=dirs)


def _upsert(conn: sqlite3.Connection, fp: Path, indexed_at: float) -> None:
    try:
        st = fp.stat()
    except Exception:
        return
    ext = fp.suffix.lower()
    conn.execute(
        """INSERT INTO files(path, ext, size, mtime, indexed_at)
           VALUES(?,?,?,?,?)
           ON CONFLICT(path) DO UPDATE SET
             ext=excluded.ext,
             size=excluded.size,
             mtime=excluded.mtime,
             indexed_at=excluded.indexed_at
        """,
        (str(fp), ext, int(st.st_size), float(st.st_mtime), float(indexed_at)),
    )


def list_index(db: Path | str | None = None, *, limit: int = 100) -> List[Dict[str, Any]]:
    dbp = open_db(db)
    conn = _connect(dbp)
    try:
        cur = conn.execute(
            "SELECT path, ext, size, mtime, indexed_at FROM files ORDER BY indexed_at DESC LIMIT ?",
            (int(limit),),
        )
        rows = [
            {"path": r[0], "ext": r[1], "size": r[2], "mtime": r[3], "indexed_at": r[4]}
            for r in cur.fetchall()
        ]
        return rows
    finally:
        conn.close()


def summarize_index(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    by_ext: Dict[str, int] = {}
    for r in rows:
        by_ext[r.get("ext") or ""] = by_ext.get(r.get("ext") or "", 0) + 1
    top_ext = sorted(by_ext.items(), key=lambda x: x[1], reverse=True)[:8]
    return {"total_files": total, "top_ext": top_ext}
