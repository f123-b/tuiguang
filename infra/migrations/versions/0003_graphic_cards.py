"""Add optional graphic documents without rewriting existing content."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("content_packages", sa.Column("graphics", sa.JSON(), nullable=True))
    op.add_column("content_packages", sa.Column("graphics_render", sa.JSON(), nullable=True))


def downgrade():
    raise RuntimeError("Retain additive columns on application rollback; use a verified backup for full recovery.")
