"""Patient-initiated repository transfers with reason and auditor threshold review."""

from alembic import op
import sqlalchemy as sa

revision = "0010_patient_repository_transfers"
down_revision = "0009_profile_update_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transfer_request", sa.Column("reason", sa.Text(), nullable=False, server_default="Legacy transfer request"), schema="healthnet")
    op.add_column("transfer_request", sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.false()), schema="healthnet")
    op.add_column("transfer_request", sa.Column("review_status", sa.String(length=24), nullable=False, server_default="NOT_REQUIRED"), schema="healthnet")
    op.add_column("transfer_request", sa.Column("reviewed_by", sa.String(length=128), nullable=True), schema="healthnet")
    op.add_column("transfer_request", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True), schema="healthnet")
    op.add_column("transfer_request", sa.Column("reviewer_note", sa.Text(), nullable=True), schema="healthnet")


def downgrade() -> None:
    op.drop_column("transfer_request", "reviewer_note", schema="healthnet")
    op.drop_column("transfer_request", "reviewed_at", schema="healthnet")
    op.drop_column("transfer_request", "reviewed_by", schema="healthnet")
    op.drop_column("transfer_request", "review_status", schema="healthnet")
    op.drop_column("transfer_request", "review_required", schema="healthnet")
    op.drop_column("transfer_request", "reason", schema="healthnet")
