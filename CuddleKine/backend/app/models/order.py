"""订单模型"""
import enum
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum, func
from ..database import Base


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"                    # 草稿
    MATERIAL_IMPORTED = "material_imported"  # 素材已导入
    BRIEF_PENDING = "brief_pending"    # 待确认 brief
    BRIEF_CONFIRMED = "brief_confirmed"  # brief 已确认
    GENERATING = "generating"          # 生成中
    REVIEWING = "reviewing"            # 审核中
    EXPORTED = "exported"              # 已导出
    ARCHIVED = "archived"              # 已归档


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(32), unique=True, nullable=False, comment="订单编号")
    customer_name = Column(String(128), comment="客户名称")

    # Brief 核心字段
    character_type = Column(String(128), comment="角色类型")
    target_height = Column(Float, comment="目标成品高度(cm)")
    main_proportions = Column(Text, comment="主要比例描述")
    colors = Column(Text, comment="颜色")
    material_preference = Column(Text, comment="材质倾向")
    accessories = Column(Text, comment="配件")
    key_features = Column(Text, comment="关键辨识特征")
    allowed_simplifications = Column(Text, comment="允许简化项")
    pending_items = Column(Text, comment="待确认项")
    craft_notes = Column(Text, comment="工艺备注")

    # 状态
    status = Column(Enum(OrderStatus), default=OrderStatus.DRAFT, nullable=False)
    confirmed_version_id = Column(Integer, comment="已确认的生成版本ID")

    # 纸样预留字段
    parts_list = Column(Text, comment="部件列表")
    symmetry_relations = Column(Text, comment="对称关系")
    connection_relations = Column(Text, comment="连接关系")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
