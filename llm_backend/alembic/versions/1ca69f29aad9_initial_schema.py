"""initial_schema — 创建用户、会话、消息三张表

Revision ID: 1ca69f29aad9
Revises:
Create Date: 2026-05-05 23:03:19.936848
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '1ca69f29aad9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('username', sa.String(50), unique=True, nullable=False),
        sa.Column('email', sa.String(100), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(20), default='active'),
    )

    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('status', sa.String(20), default='ongoing'),
        sa.Column('dialogue_type', sa.Enum('NORMAL', 'DEEP_THINKING', 'WEB_SEARCH', 'RAG',
                                           name='dialogue_type'), nullable=False),
    )

    op.create_table(
        'messages',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('conversation_id', sa.Integer, sa.ForeignKey('conversations.id', ondelete='CASCADE')),
        sa.Column('sender', sa.String(50), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('message_type', sa.String(20), default='text'),
    )


def downgrade() -> None:
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('users')
    op.execute("DROP TYPE IF EXISTS dialogue_type")
