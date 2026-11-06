"""Add recoverable video edits and content attachments."""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("content_packages", sa.Column("video_attachment", sa.JSON(), nullable=True))
    op.create_table(
        "video_revisions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("video_id", sa.String(32), sa.ForeignKey("video_projects.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("editor_id", sa.String(32), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("video_id", "revision"),
    )


def downgrade():
    raise RuntimeError("Keep additive history; restore a verified backup for full rollback.")
