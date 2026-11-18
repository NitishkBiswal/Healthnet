"""Support auditor review of possible duplicate patient profile edits."""

from alembic import op
import sqlalchemy as sa

revision = "0009_profile_update_review"
down_revision = "0008_aadhaar_identity_vault"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "duplicate_review",
        sa.Column("review_type", sa.String(length=32), nullable=False, server_default="DUPLICATE_REGISTRATION"),
        schema="healthnet",
    )
    op.add_column(
        "duplicate_review",
        sa.Column("target_patient_id", sa.Uuid(), nullable=True),
        schema="healthnet",
    )
    op.create_foreign_key(
        "fk_duplicate_review_target_patient",
        "duplicate_review",
        "patient_identity",
        ["target_patient_id"],
        ["id"],
        source_schema="healthnet",
        referent_schema="healthnet",
    )
    op.create_index(
        "ix_healthnet_duplicate_review_target_patient_id",
        "duplicate_review",
        ["target_patient_id"],
        unique=False,
        schema="healthnet",
    )
    op.add_column(
        "duplicate_review",
        sa.Column("proposed_address", sa.Text(), nullable=True),
        schema="healthnet",
    )


def downgrade() -> None:
    op.drop_column("duplicate_review", "proposed_address", schema="healthnet")
    op.drop_index("ix_healthnet_duplicate_review_target_patient_id", table_name="duplicate_review", schema="healthnet")
    op.drop_constraint("fk_duplicate_review_target_patient", "duplicate_review", schema="healthnet", type_="foreignkey")
    op.drop_column("duplicate_review", "target_patient_id", schema="healthnet")
    op.drop_column("duplicate_review", "review_type", schema="healthnet")
