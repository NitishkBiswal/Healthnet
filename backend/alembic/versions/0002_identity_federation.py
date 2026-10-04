"""identity federation tables

Revision ID: 0002_identity_federation
Revises: a0b1c2d3e4f5
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_identity_federation"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE healthnet.health_id_sequence START WITH 1")
    op.create_table(
        "patient_identity",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_health_id", sa.String(32), nullable=False),
        sa.Column("issuing_jurisdiction", sa.String(32), nullable=False),
        sa.Column("given_name", sa.String(100), nullable=False),
        sa.Column("family_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("sex", sa.String(32)),
        sa.Column("phone", sa.String(32)),
        sa.Column("email", sa.String(320)),
        sa.Column("address", sa.Text()),
        sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"),
        sa.Column("superseded_by", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["superseded_by"], ["healthnet.patient_identity.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="healthnet",
    )
    op.create_index("ix_patient_identity_health_id", "patient_identity", ["display_health_id"], unique=True, schema="healthnet")
    op.create_index("ix_patient_identity_jurisdiction", "patient_identity", ["issuing_jurisdiction"], schema="healthnet")

    op.create_table(
        "patient_identifier",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("identifier_type", sa.String(64), nullable=False),
        sa.Column("identifier_value", sa.String(256), nullable=False),
        sa.Column("issuing_authority", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["healthnet.patient_identity.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="healthnet",
    )
    op.create_index("ix_patient_identifier_patient_id", "patient_identifier", ["patient_id"], schema="healthnet")

    op.create_table(
        "patient_location_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("jurisdiction", sa.String(32), nullable=False),
        sa.Column("movement_type", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["healthnet.patient_identity.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="healthnet",
    )
    op.create_index("ix_patient_location_history_patient_id", "patient_location_history", ["patient_id"], schema="healthnet")

    op.create_table(
        "duplicate_review",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_patient_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_given_name", sa.String(100), nullable=False),
        sa.Column("proposed_family_name", sa.String(100), nullable=False),
        sa.Column("proposed_date_of_birth", sa.Date(), nullable=False),
        sa.Column("proposed_sex", sa.String(32)),
        sa.Column("proposed_phone", sa.String(32)),
        sa.Column("proposed_email", sa.String(320)),
        sa.Column("proposed_issuing_jurisdiction", sa.String(32), nullable=False),
        sa.Column("proposed_identifiers", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("reviewer_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["candidate_patient_id"], ["healthnet.patient_identity.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="healthnet",
    )
    op.create_index("ix_duplicate_review_candidate_patient_id", "duplicate_review", ["candidate_patient_id"], schema="healthnet")
    op.create_index("ix_duplicate_review_status", "duplicate_review", ["status"], schema="healthnet")


def downgrade() -> None:
    op.drop_table("duplicate_review", schema="healthnet")
    op.drop_table("patient_location_history", schema="healthnet")
    op.drop_table("patient_identifier", schema="healthnet")
    op.drop_index("ix_patient_identity_jurisdiction", table_name="patient_identity", schema="healthnet")
    op.drop_index("ix_patient_identity_health_id", table_name="patient_identity", schema="healthnet")
    op.drop_table("patient_identity", schema="healthnet")
    op.execute("DROP SEQUENCE healthnet.health_id_sequence")
