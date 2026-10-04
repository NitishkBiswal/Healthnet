"""segments 11-12 trust ledger and EHR migration

Revision ID: 0005_segments_11_12
Revises: 0004_segments_6_10
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_segments_11_12"
down_revision = "0004_segments_6_10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "trust_ledger_entry",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("transaction_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("opaque_subject_reference", sa.String(256), nullable=False),
        sa.Column("source_repository_id", sa.Uuid(), nullable=True),
        sa.Column("destination_repository_id", sa.Uuid(), nullable=True),
        sa.Column("authorization_reference", sa.String(256), nullable=False),
        sa.Column("package_hash", sa.String(128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("audit_reference", sa.String(256), nullable=True),
        sa.Column("previous_entry_hash", sa.String(64), nullable=True),
        sa.Column("entry_hash", sa.String(64), nullable=False, unique=True),
        schema="healthnet",
    )
    for name, column in [
        ("ix_trust_ledger_entry_transaction_id", "transaction_id"),
        ("ix_trust_ledger_entry_event_type", "event_type"),
        ("ix_trust_ledger_entry_opaque_subject_reference", "opaque_subject_reference"),
        ("ix_trust_ledger_entry_timestamp", "timestamp"),
        ("ix_trust_ledger_entry_status", "status"),
        ("ix_trust_ledger_entry_entry_hash", "entry_hash"),
    ]:
        op.create_index(name, "trust_ledger_entry", [column], schema="healthnet")

    op.create_table(
        "transfer_request",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("health_id", sa.String(32), nullable=False),
        sa.Column("source_repository_id", sa.Uuid(), nullable=False),
        sa.Column("destination_repository_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.String(128), nullable=False),
        sa.Column("purpose", sa.String(128), nullable=False),
        sa.Column("scope", sa.String(128), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("authorization_reference", sa.String(256)),
        sa.Column("package_hash", sa.String(128)),
        sa.Column("error_message", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["source_repository_id"], ["healthnet.repository.id"]),
        sa.ForeignKeyConstraint(["destination_repository_id"], ["healthnet.repository.id"]),
        schema="healthnet",
    )
    op.create_index("ix_transfer_request_health_id", "transfer_request", ["health_id"], schema="healthnet")
    op.create_index("ix_transfer_request_state", "transfer_request", ["state"], schema="healthnet")

    op.create_table(
        "transfer_authorization_token",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("transfer_request_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("issued_by", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["transfer_request_id"], ["healthnet.transfer_request.id"]),
        schema="healthnet",
    )
    op.create_index("ix_transfer_authorization_token_transfer_request_id", "transfer_authorization_token", ["transfer_request_id"], schema="healthnet")
    op.create_index("ix_transfer_authorization_token_active", "transfer_authorization_token", ["active"], schema="healthnet")

    op.create_table(
        "transfer_manifest",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("transfer_request_id", sa.Uuid(), nullable=False),
        sa.Column("resource_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manifest_hash", sa.String(64), nullable=False),
        sa.Column("package_hash", sa.String(128), nullable=False),
        sa.Column("validation_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["transfer_request_id"], ["healthnet.transfer_request.id"]),
        schema="healthnet",
    )
    op.create_index("ix_transfer_manifest_transfer_request_id", "transfer_manifest", ["transfer_request_id"], schema="healthnet")


def downgrade():
    for table in ["transfer_manifest", "transfer_authorization_token", "transfer_request", "trust_ledger_entry"]:
        op.drop_table(table, schema="healthnet")
