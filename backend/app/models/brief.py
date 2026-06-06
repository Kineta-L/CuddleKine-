"""Structured plush toy brief model."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func

from ..database import Base


class Brief(Base):
    __tablename__ = "briefs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, default=1)
    is_confirmed = Column(Boolean, default=False)

    structured_content = Column(Text, comment="Structured brief JSON")
    missing_info = Column(Text, comment="Missing info JSON")
    conflicts = Column(Text, comment="Conflict list JSON")
    customer_replies = Column(Text, comment="Customer reply JSON")

    # Phase 1 AI engineering trace fields.
    source_material_ids = Column(Text, default="", comment="Material id list JSON")
    source_type = Column(String(64), default="", comment="Dominant source type")
    pending_questions = Column(Text, default="", comment="Customer-facing questions JSON")
    risk_notes = Column(Text, default="", comment="Risk notes JSON")
    designer_edits = Column(Text, default="", comment="Designer edit patch JSON")
    ai_model_used = Column(String(128), default="rule-based", comment="AI/model used")
    prompt_version = Column(String(64), default="plush-prompt-v1", comment="Prompt builder version")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
