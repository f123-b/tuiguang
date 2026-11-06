"""Encrypted workspace model configuration and persistent in-app notifications."""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def common():
    return [
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("workspace_id", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.String(40), nullable=False),
    ]


def upgrade():
    op.create_table(
        "handoff_outcomes",
        *common(),
        sa.Column("package_id", sa.String(32), sa.ForeignKey("manual_publish_packages.id"), nullable=False),
        sa.Column("outcome", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("recorded_by", sa.String(32), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("package_id"),
    )
    op.create_table(
        "model_configs",
        *common(),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("model_id", sa.String(120), nullable=False),
        sa.Column("model_revision", sa.String(120), nullable=True),
        sa.Column("base_url", sa.String(1000), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=True),
        sa.Column("input_price", sa.Integer(), nullable=False),
        sa.Column("output_price", sa.Integer(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("price_source", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.UniqueConstraint("workspace_id"),
    )
    op.create_table(
        "user_preferences",
        *common(),
        sa.Column("notification_mode", sa.String(20), nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False),
        sa.Column("digest_hour", sa.Integer(), nullable=False),
        sa.UniqueConstraint("workspace_id"),
    )
    op.create_table(
        "notifications",
        *common(),
        sa.Column("dedupe_key", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("action_path", sa.String(300), nullable=False),
        sa.Column("read_at", sa.String(40), nullable=True),
        sa.UniqueConstraint("workspace_id", "dedupe_key"),
    )
    op.create_table(
        "publish_reminders",
        *common(),
        sa.Column("package_id", sa.String(32), sa.ForeignKey("manual_publish_packages.id"), nullable=False),
        sa.Column("due_at", sa.String(40), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.UniqueConstraint("package_id", "due_at"),
    )


def downgrade():
    raise RuntimeError(
        "Retain additive configuration and audit records; restore a verified backup for full rollback."
    )
