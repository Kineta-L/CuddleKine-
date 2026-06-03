"""生成记录模型"""
import enum
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Enum, ForeignKey, func
from ..database import Base


class ViewType(str, enum.Enum):
    MAIN = "main"           # 主视图
    FRONT = "front"         # 正面
    SIDE = "side"           # 侧面
    BACK = "back"           # 背面


class GenerationRecord(Base):
    __tablename__ = "generation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)

    # 派生关系
    source_version_id = Column(Integer, comment="来源版本ID（material 或 generation id）")
    derivation_type = Column(String(32), comment="派生类型: main_view_candidate/selected/local_modify/front/side/back")

    # 视图类型
    view_type = Column(Enum(ViewType), nullable=False)

    # 文件
    file_path = Column(String(512), comment="生成图片路径")

    # 锁定区域 (JSON)
    locked_regions = Column(Text, comment="锁定区域定义 JSON")

    # ── Provider 信息（Phase 1 新增） ──
    provider = Column(String(32), default="", comment="使用的供应商: comfyui/openai/replicate/mock")
    provider_model = Column(String(128), default="", comment="使用的模型名称")
    quality_mode = Column(String(16), default="sample", comment="质量模式: draft/sample/final")
    prompt = Column(Text, default="", comment="最终正向提示词")
    negative_prompt = Column(Text, default="", comment="最终负向提示词")
    reference_material_id = Column(Integer, comment="使用的参考素材ID")
    raw_params = Column(Text, comment="生成参数 JSON")
    raw_response = Column(Text, comment="API 原始响应摘要 JSON")
    cost_estimate = Column(Float, default=0.0, comment="成本估算(USD)")
    output_has_alpha = Column(Boolean, default=False, comment="是否透明背景")
    postprocess_status = Column(String(16), default="", comment="后处理状态")

    # ── 旧字段（保留兼容） ──
    model_name = Column(String(128), comment="使用的模型名称（已废弃，见 provider_model）")
    license_status = Column(String(32), default="unreviewed", comment="许可证状态")
    workflow_version = Column(String(64), comment="工作流版本")
    generation_params = Column(Text, comment="生成参数 JSON（已废弃，见 raw_params）")

    # 性能
    duration = Column(Float, comment="生成耗时(秒)")

    # 错误
    error_message = Column(Text, comment="失败原因")

    created_at = Column(DateTime, server_default=func.now())
