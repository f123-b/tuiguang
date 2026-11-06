"""Immutable quality evidence and preview-bound human decisions."""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "video_projects",
        sa.Column("preview_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("render_jobs", sa.Column("purpose", sa.String(20), nullable=False, server_default="final"))
    op.create_table(
        "quality_reports",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("subject_type", sa.String(20), nullable=False),
        sa.Column("subject_id", sa.String(32), nullable=False),
        sa.Column("subject_revision", sa.Integer(), nullable=False),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("ai_run_id", sa.String(32), sa.ForeignKey("creator_runs.id"), nullable=True, unique=True),
        sa.UniqueConstraint("workspace_id", "subject_type", "subject_id", "source_digest"),
    )
    op.create_table(
        "quality_reviews",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("video_id", sa.String(32), sa.ForeignKey("video_projects.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("preview_job_id", sa.String(32), sa.ForeignKey("render_jobs.id"), nullable=False),
        sa.Column("report_id", sa.String(32), sa.ForeignKey("quality_reports.id"), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("recorded_by", sa.String(32), sa.ForeignKey("users.id"), nullable=False),
    )


def downgrade():
    raise RuntimeError("Preserve quality decisions; restore the verified pre-0012 backup for rollback.")
