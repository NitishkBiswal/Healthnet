"""Add admin-reviewed provider jurisdiction transfers."""

from alembic import op
import sqlalchemy as sa

revision = "0012_provider_juris_xfer"
down_revision = "0011_provider_notice_dismissals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_jurisdiction_request",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("current_jurisdiction", sa.String(length=32), nullable=False),
        sa.Column("requested_jurisdiction", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reviewer_subject", sa.String(length=128), nullable=True),
        sa.Column("reviewer_note", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["provider_id"], ["healthnet.provider.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="healthnet",
    )
    op.create_index(
        "ix_healthnet_provider_jurisdiction_request_provider_id",
        "provider_jurisdiction_request", ["provider_id"], schema="healthnet",
    )
    op.create_index(
        "ix_healthnet_provider_jurisdiction_request_status",
        "provider_jurisdiction_request", ["status"], schema="healthnet",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_healthnet_provider_jurisdiction_request_status",
        table_name="provider_jurisdiction_request", schema="healthnet",
    )
    op.drop_index(
        "ix_healthnet_provider_jurisdiction_request_provider_id",
        table_name="provider_jurisdiction_request", schema="healthnet",
    )
    op.drop_table("provider_jurisdiction_request", schema="healthnet")
