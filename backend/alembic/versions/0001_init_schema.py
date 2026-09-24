"""init schema

Revision ID: a0b1c2d3e4f5
Revises:
Create Date: 2026-09-21 15:15:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS healthnet")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS healthnet")
