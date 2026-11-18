"""Identity tuning and time-limited emergency access.

Revision ID: 0008_identity_config_emergency_access
Revises: 0007_identity_resolution_and_jurisdictions
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_identity_config_emergency_access"
down_revision = "0007_identity_resolution_and_jurisdictions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_match_configuration",
        sa.Column("config_key", sa.String(32), primary_key=True),
        sa.Column("name_weight", sa.Float(), nullable=False),
        sa.Column("date_of_birth_weight", sa.Float(), nullable=False),
        sa.Column("sex_weight", sa.Float(), nullable=False),
        sa.Column("phone_weight", sa.Float(), nullable=False),
        sa.Column("email_weight", sa.Float(), nullable=False),
        sa.Column("medium_confidence", sa.Float(), nullable=False),
        sa.Column("high_confidence", sa.Float(), nullable=False),
        schema="healthnet",
    )
    op.execute(
        """
        INSERT INTO healthnet.identity_match_configuration
            (config_key, name_weight, date_of_birth_weight, sex_weight,
             phone_weight, email_weight, medium_confidence, high_confidence)
        VALUES ('default', 0.45, 0.30, 0.05, 0.10, 0.10, 0.70, 0.90)
        """
    )

    op.create_table(
        "break_glass_grant",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("healthnet.break_glass_event.id"),
            nullable=False,
        ),
        sa.Column("health_id", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="healthnet",
    )
    op.create_index(
        "ix_break_glass_grant_event_id",
        "break_glass_grant",
        ["event_id"],
        schema="healthnet",
    )
    op.create_index(
        "ix_break_glass_grant_health_id",
        "break_glass_grant",
        ["health_id"],
        schema="healthnet",
    )
    op.create_index(
        "ix_break_glass_grant_actor_id",
        "break_glass_grant",
        ["actor_id"],
        schema="healthnet",
    )
    op.create_index(
        "ix_break_glass_grant_expires_at",
        "break_glass_grant",
        ["expires_at"],
        schema="healthnet",
    )

    op.create_table(
        "patient_notification",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("patient_subject", sa.String(128), nullable=False),
        sa.Column("health_id", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("message", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        schema="healthnet",
    )
    op.create_index(
        "ix_patient_notification_patient_subject",
        "patient_notification",
        ["patient_subject"],
        schema="healthnet",
    )
    op.create_index(
        "ix_patient_notification_health_id",
        "patient_notification",
        ["health_id"],
        schema="healthnet",
    )


def downgrade() -> None:
    op.drop_table("patient_notification", schema="healthnet")
    op.drop_table("break_glass_grant", schema="healthnet")
    op.drop_table("identity_match_configuration", schema="healthnet")
