"""Persist editorial plans and freeze run inputs; retain all v1 records."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "editorial_entries",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("creator_id", sa.String(32), sa.ForeignKey("creator_profiles.id"), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("angle", sa.String(40), nullable=False),
        sa.Column("fact_refs", sa.JSON(), nullable=False),
        sa.Column("brand_revision", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.UniqueConstraint("creator_id", "date"),
    )
    op.create_index("ix_editorial_entries_workspace_id", "editorial_entries", ["workspace_id"])
    # SQLite supports an additive nullable REFERENCES column, avoiding a table rebuild
    # while content/ledger rows already reference creator_runs.
    if op.get_bind().dialect.name == "sqlite":
        op.execute(
            "ALTER TABLE creator_runs ADD COLUMN editorial_entry_id VARCHAR(32) REFERENCES editorial_entries(id)"
        )
    else:
        op.add_column(
            "creator_runs",
            sa.Column(
                "editorial_entry_id",
                sa.String(32),
                sa.ForeignKey("editorial_entries.id", name="fk_run_editorial_entry"),
                nullable=True,
            ),
        )
    op.create_index("uq_creator_runs_editorial_entry", "creator_runs", ["editorial_entry_id"], unique=True)
    op.add_column("creator_runs", sa.Column("input_snapshot", sa.JSON(), nullable=True))
    op.add_column("budget_ledgers", sa.Column("billing_date", sa.String(10), nullable=True))
    op.execute("UPDATE budget_ledgers SET billing_date = operational_date WHERE billing_date IS NULL")


def downgrade():
    raise RuntimeError(
        "Keep additive 0002 schema when rolling back the application; restore a verified backup for full rollback."
    )
