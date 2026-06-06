"""Image generation API with provider registry and prompt traceability."""
from __future__ import annotations

import json
import base64
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import GENERATED_DIR
from ..database import get_db
from ..models.brief import Brief
from ..models.generation import GenerationRecord, ViewType
from ..models.material import Material, MaterialType
from ..models.order import Order, OrderStatus
from ..prompts import build_plush_prompt
from ..services.image_postprocess import normalize_turnaround_canvas
from ..services.prompt_builder import build_provider_prompt
from ..services.providers.base import GenerateJob
from ..services.providers.agnes_provider import AgnesProvider
from ..services.providers.comfyui_provider import ComfyUIProvider
from ..services.providers.mock_provider import MockProvider
from ..services.providers.openai_provider import OpenAIProvider
from ..services.providers.registry import get_provider, list_providers, register_provider
from ..services.providers.replicate_provider import ReplicateProvider
from ..services.settings_service import get_default_provider, get_default_quality, load_settings

router = APIRouter(prefix="/api/generation", tags=["generation"])

register_provider(ComfyUIProvider())
register_provider(OpenAIProvider())
register_provider(ReplicateProvider())
register_provider(AgnesProvider())
register_provider(MockProvider())


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

    # Phase 1 AI engineering fields.
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


def _generation_response(record: GenerationRecord) -> GenerationResponse:
    return GenerationResponse(
        id=record.id,
        order_id=record.order_id,
        provider=record.provider or "",
        provider_model=record.provider_model or "",
        quality_mode=record.quality_mode or "sample",
        source_version_id=record.source_version_id,
        derivation_type=record.derivation_type,
        view_type=record.view_type.value,
        file_path=record.file_path,
        locked_regions=record.locked_regions,
        model_name=record.model_name,
        license_status=record.license_status,
        workflow_version=record.workflow_version,
        duration=record.duration,
        error_message=record.error_message,
        brief_id=record.brief_id,
        prompt_builder_version=record.prompt_builder_version or "",
        final_prompt=record.final_prompt or "",
        provider_prompt=record.provider_prompt or "",
        source_material_ids=record.source_material_ids or "",
        quality_status=record.quality_status or "unreviewed",
        review_notes=record.review_notes or "",
        created_at=str(record.created_at),
    )


@router.get("/providers", summary="List image generation providers")
async def api_providers():
    infos = list_providers()
    for info in infos:
        try:
            provider = get_provider(info.id)
            health = await provider.health_check()
            info.configured = health.configured
        except Exception:
            info.configured = False
    return [
        {
            "id": item.id,
            "name": item.name,
            "enabled": item.enabled,
            "configured": item.configured,
            "supports_text_to_image": item.supports_text_to_image,
            "supports_image_to_image": item.supports_image_to_image,
            "supports_inpaint": item.supports_inpaint,
            "supports_transparent_background": item.supports_transparent_background,
            "models": item.models,
        }
        for item in infos
    ]


@router.post("/generate", response_model=GenerationResponse)
async def generate_image(data: GenerateRequest, db: Session = Depends(get_db)):
    order = _get_order(data.order_id, db)
    _validate_view_type(data.view_type)
    settings = load_settings()
    provider_id = _resolve_provider(data.provider)
    quality_mode = data.quality_mode or get_default_quality()
    model_name = data.model or data.model_name or str(settings.get("default_model") or "")
    transparent_background = (
        data.transparent_background
        if data.transparent_background is not None
        else bool(settings.get("transparent_background", True))
    )
    provider = get_provider(provider_id)
    await _ensure_provider_ready(provider_id, provider)

    brief = _resolve_generation_brief(order, data, quality_mode, db)
    prompt_pack = _build_prompt_pack(order, brief, data, provider_id, quality_mode)
    source_material_ids = data.source_material_ids or _source_material_ids_from_brief(brief)
    ref_images = _reference_images(order.id, data, source_material_ids, db)

    output_dir = GENERATED_DIR / str(data.order_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / f"{data.view_type}_{uuid.uuid4().hex[:8]}.png")
    params = dict(data.overrides or {})
    mask_path = _save_mask_data_url(params.pop("mask_data_url", ""), output_dir, data.view_type)
    if mask_path:
        params["mask"] = mask_path

    if mask_path and data.derivation_type == "local_modify":
        prompt_pack["provider_prompt"] = (
            f"{prompt_pack['provider_prompt']}\n"
            "Only modify the painted mask area. Preserve all unmasked parts exactly: plush identity, "
            "camera angle, canvas size, proportions, outfit, colors, accessories, material texture, and lighting."
        )
        prompt_pack["final_prompt"] = (
            f"{prompt_pack['final_prompt']}\n"
            "Only modify the painted mask area. Preserve all unmasked parts exactly."
        )

    record = GenerationRecord(
        order_id=data.order_id,
        source_version_id=data.source_version_id,
        derivation_type=data.derivation_type,
        view_type=ViewType(data.view_type),
        locked_regions=data.locked_regions,
        provider=provider_id,
        provider_model=model_name,
        quality_mode=quality_mode,
        prompt=prompt_pack["provider_prompt"],
        negative_prompt=prompt_pack["negative_prompt"],
        reference_material_id=data.reference_material_id,
        model_name=model_name or "pending",
        license_status="unreviewed",
        raw_params=json.dumps(params, ensure_ascii=False),
        brief_id=brief.id if brief else None,
        prompt_builder_version=prompt_pack["version"],
        final_prompt=prompt_pack["final_prompt"],
        provider_prompt=prompt_pack["provider_prompt"],
        source_material_ids=json.dumps(source_material_ids, ensure_ascii=False),
        quality_status="unreviewed",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        job = GenerateJob(
            order_id=data.order_id,
            provider=provider_id,
            model=model_name,
            quality_mode=quality_mode,
            prompt=prompt_pack["provider_prompt"],
            negative_prompt=prompt_pack["negative_prompt"],
            view_type=data.view_type,
            derivation_type=data.derivation_type,
            workflow_name=data.workflow_name,
            source_version_id=data.source_version_id,
            reference_material_id=data.reference_material_id,
            reference_images=ref_images,
            locked_regions=data.locked_regions,
            transparent_background=transparent_background,
            output_path=output_path,
            params=params,
        )
        result = await provider.generate(job)
        if data.view_type in {"front", "side", "back"} and result.file_path:
            result.file_path = normalize_turnaround_canvas(result.file_path)
        record.file_path = result.file_path
        record.duration = result.duration
        record.workflow_version = data.workflow_name
        record.provider_model = result.model or model_name
        record.cost_estimate = result.cost_estimate
        record.raw_response = result.raw_response
    except HTTPException:
        db.commit()
        raise
    except Exception as exc:
        record.error_message = str(exc)
        db.commit()
        db.refresh(record)
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}")

    if data.view_type == "main":
        order.status = OrderStatus.REVIEWING
    db.commit()
    db.refresh(record)
    return _generation_response(record)


@router.get("/{order_id}", response_model=list[GenerationResponse])
def list_generations(order_id: int, db: Session = Depends(get_db)):
    records = (
        db.query(GenerationRecord)
        .filter(GenerationRecord.order_id == order_id)
        .order_by(GenerationRecord.created_at.desc())
        .all()
    )
    return [_generation_response(record) for record in records]


@router.post("/batch-multiview", response_model=list[GenerationResponse])
async def batch_multiview(data: GenerateRequest, db: Session = Depends(get_db)):
    order = _get_order(data.order_id, db)
    if not data.source_version_id:
        raise HTTPException(status_code=400, detail="Please confirm a main version first.")
    source_gen = db.query(GenerationRecord).filter(GenerationRecord.id == data.source_version_id).first()
    if not source_gen or not source_gen.file_path:
        raise HTTPException(status_code=400, detail="Source generation file does not exist.")
    if order.confirmed_version_id != source_gen.id:
        raise HTTPException(
            status_code=400,
            detail="Please confirm the main sample version before generating front/side/back views.",
        )

    settings = load_settings()
    provider_id = _resolve_provider(data.provider)
    quality_mode = data.quality_mode or get_default_quality()
    model_name = data.model or data.model_name or str(settings.get("default_model") or "")
    transparent_background = (
        data.transparent_background
        if data.transparent_background is not None
        else bool(settings.get("transparent_background", True))
    )
    provider = get_provider(provider_id)
    await _ensure_provider_ready(provider_id, provider)
    brief = _resolve_generation_brief(order, data, quality_mode, db)
    source_material_ids = data.source_material_ids or _source_material_ids_from_brief(brief)
    results: list[GenerationResponse] = []

    for view_type in ["front", "side", "back"]:
        view_request = data.model_copy(update={"view_type": view_type, "derivation_type": view_type})
        prompt_pack = _build_prompt_pack(order, brief, view_request, provider_id, quality_mode)
        output_dir = GENERATED_DIR / str(data.order_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = str(output_dir / f"{view_type}_{uuid.uuid4().hex[:8]}.png")

        record = GenerationRecord(
            order_id=data.order_id,
            source_version_id=data.source_version_id,
            derivation_type=view_type,
            view_type=ViewType(view_type),
            provider=provider_id,
            provider_model=model_name,
            quality_mode=quality_mode,
            prompt=prompt_pack["provider_prompt"],
            negative_prompt=prompt_pack["negative_prompt"],
            model_name=model_name or "pending",
            license_status="unreviewed",
            brief_id=brief.id if brief else None,
            prompt_builder_version=prompt_pack["version"],
            final_prompt=prompt_pack["final_prompt"],
            provider_prompt=prompt_pack["provider_prompt"],
            source_material_ids=json.dumps(source_material_ids, ensure_ascii=False),
            quality_status="unreviewed",
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        try:
            job = GenerateJob(
                order_id=data.order_id,
                provider=provider_id,
                model=model_name,
                quality_mode=quality_mode,
                prompt=prompt_pack["provider_prompt"],
                negative_prompt=prompt_pack["negative_prompt"],
                view_type=view_type,
                derivation_type=view_type,
                workflow_name="multiview.json",
                source_version_id=data.source_version_id,
                reference_images=[source_gen.file_path],
                transparent_background=transparent_background,
                output_path=filepath,
                params=data.overrides or {},
            )
            result = await provider.generate(job)
            if result.file_path:
                result.file_path = normalize_turnaround_canvas(result.file_path)
            record.file_path = result.file_path
            record.duration = result.duration
            record.provider_model = result.model or model_name
            record.raw_response = result.raw_response
        except Exception as exc:
            record.error_message = str(exc)

        db.commit()
        db.refresh(record)
        results.append(_generation_response(record))

    return results


@router.post("/{generation_id}/confirm")
def confirm_version(generation_id: int, db: Session = Depends(get_db)):
    record = db.query(GenerationRecord).filter(GenerationRecord.id == generation_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Generation record not found.")
    if not record.file_path:
        raise HTTPException(status_code=400, detail="This generation has no image output.")
    order = _get_order(record.order_id, db)
    order.confirmed_version_id = record.id
    db.commit()
    return {"message": "Version confirmed", "confirmed_version_id": record.id}


def _get_order(order_id: int, db: Session) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


def _validate_view_type(view_type: str) -> None:
    if view_type not in [item.value for item in ViewType]:
        raise HTTPException(status_code=400, detail=f"Invalid view type: {view_type}")


def _resolve_provider(provider: str) -> str:
    provider_id = provider or get_default_provider()
    if provider_id not in {"comfyui", "openai", "replicate", "agnes", "mock"}:
        return get_default_provider()
    return provider_id


async def _ensure_provider_ready(provider_id: str, provider) -> None:
    if provider_id not in {"openai", "replicate", "agnes"}:
        return
    health = await provider.health_check()
    if not health.configured:
        raise HTTPException(
            status_code=400,
            detail=f"{provider.name} is not configured. Add the API key/token in Settings first.",
        )
    if not health.available:
        raise HTTPException(status_code=400, detail=f"{provider.name} unavailable: {health.message}")


def _resolve_generation_brief(
    order: Order,
    data: GenerateRequest,
    quality_mode: str,
    db: Session,
) -> Brief | None:
    query = db.query(Brief).filter(Brief.order_id == order.id)
    brief: Brief | None = None
    if data.brief_id:
        brief = query.filter(Brief.id == data.brief_id).first()
    elif order.confirmed_brief_id:
        brief = query.filter(Brief.id == order.confirmed_brief_id).first()
    if not brief:
        brief = query.filter(Brief.is_confirmed == True).order_by(Brief.version.desc()).first()  # noqa: E712
    if not brief and quality_mode == "draft":
        return None
    if not brief:
        raise HTTPException(
            status_code=400,
            detail="Sample/final generation requires a confirmed structured brief. Analyze and confirm the brief first.",
        )
    if data.use_confirmed_brief_only and quality_mode in {"sample", "final"} and not brief.is_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Sample/final generation requires a confirmed brief.",
        )
    return brief


def _build_prompt_pack(
    order: Order,
    brief: Brief | None,
    data: GenerateRequest,
    provider_id: str,
    quality_mode: str,
) -> dict[str, str]:
    if brief:
        structured = json.loads(brief.structured_content or "{}")
        return build_provider_prompt(
            structured,
            provider=provider_id,
            view_type=data.view_type,
            quality_mode=quality_mode,
            modification_prompt=data.modification_prompt or "",
            locked_regions=data.locked_regions or "",
        )
    prompt_text, negative = build_plush_prompt(
        order,
        data.view_type,
        data.modification_prompt or "",
        data.locked_regions or "",
        quality_mode,
    )
    return {
        "version": "legacy-order-prompt",
        "final_prompt": prompt_text,
        "provider_prompt": prompt_text,
        "negative_prompt": negative,
    }


def _source_material_ids_from_brief(brief: Brief | None) -> list[int]:
    if not brief or not brief.source_material_ids:
        return []
    try:
        values = json.loads(brief.source_material_ids)
        return [int(item) for item in values]
    except Exception:
        return []


def _reference_images(
    order_id: int,
    data: GenerateRequest,
    source_material_ids: list[int],
    db: Session,
) -> list[str]:
    ref_images: list[str] = []
    if data.reference_material_id:
        material = db.query(Material).filter(Material.id == data.reference_material_id).first()
        if material and material.file_path:
            ref_images.append(material.file_path)
    elif source_material_ids:
        materials = (
            db.query(Material)
            .filter(Material.id.in_(source_material_ids))
            .order_by(Material.created_at.asc())
            .all()
        )
        ref_images.extend([material.file_path for material in materials if material.file_path])
    else:
        material = (
            db.query(Material)
            .filter(
                Material.order_id == order_id,
                Material.type.in_([MaterialType.REFERENCE, MaterialType.PHOTO, MaterialType.SKETCH]),
            )
            .order_by(Material.created_at.desc())
            .first()
        )
        if material and material.file_path:
            ref_images.append(material.file_path)

    if data.source_version_id:
        source = db.query(GenerationRecord).filter(GenerationRecord.id == data.source_version_id).first()
        if source and source.file_path:
            ref_images.insert(0, source.file_path)
    return ref_images


def _save_mask_data_url(mask_data_url: str, output_dir, view_type: str) -> str:
    if not mask_data_url:
        return ""
    prefix = "base64,"
    if prefix not in mask_data_url:
        return ""
    try:
        encoded = mask_data_url.split(prefix, 1)[1]
        mask_bytes = base64.b64decode(encoded)
        mask_path = output_dir / f"{view_type}_mask_{uuid.uuid4().hex[:8]}.png"
        mask_path.write_bytes(mask_bytes)
        return str(mask_path)
    except Exception:
        return ""
