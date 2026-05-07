"""add thread_id and update dialogue_type

Revision ID: a1304eeb2d47
Revises: 1ca69f29aad9
Create Date: 2026-05-07 16:24:21.761421

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1304eeb2d47'
down_revision: Union[str, Sequence[str], None] = '1ca69f29aad9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. 添加 thread_id 列
    op.add_column('conversations', sa.Column('thread_id', sa.String(length=64), nullable=True, comment='LangGraph agent 对话线程 UUID'))
    op.create_index(op.f('ix_conversations_thread_id'), 'conversations', ['thread_id'], unique=True)

    # 2. 更新 dialogue_type 枚举：先改已有数据，再改列定义
    op.execute("UPDATE conversations SET dialogue_type = 'GENERAL' WHERE dialogue_type IN ('NORMAL','DEEP_THINKING','WEB_SEARCH','RAG')")
    op.execute("ALTER TABLE conversations MODIFY COLUMN dialogue_type ENUM('GENERAL','AGENT') NOT NULL")


def downgrade() -> None:
    """Downgrade schema."""
    # 回退枚举
    op.execute("ALTER TABLE conversations MODIFY COLUMN dialogue_type ENUM('NORMAL','DEEP_THINKING','WEB_SEARCH','RAG') NOT NULL")

    op.drop_index(op.f('ix_conversations_thread_id'), table_name='conversations')
    op.drop_column('conversations', 'thread_id')
