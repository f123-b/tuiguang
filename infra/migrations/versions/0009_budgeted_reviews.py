"""Optional metric versions, independent AI report tasks and user cost receipts."""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("metric_snapshots", sa.Column("content_revision", sa.Integer(), nullable=True))
    op.add_column("budget_ledgers", sa.Column("reconciliation", sa.JSON(), nullable=True))
    if op.get_bind().dialect.name == "sqlite":
        op.execute(
            "ALTER TABLE learning_reports ADD COLUMN ai_run_id VARCHAR(32) REFERENCES creator_runs(id)"
        )
    else:
        op.add_column(
            "learning_reports",
            sa.Column(
                "ai_run_id",
                sa.String(32),
                sa.ForeignKey("creator_runs.id", name="fk_learning_report_ai_run"),
                nullable=True,
            ),
        )
    op.create_index("uq_learning_reports_ai_run", "learning_reports", ["ai_run_id"], unique=True)


def downgrade():
    raise RuntimeError("Retain additive review receipts; use a verified backup for full recovery.")
