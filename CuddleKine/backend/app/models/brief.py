"""Brief 模型 — 结构化需求摘要"""
from sqlalchemy import Column, Integer, Text, Boolean, DateTime, ForeignKey, func
from ..database import Base


class Brief(Base):
    __tablename__ = "briefs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, default=1)
    is_confirmed = Column(Boolean, default=False)

    # 结构化内容 (JSON)
    structured_content = Column(Text, comment="提取的结构化需求 JSON")

    # 追问
    missing_info = Column(Text, comment="缺失信息列表 JSON")
    conflicts = Column(Text, comment="冲突项列表 JSON")

    # 客户答复
    customer_replies = Column(Text, comment="客户答复 JSON")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
