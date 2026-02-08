"""0005 user day state

Revision ID: 0005_user_day_state
Revises: 0004_day_plans
Create Date: 2026-02-08 15:44:58

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_user_day_state"
down_revision = "0004_day_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_day_state",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=120), nullable=False, unique=True),
        sa.Column("state", sa.String(length=20), nullable=False, server_default="day"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_day_state_user_id", "user_day_state", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_day_state_user_id", table_name="user_day_state")
    op.drop_table("user_day_state")
