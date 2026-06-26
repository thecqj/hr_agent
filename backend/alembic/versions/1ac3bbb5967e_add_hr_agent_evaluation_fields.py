"""add_hr_agent_evaluation_fields

Revision ID: 1ac3bbb5967e
Revises: 99186d2082a7
Create Date: 2026-06-25 18:22:12.393829

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1ac3bbb5967e'
down_revision: Union[str, Sequence[str], None] = '99186d2082a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create evaltaskstatus enum type
    evaltaskstatus = postgresql.ENUM(
        'PENDING', 'RUNNING', 'COMPLETED', 'CONFIRMED', 'FAILED',
        name='evaltaskstatus',
        create_type=False,
    )

    op.execute("CREATE TYPE evaltaskstatus AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'CONFIRMED', 'FAILED')")

    # 2. Create evaluation_tasks table
    op.create_table('evaluation_tasks',
    sa.Column('job_id', sa.UUID(), nullable=False),
    sa.Column('triggered_by', sa.UUID(), nullable=False),
    sa.Column('status', evaltaskstatus, nullable=False),
    sa.Column('total_count', sa.Integer(), nullable=False),
    sa.Column('evaluated_count', sa.Integer(), nullable=False),
    sa.Column('result_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_tasks_job_id'), 'evaluation_tasks', ['job_id'], unique=False)
    op.create_index(op.f('ix_evaluation_tasks_triggered_by'), 'evaluation_tasks', ['triggered_by'], unique=False)

    # 3. Rename match_score -> ai_score (column existed in initial schema)
    op.alter_column('applications', 'match_score', new_column_name='ai_score')

    # 4. Drop ai_suggestions (column existed in initial schema, no longer in ORM)
    op.drop_column('applications', 'ai_suggestions')

    # 5. Add new AI evaluation fields on applications
    op.add_column('applications', sa.Column('ai_evaluation', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('applications', sa.Column('ai_decision', sa.String(length=20), nullable=True))
    op.add_column('applications', sa.Column('ai_decision_reason', sa.Text(), nullable=True))
    op.add_column('applications', sa.Column('ai_evaluated_at', sa.DateTime(), nullable=True))

    # 6. Add interview_quota to jobs
    op.add_column('jobs', sa.Column('interview_quota', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # 6. Remove interview_quota from jobs
    op.drop_column('jobs', 'interview_quota')

    # 5. Remove new AI evaluation fields from applications
    op.drop_column('applications', 'ai_evaluated_at')
    op.drop_column('applications', 'ai_decision_reason')
    op.drop_column('applications', 'ai_decision')
    op.drop_column('applications', 'ai_evaluation')

    # 4. Re-add ai_suggestions
    op.add_column('applications', sa.Column('ai_suggestions', sa.TEXT(), autoincrement=False, nullable=True))

    # 3. Rename ai_score back to match_score
    op.alter_column('applications', 'ai_score', new_column_name='match_score')

    # 2. Drop evaluation_tasks table
    op.drop_index(op.f('ix_evaluation_tasks_triggered_by'), table_name='evaluation_tasks')
    op.drop_index(op.f('ix_evaluation_tasks_job_id'), table_name='evaluation_tasks')
    op.drop_table('evaluation_tasks')

    # 1. Drop evaltaskstatus enum type
    op.execute('DROP TYPE evaltaskstatus')
