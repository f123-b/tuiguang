"""Auditable feedback, reports and approved strategy pointers."""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def common():
    return [
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.String(40), nullable=False),
    ]


def upgrade():
    op.add_column("creator_profiles", sa.Column("active_strategy_id", sa.String(32), nullable=True))
    op.add_column("editorial_entries", sa.Column("strategy_snapshot", sa.JSON(), nullable=True))
    op.add_column(
        "metric_snapshots", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true())
    )
    op.create_table(
        "feedback_notes",
        *common(),
        sa.Column("content_id", sa.String(32), sa.ForeignKey("content_packages.id"), nullable=False),
        sa.Column("content_revision", sa.Integer(), nullable=False),
        sa.Column("reason_tag", sa.String(40), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("recorded_by", sa.String(32), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "learning_reports",
        *common(),
        sa.Column("creator_id", sa.String(32), sa.ForeignKey("creator_profiles.id"), nullable=False),
        sa.Column("period_start", sa.String(10), nullable=False),
        sa.Column("period_end", sa.String(10), nullable=False),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.UniqueConstraint("creator_id", "period_start", "period_end", "source_digest"),
    )
    op.create_table(
        "strategy_versions",
        *common(),
        sa.Column("creator_id", sa.String(32), sa.ForeignKey("creator_profiles.id"), nullable=False),
        sa.Column(
            "report_id", sa.String(32), sa.ForeignKey("learning_reports.id"), nullable=False, unique=True
        ),
        sa.Column("parent_id", sa.String(32), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("decided_by", sa.String(32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.String(40), nullable=True),
    )


def downgrade():
    raise RuntimeError("Keep additive learning records; restore a verified backup for full rollback.")
