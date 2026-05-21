"""话题段管理 — 按 thread_id 找到当前活跃段，不存在则新建"""
from typing import Optional

from sqlalchemy import select
from loguru import logger as _log

from app.core.database import AsyncSessionLocal
from app.models.conversation import Conversation
from app.models.topic_segment import TopicSegment


class SegmentManager:
    """所有段操作走静态方法，无实例状态，测试时可直接 mock"""

    @staticmethod
    async def get_or_open_segment(thread_id: str) -> Optional[int]:
        """返回 thread_id 对应 conversation 的当前活跃段 ID。

        找不到 Conversation 记录时返回 None（会话还未落库，跳过 slot 隔离）。
        """
        async with AsyncSessionLocal() as db:
            conv = (await db.execute(
                select(Conversation).where(Conversation.thread_id == thread_id)
            )).scalar_one_or_none()

            if not conv:
                _log.warning(f"SegmentManager: thread {thread_id} 无 Conversation，跳过段管理")
                return None

            seg = (await db.execute(
                select(TopicSegment)
                .where(
                    TopicSegment.conversation_id == conv.id,
                    TopicSegment.ended_at.is_(None),
                )
            )).scalar_one_or_none()

            if seg:
                return seg.id

            new_seg = TopicSegment(conversation_id=conv.id)
            db.add(new_seg)
            await db.commit()
            await db.refresh(new_seg)
            _log.info(f"SegmentManager: opened segment {new_seg.id} for conv {conv.id}")
            return new_seg.id

    @staticmethod
    async def end_segment(segment_id: int, summary: str = "") -> None:
        """标记段结束（写 ended_at），可选写入 LLM 摘要。"""
        from datetime import datetime
        async with AsyncSessionLocal() as db:
            seg = (await db.execute(
                select(TopicSegment).where(TopicSegment.id == segment_id)
            )).scalar_one_or_none()
            if seg and seg.ended_at is None:
                seg.ended_at = datetime.utcnow()
                if summary:
                    seg.summary = summary
                await db.commit()
                _log.info(f"SegmentManager: closed segment {segment_id}")
