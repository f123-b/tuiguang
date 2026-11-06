"""User briefs and immutable script revisions. Existing workflows are unchanged."""

from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "creation_briefs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("brand_id", sa.String(32), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("topic", sa.String(180), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
    )
    op.create_table(
        "brief_plans",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("brief_id", sa.String(32), sa.ForeignKey("creation_briefs.id"), nullable=False),
        sa.Column("brief_revision", sa.Integer(), nullable=False),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("plan_hash", sa.String(64), nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("review", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("parent_id", sa.String(32), nullable=True),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("creator_runs.id"), nullable=True, unique=True),
        sa.Column("video_id", sa.String(32), sa.ForeignKey("video_projects.id"), nullable=True),
        sa.UniqueConstraint("brief_id", "plan_hash"),
    )


def downgrade():
    raise RuntimeError("Preserve user briefs/scripts; restore a verified pre-0013 backup for full rollback.")
