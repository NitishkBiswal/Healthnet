"""Single authoritative repository per patient.

Revision ID: 0007_single_repository_custody
Revises: 0006_segment14
"""

from alembic import op


revision = "0007_single_repository_custody"
down_revision = "0006_segment14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_record_locator_one_active_per_patient",
        "record_locator",
        ["health_id"],
        unique=True,
        schema="healthnet",
        postgresql_where=op.f("status") == "ACTIVE",
    )


def downgrade() -> None:
    op.drop_index(
        "uq_record_locator_one_active_per_patient",
        table_name="record_locator",
        schema="healthnet",
    )
