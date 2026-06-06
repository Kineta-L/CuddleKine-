"""Material model."""
import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, func

from ..database import Base


class MaterialType(str, enum.Enum):
    TEXT = "text"
    CHAT_SCREENSHOT = "chat_screenshot"
    PHOTO = "photo"
    SKETCH = "sketch"
    REFERENCE = "reference"


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    type = Column(Enum(MaterialType), nullable=False)
    file_path = Column(String(512), comment="Stored file path")
    original_name = Column(String(256), comment="Original upload name")
    ocr_text = Column(Text, comment="OCR text")
    notes = Column(Text, comment="Designer notes")

    # AI material understanding trace fields.
    source_type = Column(String(64), default="", comment="Normalized source type")
    detected_subject = Column(String(256), default="", comment="Detected main subject")
    image_width = Column(Integer, comment="Image width in pixels")
    image_height = Column(Integer, comment="Image height in pixels")
    ai_description = Column(Text, default="", comment="AI or rule-based material description")
    visual_features_json = Column(Text, default="", comment="Detected visual features JSON")
    processing_status = Column(String(32), default="pending", comment="pending/analyzed/error")

    created_at = Column(DateTime, server_default=func.now())
