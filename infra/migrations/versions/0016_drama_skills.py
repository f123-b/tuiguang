"""Private story plans and immutable production bindings."""

from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "drama_projects",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("brand_id", sa.String(32), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("confirmation", sa.JSON(), nullable=False),
        sa.Column("bindings", sa.JSON(), nullable=False),
        sa.Column("history", sa.JSON(), nullable=False),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("creator_runs.id"), nullable=True),
    )


def downgrade():
    raise RuntimeError("Preserve drama plans and receipts; use the verified pre-0016 backup.")
