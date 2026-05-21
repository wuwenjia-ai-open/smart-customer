from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, func
from app.core.database import Base


class DialogueState(Base):
    """对话槽位 — 按 (segment_id, worker_type) 二维隔离，防止跨 Worker 槽位污染

    worker_type 取值:
      product_qa | order_qa | after_sales | general_chat — Worker 私有槽位
      _profile  — 跨 Worker 共享的用户偏好槽位（预算/品牌等）
    """
    __tablename__ = "dialogue_states"

    segment_id = Column(
        Integer, ForeignKey("topic_segments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    worker_type = Column(String(32), primary_key=True, comment="worker名 或 _profile")
    slots = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
