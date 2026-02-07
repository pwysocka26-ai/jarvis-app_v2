import os
from alembic.config import Config
from alembic import command

def test_alembic_upgrade_downgrade_cycle(tmp_path, monkeypatch):
    # Use a temporary sqlite DB for migration testing
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    cfg = Config("alembic.ini")
    # Run to head
    command.upgrade(cfg, "head")
    # Downgrade all the way to base
    command.downgrade(cfg, "base")
    # Upgrade again (should succeed)
    command.upgrade(cfg, "head")
