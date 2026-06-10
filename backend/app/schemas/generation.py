"""Schemas for image generation APIs."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    order_id: int
    provider: str = ""
    model: str = ""
    quality_mode: str = ""
    workflow_name: str = "main_view.json"
    view_type: str = "main"
    derivation_type: str = "main_view_candidate"
    source_version_id: Optional[int] = None
    locked_regions: Optional[str] = None
    modification_prompt: Optional[str] = None
    model_name: Optional[str] = None
    reference_material_id: Optional[int] = None
    transparent_background: Optional[bool] = None
    overrides: Optional[dict] = None

    # AI engineering trace fields.
    brief_id: Optional[int] = None
    source_material_ids: Optional[list[int]] = None
    prompt_builder_version: Optional[str] = None
    use_confirmed_brief_only: bool = True


class GenerationResponse(BaseModel):
    id: int
    order_id: int
    provider: str = ""
    provider_model: str = ""
    quality_mode: str = "sample"
    source_version_id: Optional[int]
    derivation_type: Optional[str]
    view_type: str
    file_path: Optional[str]
    locked_regions: Optional[str]
    model_name: Optional[str]
    license_status: Optional[str]
    workflow_version: Optional[str]
    duration: Optional[float]
    error_message: Optional[str]
    brief_id: Optional[int] = None
    prompt_builder_version: str = ""
    final_prompt: str = ""
    provider_prompt: str = ""
    source_material_ids: str = ""
    quality_status: str = "unreviewed"
    review_notes: str = ""
    created_at: str

    model_config = {"from_attributes": True}
