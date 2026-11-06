"""Private evidence and content revision history; additive only."""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def common():
    return [
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.String(40), nullable=False),
    ]


def upgrade():
    op.add_column("brand_assets", sa.Column("review_note", sa.Text(), nullable=True))
    op.add_column("content_packages", sa.Column("variants", sa.JSON(), nullable=True))
    op.create_table(
        "content_revisions",
        *common(),
        sa.Column("content_id", sa.String(32), sa.ForeignKey("content_packages.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("editor_id", sa.String(32), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason_tag", sa.String(40), nullable=False),
        sa.UniqueConstraint("content_id", "revision"),
    )
    op.create_table(
        "brand_changes",
        *common(),
        sa.Column("brand_id", sa.String(32), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("product_version", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("reviewed_by", sa.String(32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.String(40), nullable=True),
    )


def downgrade():
    raise RuntimeError("Retain additive schema; restore a verified backup for full rollback.")
