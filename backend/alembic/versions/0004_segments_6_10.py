"""segments 6-10 policy fhir longitudinal emergency audit provenance
Revision ID: 0004_segments_6_10
Revises: 0003_segments_2_5
"""
from alembic import op
import sqlalchemy as sa
revision="0004_segments_6_10"
down_revision="0003_segments_2_5"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("jurisdiction",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("code",sa.String(32),unique=True,nullable=False),sa.Column("name",sa.String(160),nullable=False),sa.Column("active",sa.Boolean(),server_default=sa.true(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),schema="healthnet")
    op.create_index("ix_jurisdiction_code","jurisdiction",["code"],schema="healthnet")
    op.create_table("policy_rule",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("jurisdiction_id",sa.Uuid(),nullable=False),sa.Column("name",sa.String(160),nullable=False),sa.Column("purpose",sa.String(128),nullable=False),sa.Column("scope",sa.String(128),nullable=False),sa.Column("effect",sa.String(16),server_default="ALLOW",nullable=False),sa.Column("description",sa.Text()),sa.Column("active",sa.Boolean(),server_default=sa.true(),nullable=False),schema="healthnet")
    op.create_index("ix_policy_rule_jurisdiction_id","policy_rule",["jurisdiction_id"],schema="healthnet")
    op.create_table("emergency_health_profile",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("health_id",sa.String(32),unique=True,nullable=False),sa.Column("blood_group",sa.String(8)),sa.Column("allergies",sa.Text(),server_default=""),sa.Column("medications",sa.Text(),server_default=""),sa.Column("conditions",sa.Text(),server_default=""),sa.Column("emergency_contacts",sa.Text(),server_default=""),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now()),schema="healthnet")
    op.create_index("ix_emergency_health_profile_health_id","emergency_health_profile",["health_id"],schema="healthnet")
    op.create_table("break_glass_event",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("health_id",sa.String(32),nullable=False),sa.Column("actor_id",sa.String(128),nullable=False),sa.Column("reason",sa.Text(),nullable=False),sa.Column("invoked_at",sa.DateTime(timezone=True),server_default=sa.func.now()),schema="healthnet")
    op.create_index("ix_break_glass_event_health_id","break_glass_event",["health_id"],schema="healthnet")
    op.create_table("audit_event",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("event_type",sa.String(32),nullable=False),sa.Column("health_id",sa.String(32)),sa.Column("actor_id",sa.String(128),nullable=False),sa.Column("action",sa.String(160),nullable=False),sa.Column("payload",sa.Text(),server_default="{}"),sa.Column("prev_event_hash",sa.String(64)),sa.Column("event_hash",sa.String(64),unique=True,nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),schema="healthnet")
    op.create_index("ix_audit_event_health_id","audit_event",["health_id"],schema="healthnet")
    op.create_table("record_provenance",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("health_id",sa.String(32),nullable=False),sa.Column("repository_id",sa.Uuid()),sa.Column("resource_type",sa.String(64),nullable=False),sa.Column("resource_id",sa.String(128),nullable=False),sa.Column("source_system",sa.String(256),nullable=False),sa.Column("actor_id",sa.String(128),nullable=False),sa.Column("action",sa.String(64),nullable=False),sa.Column("details",sa.Text(),server_default="{}"),sa.Column("recorded_at",sa.DateTime(timezone=True),server_default=sa.func.now()),schema="healthnet")
    op.create_index("ix_record_provenance_health_id","record_provenance",["health_id"],schema="healthnet")
    op.create_table("longitudinal_view_log",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("health_id",sa.String(32),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),schema="healthnet")
def downgrade():
    for t in ["longitudinal_view_log","record_provenance","audit_event","break_glass_event","emergency_health_profile","policy_rule","jurisdiction"]:
        op.drop_table(t,schema="healthnet")
