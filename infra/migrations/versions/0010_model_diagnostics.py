"""Explicit local gateway trust, compatibility switches and diagnostic receipts."""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "model_configs",
        sa.Column("endpoint_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "model_configs", sa.Column("json_mode", sa.Boolean(), nullable=False, server_default=sa.true())
    )
    op.add_column(
        "model_configs",
        sa.Column("token_parameter", sa.String(40), nullable=False, server_default="max_tokens"),
    )
    op.create_table(
        "model_checks",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("config_revision", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("creator_runs.id"), unique=True, nullable=True),
        sa.Column("result", sa.JSON(), nullable=False),
    )


def downgrade():
    raise RuntimeError("Preserve model diagnostic receipts; restore verified backup for full rollback.")
