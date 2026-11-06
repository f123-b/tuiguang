"""Opt-in daily media configuration, without changing existing creator behavior."""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("creator_profiles", sa.Column("render_options", sa.JSON(), nullable=True))


def downgrade():
    raise RuntimeError(
        "Keep additive options and pause new workers; use a verified backup for full rollback."
    )
