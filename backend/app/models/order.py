"""Order model."""
import enum

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String, Text, func

from ..database import Base


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    MATERIAL_IMPORTED = "material_imported"
    BRIEF_PENDING = "brief_pending"
    BRIEF_CONFIRMED = "brief_confirmed"
    GENERATING = "generating"
    REVIEWING = "reviewing"
    EXPORTED = "exported"
    ARCHIVED = "archived"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(32), unique=True, nullable=False, comment="Order number")
    customer_name = Column(String(128), comment="Customer name")

    # Legacy editable brief fields kept for compatibility and quick display.
    character_type = Column(String(128), comment="Character type")
    target_height = Column(Float, comment="Target finished height in cm")
    main_proportions = Column(Text, comment="Main proportions")
    colors = Column(Text, comment="Color palette")
    material_preference = Column(Text, comment="Material preference")
    accessories = Column(Text, comment="Accessories")
    key_features = Column(Text, comment="Key identity features")
    allowed_simplifications = Column(Text, comment="Allowed simplifications")
    pending_items = Column(Text, comment="Pending items")
    craft_notes = Column(Text, comment="Craft notes")

    status = Column(Enum(OrderStatus), default=OrderStatus.DRAFT, nullable=False)
    confirmed_version_id = Column(Integer, comment="Confirmed generation version id")

    # AI brief workflow state.
    brief_status = Column(String(32), default="not_started", comment="not_started/analyzing/pending/confirmed")
    confirmed_brief_id = Column(Integer, comment="Confirmed structured brief id")
    source_summary = Column(Text, default="", comment="Material source summary")
    customer_question_status = Column(String(32), default="not_needed", comment="not_needed/pending/answered")

    # Pattern/package reserved fields.
    parts_list = Column(Text, comment="Parts list")
    symmetry_relations = Column(Text, comment="Symmetry relations")
    connection_relations = Column(Text, comment="Connection relations")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
