"""Persistent offline voice and video production jobs."""

from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "narration_jobs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("video_id", sa.String(32), sa.ForeignKey("video_projects.id"), nullable=False),
        sa.Column("base_revision", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.String(32), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("source", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("stage", sa.String(40), nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("receipt", sa.JSON(), nullable=False),
        sa.Column("lease_until", sa.String(40), nullable=True),
        sa.Column("trace_id", sa.String(32), nullable=False),
        sa.UniqueConstraint("workspace_id", "idempotency_key"),
    )


def downgrade():
    raise RuntimeError("Keep production history; restore a verified pre-0014 backup for rollback.")
