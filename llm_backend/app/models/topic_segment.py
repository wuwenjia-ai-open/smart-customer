from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text, func
from app.core.database import Base


class TopicSegment(Base):
    """话题段 — 一条 conversation 按话题切分成多个段，slots 挂在段上而非整条对话"""
    __tablename__ = "topic_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    ended_at = Column(DateTime, nullable=True, comment="NULL = 当前活跃段")
    summary = Column(Text, nullable=True, comment="段结束后 LLM 压缩的话题摘要")
