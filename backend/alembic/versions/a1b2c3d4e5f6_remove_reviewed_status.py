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
    # Migrate existing reviewed records to interview
    op.execute("UPDATE applications SET status = 'interview' WHERE status = 'reviewed'")
    # NOTE: The PostgreSQL native enum type 'applicationstatus' still contains 'REVIEWED'
    # as a valid value. This is harmless — the application code no longer produces 'reviewed'
    # status values. Removing a value from a PG enum requires DROP/RECREATE which is risky
    # on production databases with dependent columns. Leaving the dead value is the safe choice.


def downgrade() -> None:
    # Cannot automatically reverse — reviewed status has been removed
    pass
