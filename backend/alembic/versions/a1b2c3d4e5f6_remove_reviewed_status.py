"""remove reviewed status

Revision ID: a1b2c3d4e5f6
Revises: 9d45e7aca4fb
Create Date: 2026-06-29 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9d45e7aca4fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migrate existing REVIEWED records to INTERVIEW.
    # PG native enum values are uppercase (PENDING, REVIEWED, INTERVIEW, ...).
    op.execute("UPDATE applications SET status = 'INTERVIEW' WHERE status = 'REVIEWED'")


def downgrade() -> None:
    # Cannot automatically reverse — reviewed status has been removed
    pass
