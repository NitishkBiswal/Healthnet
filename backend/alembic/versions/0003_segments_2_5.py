"""segments 2-5 repositories locator trust consent

Revision ID: 0003_segments_2_5
Revises: 0002_identity_federation
"""
from alembic import op
import sqlalchemy as sa

revision="0003_segments_2_5"
down_revision="0002_identity_federation"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("repository",
        sa.Column("id",sa.Uuid(),nullable=False), sa.Column("code",sa.String(64),nullable=False),
        sa.Column("name",sa.String(160),nullable=False), sa.Column("jurisdiction",sa.String(32),nullable=False),
        sa.Column("base_url",sa.String(512),nullable=False), sa.Column("status",sa.String(16),nullable=False,server_default="ONLINE"),
        sa.Column("description",sa.Text()), sa.Column("last_checked_at",sa.DateTime(timezone=True)),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("code"), schema="healthnet")
    op.create_index("ix_repository_code","repository",["code"],schema="healthnet")
    op.create_index("ix_repository_jurisdiction","repository",["jurisdiction"],schema="healthnet")
    op.create_index("ix_repository_status","repository",["status"],schema="healthnet")
    op.execute("""
        INSERT INTO healthnet.repository
            (id, code, name, jurisdiction, base_url, status, description)
        VALUES
            ('00000000-0000-0000-0000-000000000201', 'IN-OD', 'Odisha Health Repository', 'IN-OD', 'http://localhost:8091/fhir', 'ONLINE', 'Simulated jurisdictional repository for development'),
            ('00000000-0000-0000-0000-000000000202', 'IN-KA', 'Karnataka Health Repository', 'IN-KA', 'http://localhost:8092/fhir', 'ONLINE', 'Simulated jurisdictional repository for development'),
            ('00000000-0000-0000-0000-000000000203', 'MV', 'Maldives Health Repository', 'MV', 'http://localhost:8093/fhir', 'ONLINE', 'Simulated jurisdictional repository for development')
    """)

    op.create_table("ehr_custody",
        sa.Column("id",sa.Uuid(),nullable=False), sa.Column("health_id",sa.String(32),nullable=False),
        sa.Column("repository_id",sa.Uuid(),nullable=False), sa.Column("resource_types",sa.String(512),nullable=False),
        sa.Column("custody_start",sa.DateTime(timezone=True),nullable=False), sa.Column("custody_end",sa.DateTime(timezone=True)),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["repository_id"],["healthnet.repository.id"]), sa.PrimaryKeyConstraint("id"), schema="healthnet")
    op.create_index("ix_ehr_custody_health_id","ehr_custody",["health_id"],schema="healthnet")
    op.create_index("ix_ehr_custody_repository_id","ehr_custody",["repository_id"],schema="healthnet")

    op.create_table("record_locator",
        sa.Column("id",sa.Uuid(),nullable=False), sa.Column("health_id",sa.String(32),nullable=False),
        sa.Column("repository_id",sa.Uuid(),nullable=False), sa.Column("endpoint",sa.String(512),nullable=False),
        sa.Column("resource_types",sa.String(512),nullable=False), sa.Column("status",sa.String(16),nullable=False,server_default="ACTIVE"),
        sa.Column("last_verified_at",sa.DateTime(timezone=True)), sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.Column("notes",sa.Text()), sa.ForeignKeyConstraint(["repository_id"],["healthnet.repository.id"]),
        sa.PrimaryKeyConstraint("id"),schema="healthnet")
    op.create_index("ix_record_locator_health_id","record_locator",["health_id"],schema="healthnet")
    op.create_index("ix_record_locator_repository_id","record_locator",["repository_id"],schema="healthnet")
    op.create_index("ix_record_locator_status","record_locator",["status"],schema="healthnet")

    op.create_table("organization",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("external_id",sa.String(128),nullable=False),
        sa.Column("name",sa.String(200),nullable=False),sa.Column("jurisdiction",sa.String(32),nullable=False),
        sa.Column("trust_status",sa.String(16),nullable=False,server_default="ACTIVE"),
        sa.Column("issuer",sa.String(512)),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("external_id"),schema="healthnet")
    op.create_index("ix_organization_external_id","organization",["external_id"],schema="healthnet")
    op.create_index("ix_organization_jurisdiction","organization",["jurisdiction"],schema="healthnet")
    op.create_index("ix_organization_trust_status","organization",["trust_status"],schema="healthnet")

    op.create_table("provider",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("external_id",sa.String(128),nullable=False),
        sa.Column("given_name",sa.String(100),nullable=False),sa.Column("family_name",sa.String(100),nullable=False),
        sa.Column("license_number",sa.String(128),nullable=False),sa.Column("jurisdiction",sa.String(32),nullable=False),
        sa.Column("trust_status",sa.String(16),nullable=False,server_default="ACTIVE"),
        sa.Column("keycloak_subject",sa.String(128)),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("external_id"),sa.UniqueConstraint("license_number"),schema="healthnet")
    op.create_index("ix_provider_external_id","provider",["external_id"],schema="healthnet")
    op.create_index("ix_provider_license_number","provider",["license_number"],schema="healthnet")
    op.create_index("ix_provider_trust_status","provider",["trust_status"],schema="healthnet")
    op.create_index("ix_provider_keycloak_subject","provider",["keycloak_subject"],schema="healthnet",unique=True)

    op.create_table("practitioner_role",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("provider_id",sa.Uuid(),nullable=False),
        sa.Column("organization_id",sa.Uuid(),nullable=False),sa.Column("role",sa.String(32),nullable=False),
        sa.Column("active",sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.ForeignKeyConstraint(["provider_id"],["healthnet.provider.id"]),
        sa.ForeignKeyConstraint(["organization_id"],["healthnet.organization.id"]),
        sa.PrimaryKeyConstraint("id"),schema="healthnet")

    op.create_table("consent",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("health_id",sa.String(32),nullable=False),
        sa.Column("grantee_type",sa.String(32),nullable=False),sa.Column("grantee_id",sa.String(128),nullable=False),
        sa.Column("purpose",sa.String(128),nullable=False),sa.Column("scopes",sa.String(512),nullable=False),
        sa.Column("status",sa.String(16),nullable=False,server_default="ACTIVE"),
        sa.Column("valid_from",sa.DateTime(timezone=True),nullable=False),sa.Column("valid_until",sa.DateTime(timezone=True)),
        sa.Column("revoked_at",sa.DateTime(timezone=True)),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.Column("reason",sa.Text()),sa.PrimaryKeyConstraint("id"),schema="healthnet")
    op.create_index("ix_consent_health_id","consent",["health_id"],schema="healthnet")
    op.create_index("ix_consent_grantee_id","consent",["grantee_id"],schema="healthnet")
    op.create_index("ix_consent_status","consent",["status"],schema="healthnet")

def downgrade():
    for table in ["consent","practitioner_role","provider","organization","record_locator","ehr_custody","repository"]:
        op.drop_table(table,schema="healthnet")
