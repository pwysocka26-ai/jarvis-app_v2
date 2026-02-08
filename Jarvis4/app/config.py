from __future__ import annotations

"""App configuration.

The codebase started on Pydantic v1, where `BaseSettings` lived in `pydantic`.
In Pydantic v2 it moved to the `pydantic-settings` package.

To prevent runtime crashes ("BaseSettings has been moved"), we support both.
"""

import os

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

    # Memory
    memory_path: str = Field("data/memory.json", env="MEMORY_PATH")
    max_history: int = Field(50, env="MAX_HISTORY")

    # Memory backend: "file" (JSON) or "db" (Postgres/SQLite via SQLAlchemy)
    memory_backend: str = Field("file", env="MEMORY_BACKEND")

    # Database (used only when MEMORY_BACKEND=db)
    # Default: local SQLite file inside the project (works offline)
    database_url: str = Field("sqlite:///./data/jarvis.db", env="DATABASE_URL")

    # Redis (optional cache)
    redis_url: str = Field("redis://127.0.0.1:6379/0", env="REDIS_URL")


    # Ollama
    ollama_base_url: str = Field("http://127.0.0.1:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field("llama3", env="OLLAMA_MODEL")
    # Local models can be slow on first token (model load / warmup),
    # so keep a conservative default.
    ollama_timeout_s: float = Field(180.0, env="OLLAMA_TIMEOUT_S")

    # Behavior
    use_ollama: bool = Field(True, env="USE_OLLAMA")

    # PRO (local filesystem tooling)
    # IMPORTANT: In cloud deployments, keep allow_write=False and set a strict root.
    pro_fs_root: str = Field(".", env="JARVIS_FS_ROOT")
    pro_allow_write: bool = Field(False, env="JARVIS_FS_ALLOW_WRITE")
    pro_index_db: str = Field("data/pro_index.sqlite", env="JARVIS_PRO_INDEX_DB")

    # Persona / product mode
    # Default is B2C-friendly. PRO can be toggled locally for testing.
    persona: str = Field("b2c", env="JARVIS_PERSONA")  # "b2c" | "pro"
    pro_enabled: bool = Field(False, env="JARVIS_PRO_ENABLED")

    # UX knobs
    emoji: bool = Field(True, env="JARVIS_EMOJI")
    max_reply_sentences: int = Field(6, env="JARVIS_MAX_SENTENCES")

settings = Settings()
