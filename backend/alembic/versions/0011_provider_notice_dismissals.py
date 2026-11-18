"""Persist doctor-specific dismissal of revoked-consent notices."""

from alembic import op
import sqlalchemy as sa

revision = "0011_provider_notice_dismissals"
down_revision = "0010_patient_repo_transfer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_notice_dismissal",
        sa.Column("consent_id", sa.Uuid(), nullable=False),
        sa.Column("provider_subject", sa.String(length=128), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("consent_id", "provider_subject"),
        schema="healthnet",
    )


def downgrade() -> None:
    op.drop_table("provider_notice_dismissal", schema="healthnet")
