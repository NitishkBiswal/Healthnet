"""Identity resolution tables and expanded Indian jurisdiction seed data.

Revision ID: 0007_identity_resolution_and_jurisdictions
Revises: 0006_segment14
Create Date: 2026-11-06
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_identity_resolution_and_jurisdictions"
down_revision = "0006_segment14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Identity match log — records every match attempt during reg.      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "identity_match",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("query_health_id", sa.String(32), nullable=True),
        sa.Column("candidate_health_id", sa.String(32), nullable=False),
        sa.Column("match_method", sa.String(32), nullable=False),   # DETERMINISTIC | PROBABILISTIC
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("band", sa.String(16), nullable=False),            # HIGH | MEDIUM
        sa.Column("outcome", sa.String(32), nullable=False),         # REGISTERED | DUPLICATE_REVIEW | LIKELY_DUPLICATE
        sa.Column("duplicate_review_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="healthnet",
    )
    op.create_index("ix_identity_match_query_health_id",     "identity_match", ["query_health_id"],     schema="healthnet")
    op.create_index("ix_identity_match_candidate_health_id", "identity_match", ["candidate_health_id"], schema="healthnet")
    op.create_index("ix_identity_match_outcome",             "identity_match", ["outcome"],             schema="healthnet")

    # ------------------------------------------------------------------ #
    # 2. Identity merge event log — immutable record of every merge        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "identity_merge_event",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_patient_id", sa.Uuid(), nullable=False),
        sa.Column("source_health_id", sa.String(32), nullable=False),
        sa.Column("target_patient_id", sa.Uuid(), nullable=False),
        sa.Column("target_health_id", sa.String(32), nullable=False),
        sa.Column("authorized_by", sa.String(128), nullable=False),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("merged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="healthnet",
    )
    op.create_index("ix_identity_merge_event_source_patient_id", "identity_merge_event", ["source_patient_id"], schema="healthnet")
    op.create_index("ix_identity_merge_event_target_patient_id", "identity_merge_event", ["target_patient_id"], schema="healthnet")

    # ------------------------------------------------------------------ #
    # 3. Expand jurisdiction seed data — 18 Indian states + UT + 3 intl.  #
    # ------------------------------------------------------------------ #
    op.execute("""
        INSERT INTO healthnet.jurisdiction (id, code, name, active) VALUES
        ('00000000-0000-0000-0000-000000000701', 'IN-MH', 'Maharashtra',       true),
        ('00000000-0000-0000-0000-000000000702', 'IN-DL', 'Delhi',             true),
        ('00000000-0000-0000-0000-000000000703', 'IN-TN', 'Tamil Nadu',        true),
        ('00000000-0000-0000-0000-000000000704', 'IN-WB', 'West Bengal',       true),
        ('00000000-0000-0000-0000-000000000705', 'IN-GJ', 'Gujarat',           true),
        ('00000000-0000-0000-0000-000000000706', 'IN-RJ', 'Rajasthan',         true),
        ('00000000-0000-0000-0000-000000000707', 'IN-UP', 'Uttar Pradesh',     true),
        ('00000000-0000-0000-0000-000000000708', 'IN-MP', 'Madhya Pradesh',    true),
        ('00000000-0000-0000-0000-000000000709', 'IN-BR', 'Bihar',             true),
        ('00000000-0000-0000-0000-000000000710', 'IN-KL', 'Kerala',            true),
        ('00000000-0000-0000-0000-000000000711', 'IN-AP', 'Andhra Pradesh',    true),
        ('00000000-0000-0000-0000-000000000712', 'IN-TS', 'Telangana',         true),
        ('00000000-0000-0000-0000-000000000713', 'IN-AS', 'Assam',             true),
        ('00000000-0000-0000-0000-000000000714', 'IN-PB', 'Punjab',            true),
        ('00000000-0000-0000-0000-000000000715', 'IN-HR', 'Haryana',           true),
        ('00000000-0000-0000-0000-000000000716', 'IN-CH', 'Chandigarh (UT)',   true),
        ('00000000-0000-0000-0000-000000000717', 'IN-GA', 'Goa',               true),
        ('00000000-0000-0000-0000-000000000718', 'IN-JH', 'Jharkhand',         true),
        ('00000000-0000-0000-0000-000000000719', 'IN-AR', 'Arunachal Pradesh', true),
        ('00000000-0000-0000-0000-000000000720', 'IN-CT', 'Chhattisgarh',      true),
        ('00000000-0000-0000-0000-000000000721', 'IN-HP', 'Himachal Pradesh',  true),
        ('00000000-0000-0000-0000-000000000722', 'IN-MN', 'Manipur',           true),
        ('00000000-0000-0000-0000-000000000723', 'IN-ML', 'Meghalaya',         true),
        ('00000000-0000-0000-0000-000000000724', 'IN-MZ', 'Mizoram',           true),
        ('00000000-0000-0000-0000-000000000725', 'IN-NL', 'Nagaland',          true),
        ('00000000-0000-0000-0000-000000000726', 'IN-SK', 'Sikkim',            true),
        ('00000000-0000-0000-0000-000000000727', 'IN-TR', 'Tripura',           true),
        ('00000000-0000-0000-0000-000000000728', 'IN-UT', 'Uttarakhand',       true),
        ('00000000-0000-0000-0000-000000000729', 'IN-AN', 'Andaman and Nicobar Islands', true),
        ('00000000-0000-0000-0000-000000000730', 'IN-DN', 'Dadra and Nagar Haveli and Daman and Diu', true),
        ('00000000-0000-0000-0000-000000000731', 'IN-JK', 'Jammu and Kashmir', true),
        ('00000000-0000-0000-0000-000000000732', 'IN-LA', 'Ladakh',           true),
        ('00000000-0000-0000-0000-000000000733', 'IN-LD', 'Lakshadweep',       true),
        ('00000000-0000-0000-0000-000000000734', 'IN-PY', 'Puducherry',        true)
        ON CONFLICT DO NOTHING
    """)

    # ------------------------------------------------------------------ #
    # 4. Add default ALLOW policy rules for cross-Indian-state access      #
    #    for TREATMENT purpose with clinical scope.                        #
    #    Rule: any IN-* source jurisdiction can share to any IN-*          #
    #    destination for TREATMENT/clinical.                               #
    # ------------------------------------------------------------------ #
    jurisdictions = op.get_bind().execute(
        sa.text("SELECT id, code FROM healthnet.jurisdiction WHERE code LIKE 'IN-%'")
    )
    for jid, jcode in jurisdictions:
        op.execute(f"""
            INSERT INTO healthnet.policy_rule
                (id, jurisdiction_id, name, purpose, scope, effect, description, active)
            VALUES (
                gen_random_uuid(),
                '{jid}',
                'India ABDM Cross-State TREATMENT Allow - {jcode}',
                'TREATMENT',
                'clinical',
                'ALLOW',
                'Default ABDM-aligned rule permitting cross-state clinical data sharing for TREATMENT within India.',
                true
            )
            ON CONFLICT DO NOTHING
        """)
        op.execute(f"""
            INSERT INTO healthnet.policy_rule
                (id, jurisdiction_id, name, purpose, scope, effect, description, active)
            VALUES (
                gen_random_uuid(),
                '{jid}',
                'India ABDM Emergency Access Allow - {jcode}',
                'EMERGENCY',
                'clinical',
                'ALLOW',
                'Default rule permitting emergency access to clinical records across Indian jurisdictions.',
                true
            )
            ON CONFLICT DO NOTHING
        """)


def downgrade() -> None:
    op.execute("DELETE FROM healthnet.policy_rule WHERE name LIKE 'India ABDM%'")
    op.execute("""
        DELETE FROM healthnet.jurisdiction WHERE id IN (
            '00000000-0000-0000-0000-000000000701',
            '00000000-0000-0000-0000-000000000702',
            '00000000-0000-0000-0000-000000000703',
            '00000000-0000-0000-0000-000000000704',
            '00000000-0000-0000-0000-000000000705',
            '00000000-0000-0000-0000-000000000706',
            '00000000-0000-0000-0000-000000000707',
            '00000000-0000-0000-0000-000000000708',
            '00000000-0000-0000-0000-000000000709',
            '00000000-0000-0000-0000-000000000710',
            '00000000-0000-0000-0000-000000000711',
            '00000000-0000-0000-0000-000000000712',
            '00000000-0000-0000-0000-000000000713',
            '00000000-0000-0000-0000-000000000714',
            '00000000-0000-0000-0000-000000000715',
            '00000000-0000-0000-0000-000000000716',
            '00000000-0000-0000-0000-000000000717',
            '00000000-0000-0000-0000-000000000718',
            '00000000-0000-0000-0000-000000000719',
            '00000000-0000-0000-0000-000000000720',
            '00000000-0000-0000-0000-000000000721',
            '00000000-0000-0000-0000-000000000722',
            '00000000-0000-0000-0000-000000000723',
            '00000000-0000-0000-0000-000000000724',
            '00000000-0000-0000-0000-000000000725',
            '00000000-0000-0000-0000-000000000726',
            '00000000-0000-0000-0000-000000000727',
            '00000000-0000-0000-0000-000000000728',
            '00000000-0000-0000-0000-000000000729',
            '00000000-0000-0000-0000-000000000730',
            '00000000-0000-0000-0000-000000000731',
            '00000000-0000-0000-0000-000000000732',
            '00000000-0000-0000-0000-000000000733',
            '00000000-0000-0000-0000-000000000734'
        )
    """)
    op.drop_index("ix_identity_merge_event_target_patient_id", table_name="identity_merge_event", schema="healthnet")
    op.drop_index("ix_identity_merge_event_source_patient_id", table_name="identity_merge_event", schema="healthnet")
    op.drop_table("identity_merge_event", schema="healthnet")
    op.drop_index("ix_identity_match_outcome",             table_name="identity_match", schema="healthnet")
    op.drop_index("ix_identity_match_candidate_health_id", table_name="identity_match", schema="healthnet")
    op.drop_index("ix_identity_match_query_health_id",     table_name="identity_match", schema="healthnet")
    op.drop_table("identity_match", schema="healthnet")
