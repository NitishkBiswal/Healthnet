"""Segment 14 security hardening fields.

Revision ID: 0006_segment_14_security_hardening
Revises: 0005_segments_11_12
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_segment_14_security_hardening"
down_revision = "0005_segments_11_12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patient_identity",
        sa.Column("owner_subject", sa.String(length=128), nullable=True),
        schema="healthnet",
    )
    op.create_index(
        "ix_patient_identity_owner_subject",
        "patient_identity",
        ["owner_subject"],
        unique=True,
        schema="healthnet",
    )
    op.add_column(
        "duplicate_review",
        sa.Column("requesting_subject", sa.String(length=128), nullable=True),
        schema="healthnet",
    )
    op.create_index(
        "ix_duplicate_review_requesting_subject",
        "duplicate_review",
        ["requesting_subject"],
        unique=False,
        schema="healthnet",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_duplicate_review_requesting_subject",
        table_name="duplicate_review",
        schema="healthnet",
    )
    op.drop_column("duplicate_review", "requesting_subject", schema="healthnet")
    op.drop_index(
        "ix_patient_identity_owner_subject",
        table_name="patient_identity",
        schema="healthnet",
    )
    op.drop_column("patient_identity", "owner_subject", schema="healthnet")
