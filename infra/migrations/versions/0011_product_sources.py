"""Authorized product evidence snapshots and asset applicability."""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def base():
    return [
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.String(40), nullable=False),
    ]


def upgrade():
    op.create_table(
        "product_sources",
        *base(),
        sa.Column("brand_id", sa.String(32), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("recorded_by", sa.String(32), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("authorized", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("current_snapshot_id", sa.String(32), nullable=True),
        sa.Column("next_check_at", sa.String(40), nullable=True),
        sa.Column("last_checked_at", sa.String(40), nullable=True),
        sa.Column("last_error_code", sa.String(80), nullable=True),
        sa.Column("lease_until", sa.String(40), nullable=True),
    )
    op.create_table(
        "product_source_snapshots",
        *base(),
        sa.Column("source_id", sa.String(32), sa.ForeignKey("product_sources.id"), nullable=False),
        sa.Column("version", sa.String(100), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
    )
    op.create_table(
        "product_change_events",
        *base(),
        sa.Column("source_id", sa.String(32), sa.ForeignKey("product_sources.id"), nullable=False),
        sa.Column(
            "previous_snapshot_id",
            sa.String(32),
            sa.ForeignKey("product_source_snapshots.id"),
            nullable=False,
        ),
        sa.Column("snapshot_id", sa.String(32), sa.ForeignKey("product_source_snapshots.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("diff", sa.Text(), nullable=False),
        sa.Column("proposal_id", sa.String(32), sa.ForeignKey("brand_changes.id"), nullable=True),
    )
    op.create_table(
        "product_source_checks",
        *base(),
        sa.Column("source_id", sa.String(32), sa.ForeignKey("product_sources.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("trace_id", sa.String(32), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
    )
    if op.get_bind().dialect.name == "sqlite":
        op.execute(
            "ALTER TABLE brand_assets ADD COLUMN product_source_id VARCHAR(32) REFERENCES product_sources(id)"
        )
    else:
        op.add_column(
            "brand_assets",
            sa.Column(
                "product_source_id",
                sa.String(32),
                sa.ForeignKey("product_sources.id", name="fk_asset_product_source"),
                nullable=True,
            ),
        )
    op.add_column("brand_assets", sa.Column("product_version", sa.String(100), nullable=True))
    op.add_column(
        "brand_assets",
        sa.Column("applicability_status", sa.String(30), nullable=False, server_default="current"),
    )


def downgrade():
    raise RuntimeError("Preserve product source evidence; restore verified backup for full recovery.")
