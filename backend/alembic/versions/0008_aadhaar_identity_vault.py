"""Store optional Aadhaar as encrypted patient identity data."""

from alembic import op
import sqlalchemy as sa

revision = "0008_aadhaar_identity_vault"
down_revision = "0007_single_repository_custody"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patient_identity",
        sa.Column("aadhaar_encrypted", sa.Text(), nullable=True),
        schema="healthnet",
    )
    op.add_column(
        "patient_identity",
        sa.Column("aadhaar_last4", sa.String(length=4), nullable=True),
        schema="healthnet",
    )


def downgrade() -> None:
    op.drop_column("patient_identity", "aadhaar_last4", schema="healthnet")
    op.drop_column("patient_identity", "aadhaar_encrypted", schema="healthnet")
