"""drop interview_quota, is_active, context_entities

Revision ID: drop_three_fields
Revises: 2c7f74d29c65
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'drop_three_fields'
down_revision: Union[str, Sequence[str], None] = '2c7f74d29c65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop interview_quota from jobs, is_active + context_entities from conversations."""
    # jobs: drop interview_quota
    op.drop_column('jobs', 'interview_quota')

    # conversations: drop is_active (with index first)
    op.drop_index('ix_conversations_user_active', table_name='conversations')
    op.drop_column('conversations', 'is_active')

    # conversations: drop context_entities
    op.drop_column('conversations', 'context_entities')


def downgrade() -> None:
    """Re-add the dropped columns."""
    # conversations: re-add context_entities
    op.add_column('conversations', sa.Column(
        'context_entities',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        comment='结构化实体 {current_job_id, current_job_code, ...}',
    ))

    # conversations: re-add is_active
    op.add_column('conversations', sa.Column(
        'is_active',
        sa.Boolean(),
        nullable=False,
        server_default=sa.text('true'),
        comment='会话是否活跃',
    ))
    op.create_index('ix_conversations_user_active', 'conversations', ['user_id', 'is_active'], unique=False)

    # jobs: re-add interview_quota
    op.add_column('jobs', sa.Column(
        'interview_quota',
        sa.Integer(),
        nullable=False,
        server_default=sa.text('1'),
        comment='面试人数上限',
    ))
