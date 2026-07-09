"""add mode column to evaluation_tasks

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "evaluation_tasks",
        sa.Column(
            "mode",
            sa.String(length=20),
            nullable=False,
            server_default="new_only",
            comment="评估模式: new_only=仅新投递, all=重新评估全部",
        ),
    )


def downgrade() -> None:
    op.drop_column("evaluation_tasks", "mode")
