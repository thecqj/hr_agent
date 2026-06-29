"""add_requirements_to_jobs

Revision ID: 9d45e7aca4fb
Revises: 1ac3bbb5967e
Create Date: 2026-06-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9d45e7aca4fb'
down_revision: Union[str, None] = '1ac3bbb5967e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add column as nullable
    op.add_column('jobs', sa.Column('requirements', sa.Text(), nullable=True))
    # Step 2: Backfill existing rows with empty string
    op.execute("UPDATE jobs SET requirements = '' WHERE requirements IS NULL")
    # Step 3: Make NOT NULL
    op.alter_column('jobs', 'requirements', nullable=False)


def downgrade() -> None:
    op.drop_column('jobs', 'requirements')
