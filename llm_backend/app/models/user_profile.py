from sqlalchemy import Column, Integer, ForeignKey, DateTime, JSON, func
from app.core.database import Base


class UserProfile(Base):
    """用户画像 — 跨会话沉淀的长期偏好"""
    __tablename__ = "user_profiles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    preferences = Column(JSON, nullable=False, default=dict,
                         comment="例如 preferred_brands/budget_range/history_categories")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
