"""add conversations table

Revision ID: 2c7f74d29c65
Revises: 0da1a2fe2051
Create Date: 2026-06-30 14:15:36.428601

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2c7f74d29c65'
down_revision: Union[str, Sequence[str], None] = '0da1a2fe2051'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('conversations',
    sa.Column('user_id', sa.UUID(), nullable=False, comment='FK → users.id'),
    sa.Column('session_id', sa.String(length=36), nullable=False, comment='= LangGraph thread_id'),
    sa.Column('summary', sa.Text(), nullable=True, comment='LLM 生成的会话摘要'),
    sa.Column('context_entities', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='结构化实体 {current_job_id, current_job_code, ...}'),
    sa.Column('is_active', sa.Boolean(), nullable=False, comment='会话是否活跃'),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id')
    )
    op.create_index('ix_conversations_user_active', 'conversations', ['user_id', 'is_active'], unique=False)
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_conversations_user_id'), table_name='conversations')
    op.drop_index('ix_conversations_user_active', table_name='conversations')
    op.drop_table('conversations')
