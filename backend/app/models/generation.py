"""Image generation record model."""
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func

from ..database import Base


class ViewType(str, enum.Enum):
    MAIN = "main"
    FRONT = "front"
    SIDE = "side"
    BACK = "back"


class GenerationRecord(Base):
    __tablename__ = "generation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)

    source_version_id = Column(Integer, comment="Source material or generation id")
    derivation_type = Column(String(32), comment="main_view_candidate/local_modify/front/side/back")
    view_type = Column(Enum(ViewType), nullable=False)
    file_path = Column(String(512), comment="Generated image path")
    locked_regions = Column(Text, comment="Locked region JSON")

    provider = Column(String(32), default="", comment="comfyui/openai/replicate/mock")
    provider_model = Column(String(128), default="", comment="Provider model")
    quality_mode = Column(String(16), default="sample", comment="draft/sample/final")
    prompt = Column(Text, default="", comment="Final positive prompt, legacy field")
    negative_prompt = Column(Text, default="", comment="Final negative prompt")
    reference_material_id = Column(Integer, comment="Reference material id")
    raw_params = Column(Text, comment="Generation params JSON")
    raw_response = Column(Text, comment="Raw response summary JSON")
    cost_estimate = Column(Float, default=0.0, comment="Estimated cost in USD")
    output_has_alpha = Column(Boolean, default=False, comment="Transparent output")
    postprocess_status = Column(String(16), default="", comment="Postprocess status")

    # Phase 1 AI engineering trace fields.
    brief_id = Column(Integer, comment="Structured brief id used for generation")
    prompt_builder_version = Column(String(64), default="", comment="Prompt builder version")
    final_prompt = Column(Text, default="", comment="Internal final prompt")
    provider_prompt = Column(Text, default="", comment="Provider-adapted prompt")
    source_material_ids = Column(Text, default="", comment="Material id list JSON")
    quality_status = Column(String(32), default="unreviewed", comment="usable/needs_revision/rejected")
    review_notes = Column(Text, default="", comment="Designer review notes")

    # Legacy compatibility fields.
    model_name = Column(String(128), comment="Deprecated; use provider_model")
    license_status = Column(String(32), default="unreviewed", comment="License status")
    workflow_version = Column(String(64), comment="Workflow version")
    generation_params = Column(Text, comment="Deprecated; use raw_params")

    duration = Column(Float, comment="Generation duration seconds")
    error_message = Column(Text, comment="Error message")
    created_at = Column(DateTime, server_default=func.now())
