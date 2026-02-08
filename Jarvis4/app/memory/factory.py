from __future__ import annotations

from app.config import settings
from app.memory.store import MemoryStore


def get_memory_store(user_id: str = "default"):
    """Return memory backend based on MEMORY_BACKEND.

    - file: JSON file in settings.memory_path
    - db: SQL (Postgres/SQLite) via SQLAlchemy
    """
    backend = (settings.memory_backend or "file").lower().strip()
    if backend == "db":
        # Import lazily so the app can start even when DB dependencies/config
        # aren't needed (e.g. MEMORY_BACKEND=file).
        from app.memory.db_store import DBMemoryStore  # noqa: WPS433

        return DBMemoryStore(user_id=user_id, max_history=settings.max_history, history_limit=settings.max_history)
    return MemoryStore(settings.memory_path, max_history=settings.max_history)
