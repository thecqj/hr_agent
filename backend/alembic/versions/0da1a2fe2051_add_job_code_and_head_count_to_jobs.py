"""add job_code and head_count to jobs

Revision ID: 0da1a2fe2051
Revises: a1b2c3d4e5f6
Create Date: 2026-06-29 17:17:56.891340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0da1a2fe2051'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add job_code column (nullable first)
    op.add_column("jobs", sa.Column("job_code", sa.String(6), nullable=True))
    op.add_column("jobs", sa.Column("head_count", sa.Integer(), nullable=True))

    # 2. Assign random unique job_code to existing rows
    import random
    conn = op.get_bind()
    existing_jobs = conn.execute(
        sa.text("SELECT id FROM jobs ORDER BY created_at")
    ).fetchall()
    used_codes: set[str] = set()
    for row in existing_jobs:
        while True:
            num = random.randint(10000, 99999)
            code = f"J{num:05d}"
            if code not in used_codes:
                used_codes.add(code)
                break
        conn.execute(
            sa.text("UPDATE jobs SET job_code = :code WHERE id = :jid"),
            {"code": code, "jid": str(row[0])},
        )

    # 3. Set head_count and interview_quota defaults for existing rows
    conn.execute(
        sa.text("UPDATE jobs SET head_count = 1 WHERE head_count IS NULL")
    )
    conn.execute(
        sa.text("UPDATE jobs SET interview_quota = 1 WHERE interview_quota IS NULL")
    )

    # 4. Make columns NOT NULL
    op.alter_column("jobs", "job_code", nullable=False)
    op.alter_column("jobs", "head_count", nullable=False)
    op.alter_column("jobs", "interview_quota", nullable=False)

    # 5. Add unique constraint and index
    op.create_unique_constraint("uq_jobs_job_code", "jobs", ["job_code"])
    op.create_index("ix_jobs_job_code", "jobs", ["job_code"], unique=False)

    # 6. Set server defaults for future inserts
    op.alter_column("jobs", "head_count", server_default=sa.text("1"))
    op.alter_column("jobs", "interview_quota", server_default=sa.text("1"))


def downgrade() -> None:
    op.drop_index("ix_jobs_job_code", table_name="jobs")
    op.drop_constraint("uq_jobs_job_code", "jobs", type_="unique")
    op.alter_column("jobs", "interview_quota", nullable=True, server_default=None)
    op.alter_column("jobs", "head_count", nullable=True, server_default=None)
    op.drop_column("jobs", "head_count")
    op.drop_column("jobs", "job_code")
