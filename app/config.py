from __future__ import annotations

"""App configuration.

The codebase started on Pydantic v1, where `BaseSettings` lived in `pydantic`.
In Pydantic v2 it moved to the `pydantic-settings` package.

To prevent runtime crashes ("BaseSettings has been moved"), we support both.
"""

import os
from functools import lru_cache

from pydantic import Field

try:
    # Pydantic v2
    from pydantic_settings import BaseSettings
except Exception:  # pragma: no cover
    # Pydantic v1
    from pydantic import BaseSettings

class Settings(BaseSettings):
    # API auth (very simple dev auth)
    # Accept both env names (we've been using both in PowerShell):
    # - API_TOKEN (legacy)
    # - JARVIS_API_TOKEN (preferred)
    api_token: str = Field(
        default_factory=lambda: (
            os.getenv("JARVIS_API_TOKEN")
            or os.getenv("API_TOKEN")
            or "dev-token"
        )
    )

    # NOTE:
    # Pydantic v2 deprecates passing extra kwargs like `env=` to Field().
    # To keep the code warning-free without changing business logic,
    # we read environment variables via default_factory.

    # Memory
    memory_path: str = Field(default_factory=lambda: os.getenv("MEMORY_PATH", "data/memory.json"))
    max_history: int = Field(default_factory=lambda: int(os.getenv("MAX_HISTORY", "50")))

    # Memory backend: "file" (JSON) or "db" (Postgres/SQLite via SQLAlchemy)
    memory_backend: str = Field(default_factory=lambda: os.getenv("MEMORY_BACKEND", "file"))

    # Database (used only when MEMORY_BACKEND=db)
    # Default: local SQLite file inside the project (works offline)
    database_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./data/jarvis.db"))

    # Redis (optional cache)
    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))

    # Ollama
    ollama_base_url: str = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    ollama_model: str = Field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3"))
    # Local models can be slow on first token (model load / warmup),
    # so keep a conservative default.
    ollama_timeout_s: float = Field(default_factory=lambda: float(os.getenv("OLLAMA_TIMEOUT_S", "180.0")))

    # Behavior
    use_ollama: bool = Field(default_factory=lambda: os.getenv("USE_OLLAMA", "true").strip().lower() in {"1","true","t","yes","y","on"})

    # PRO (local filesystem tooling)
    # IMPORTANT: In cloud deployments, keep allow_write=False and set a strict root.
    pro_fs_root: str = Field(default_factory=lambda: os.getenv("JARVIS_FS_ROOT", "."))
    pro_allow_write: bool = Field(default_factory=lambda: os.getenv("JARVIS_FS_ALLOW_WRITE", "false").strip().lower() in {"1","true","t","yes","y","on"})
    pro_index_db: str = Field(default_factory=lambda: os.getenv("JARVIS_PRO_INDEX_DB", "data/pro_index.sqlite"))

    # Persona / product mode
    # Default is B2C-friendly. PRO can be toggled locally for testing.
    persona: str = Field(default_factory=lambda: os.getenv("JARVIS_PERSONA", "b2c"))  # "b2c" | "pro"
    pro_enabled: bool = Field(default_factory=lambda: os.getenv("JARVIS_PRO_ENABLED", "false").strip().lower() in {"1","true","t","yes","y","on"})

    # UX knobs
    emoji: bool = Field(default_factory=lambda: os.getenv("JARVIS_EMOJI", "true").strip().lower() in {"1","true","t","yes","y","on"})
    max_reply_sentences: int = Field(default_factory=lambda: int(os.getenv("JARVIS_MAX_SENTENCES", "6")))


@lru_cache
def get_settings() -> "Settings":
    """Singleton settings object (safe for DI in tests)."""
    return Settings()

settings = get_settings()