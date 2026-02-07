from alembic import op
import sqlalchemy as sa

revision = "0002_audit_trace_ids"
down_revision = "0001_init"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("audit_events") as batch:
        batch.add_column(sa.Column("request_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("trace_id", sa.String(length=64), nullable=True))

def downgrade():
    with op.batch_alter_table("audit_events") as batch:
        batch.drop_column("trace_id")
        batch.drop_column("request_id")
