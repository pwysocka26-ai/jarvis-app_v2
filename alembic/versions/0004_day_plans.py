"""day plans and reminders

Revision ID: 0004_day_plans
Revises: 0003_memory_tables
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_day_plans"
down_revision = "0003_memory_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "day_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="b2c"),
        sa.Column("summary", sa.Text(), nullable=True),
        # NOTE: use a DB-agnostic timestamp default. SQLite does not support `now()`.
        # `CURRENT_TIMESTAMP` works in SQLite and Postgres.
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_day_plans_user_id", "day_plans", ["user_id"])
    op.create_index("ix_day_plans_day", "day_plans", ["day"])

    op.create_table(
        "plan_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("day_plan_id", sa.Integer(), sa.ForeignKey("day_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False, server_default="chore"),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("location", sa.String(length=300), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_plan_items_day_plan_id", "plan_items", ["day_plan_id"])
    op.create_index("ix_plan_items_start_time", "plan_items", ["start_time"])

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("plan_item_id", sa.Integer(), sa.ForeignKey("plan_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("remind_at", sa.DateTime(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_reminders_plan_item_id", "reminders", ["plan_item_id"])
    op.create_index("ix_reminders_remind_at", "reminders", ["remind_at"])


def downgrade() -> None:
    op.drop_index("ix_reminders_remind_at", table_name="reminders")
    op.drop_index("ix_reminders_plan_item_id", table_name="reminders")
    op.drop_table("reminders")

    op.drop_index("ix_plan_items_start_time", table_name="plan_items")
    op.drop_index("ix_plan_items_day_plan_id", table_name="plan_items")
    op.drop_table("plan_items")

    op.drop_index("ix_day_plans_day", table_name="day_plans")
    op.drop_index("ix_day_plans_user_id", table_name="day_plans")
    op.drop_table("day_plans")
