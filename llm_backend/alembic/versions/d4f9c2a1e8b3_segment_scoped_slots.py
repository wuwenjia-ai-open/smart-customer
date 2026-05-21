"""segment scoped slots: add topic_segments, rebuild dialogue_states

Revision ID: d4f9c2a1e8b3
Revises: 618835c30a0e
Create Date: 2026-05-20

变更说明:
  1. 新增 topic_segments 表 — conversation 按话题段切分，slots 挂在段上
  2. 重建 dialogue_states — PK 从 thread_id 改为 (segment_id, worker_type)
     旧表数据直接丢弃（demo 环境可接受，生产需迁移脚本）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4f9c2a1e8b3'
down_revision: Union[str, Sequence[str], None] = '618835c30a0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 新增 topic_segments
    op.create_table(
        'topic_segments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True, comment='NULL = 当前活跃段'),
        sa.Column('summary', sa.Text(), nullable=True, comment='段结束后 LLM 压缩的话题摘要'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_topic_segments_conversation_id', 'topic_segments', ['conversation_id'])

    # 2. 重建 dialogue_states（旧表结构不兼容，直接 drop + recreate）
    op.drop_index('ix_dialogue_states_thread_id', table_name='dialogue_states')
    op.drop_table('dialogue_states')

    op.create_table(
        'dialogue_states',
        sa.Column('segment_id', sa.Integer(), nullable=False),
        sa.Column('worker_type', sa.String(length=32), nullable=False,
                  comment='worker名 或 _profile'),
        sa.Column('slots', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['segment_id'], ['topic_segments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('segment_id', 'worker_type'),
    )


def downgrade() -> None:
    op.drop_table('dialogue_states')
    op.drop_index('ix_topic_segments_conversation_id', table_name='topic_segments')
    op.drop_table('topic_segments')

    # 恢复旧的 dialogue_states
    op.create_table(
        'dialogue_states',
        sa.Column('thread_id', sa.String(length=64), nullable=False),
        sa.Column('slots', sa.JSON(), nullable=False, comment='累积的对话状态键值对'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('thread_id'),
    )
    op.create_index('ix_dialogue_states_thread_id', 'dialogue_states', ['thread_id'], unique=False)
