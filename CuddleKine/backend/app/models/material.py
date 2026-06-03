"""素材模型"""
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, func
from ..database import Base


class MaterialType(str, enum.Enum):
    TEXT = "text"                # 文字描述
    CHAT_SCREENSHOT = "chat_screenshot"  # 聊天截图
    PHOTO = "photo"             # 照片
    SKETCH = "sketch"           # 手绘
    REFERENCE = "reference"     # 参考玩具图


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    type = Column(Enum(MaterialType), nullable=False)
    file_path = Column(String(512), comment="存储路径")
    original_name = Column(String(256), comment="原始文件名")
    ocr_text = Column(Text, comment="OCR 识别文本")
    notes = Column(Text, comment="人工备注")

    created_at = Column(DateTime, server_default=func.now())
