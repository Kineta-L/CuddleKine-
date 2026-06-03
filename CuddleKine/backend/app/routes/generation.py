"""生成管理 API — Phase 1: Provider Registry + 多模型选择"""
import json
import uuid
import random
import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models.generation import GenerationRecord, ViewType
from ..models.order import Order, OrderStatus
from ..models.material import Material, MaterialType
from ..models.brief import Brief
from ..config import GENERATED_DIR, GENERATION_PROVIDER as DEFAULT_PROVIDER
from ..prompts import build_plush_prompt
from ..services.providers.base import GenerateJob
from ..services.providers.registry import get_provider, list_providers, register_provider
from ..services.providers.comfyui_provider import ComfyUIProvider
from ..services.providers.openai_provider import OpenAIProvider
from ..services.providers.replicate_provider import ReplicateProvider
from ..services.providers.mock_provider import MockProvider
from ..services.settings_service import get_default_provider, get_default_quality, load_settings

router = APIRouter(prefix="/api/generation", tags=["图片生成"])

# ── Provider 注册 ──────────────────────────────────

register_provider(ComfyUIProvider())
register_provider(OpenAIProvider())
register_provider(ReplicateProvider())
register_provider(MockProvider())


# ── Pydantic Schemas ───────────────────────────────

class GenerateRequest(BaseModel):
    order_id: int
    provider: str = ""                     # 空=默认 ; comfyui | openai | replicate | mock
    model: str = ""                         # 具体模型名
    quality_mode: str = ""                  # 空=设置默认 ; draft | sample | final
    workflow_name: str = "main_view.json"
    view_type: str = "main"
    derivation_type: str = "main_view_candidate"
    source_version_id: Optional[int] = None
    locked_regions: Optional[str] = None
    modification_prompt: Optional[str] = None
    model_name: Optional[str] = None        # 旧字段，兼容
    reference_material_id: Optional[int] = None
    transparent_background: Optional[bool] = None
    overrides: Optional[dict] = None


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
    created_at: str

    model_config = {"from_attributes": True}


# ── API 路由 ──────────────────────────────────────

@router.get("/providers", summary="获取可用模型供应商列表")
async def api_providers():
    """返回所有已注册 provider 的信息（含健康状态）"""
    infos = list_providers()
    # 异步检测每个 provider 的健康状态
    for info in infos:
        try:
            p = get_provider(info.id)
            h = await p.health_check()
            info.configured = h.configured
        except Exception:
            info.configured = False
    return [{
        "id": i.id,
        "name": i.name,
        "enabled": i.enabled,
        "configured": i.configured,
        "supports_text_to_image": i.supports_text_to_image,
        "supports_image_to_image": i.supports_image_to_image,
        "supports_inpaint": i.supports_inpaint,
        "supports_transparent_background": i.supports_transparent_background,
        "models": i.models,
    } for i in infos]


@router.post("/generate", response_model=GenerationResponse)
async def generate_image(data: GenerateRequest, db: Session = Depends(get_db)):
    """提交图片生成任务 — 支持多 provider"""
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if data.view_type not in [v.value for v in ViewType]:
        raise HTTPException(status_code=400, detail=f"无效的视图类型: {data.view_type}")

    # 确定 provider
    settings = load_settings()
    provider_id = data.provider or get_default_provider()
    if provider_id not in ("comfyui", "openai", "replicate", "mock"):
        provider_id = get_default_provider()
    quality_mode = data.quality_mode or get_default_quality()
    model_name = data.model or data.model_name or str(settings.get("default_model") or "")
    transparent_background = (
        data.transparent_background
        if data.transparent_background is not None
        else bool(settings.get("transparent_background", True))
    )
    provider = get_provider(provider_id)
    if provider_id in ("openai", "replicate"):
        health = await provider.health_check()
        if not health.configured:
            raise HTTPException(
                status_code=400,
                detail=f"{provider.name} 未配置 API Key/Token，请先在顶部“设置”里填写后再生成。",
            )
        if not health.available:
            raise HTTPException(
                status_code=400,
                detail=f"{provider.name} 认证失败或暂不可用：{health.message}",
            )

    # 获取参考素材
    ref_images: list[str] = []
    if data.reference_material_id:
        mat = db.query(Material).filter(Material.id == data.reference_material_id).first()
        if mat and mat.file_path:
            ref_images.append(mat.file_path)
    else:
        # 自动选取最新参考图
        mat = db.query(Material).filter(
            Material.order_id == data.order_id,
            Material.type.in_([MaterialType.REFERENCE, MaterialType.PHOTO, MaterialType.SKETCH]),
        ).order_by(Material.created_at.desc()).first()
        if mat and mat.file_path:
            ref_images.append(mat.file_path)

    # 获取来源版本图片（多视图时）
    if data.source_version_id:
        src = db.query(GenerationRecord).filter(
            GenerationRecord.id == data.source_version_id
        ).first()
        if src and src.file_path:
            ref_images.insert(0, src.file_path)

    # 构建 prompt（使用统一模板系统）
    prompt_text, negative = build_plush_prompt(
        order, data.view_type,
        data.modification_prompt or "",
        data.locked_regions or "",
        quality_mode,
    )

    # 输出路径
    output_dir = GENERATED_DIR / str(data.order_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / f"{data.view_type}_{uuid.uuid4().hex[:8]}.png")

    # 创建记录
    record = GenerationRecord(
        order_id=data.order_id,
        source_version_id=data.source_version_id,
        derivation_type=data.derivation_type,
        view_type=ViewType(data.view_type),
        locked_regions=data.locked_regions,
        provider=provider_id,
        provider_model=model_name,
        quality_mode=quality_mode,
        prompt=prompt_text,
        negative_prompt=negative,
        reference_material_id=data.reference_material_id,
        model_name=model_name or "待评测",
        license_status="unreviewed",
        raw_params=json.dumps(data.overrides or {}, ensure_ascii=False),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # 执行生成
    try:
        job = GenerateJob(
            order_id=data.order_id,
            provider=provider_id,
            model=model_name,
            quality_mode=quality_mode,
            prompt=prompt_text,
            negative_prompt=negative,
            view_type=data.view_type,
            derivation_type=data.derivation_type,
            workflow_name=data.workflow_name,
            source_version_id=data.source_version_id,
            reference_material_id=data.reference_material_id,
            reference_images=ref_images,
            locked_regions=data.locked_regions,
            transparent_background=transparent_background,
            output_path=output_path,
            params=data.overrides or {},
        )

        result = await provider.generate(job)

        record.file_path = result.file_path
        record.duration = result.duration
        record.workflow_version = data.workflow_name
        record.provider_model = result.model or model_name
        record.cost_estimate = result.cost_estimate
        record.raw_response = result.raw_response

    except HTTPException:
        db.commit()
        raise
    except Exception as e:
        record.error_message = str(e)
        db.commit()
        db.refresh(record)
        raise HTTPException(status_code=500, detail=f"生成失败: {e}")

    if data.view_type == "main":
        order.status = OrderStatus.REVIEWING
    db.commit()
    db.refresh(record)

    return GenerationResponse(
        id=record.id, order_id=record.order_id,
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
        created_at=str(record.created_at),
    )


@router.get("/{order_id}", response_model=list[GenerationResponse])
def list_generations(order_id: int, db: Session = Depends(get_db)):
    """获取订单的所有生成记录"""
    records = (
        db.query(GenerationRecord)
        .filter(GenerationRecord.order_id == order_id)
        .order_by(GenerationRecord.created_at.desc())
        .all()
    )
    return [
        GenerationResponse(
            id=r.id, order_id=r.order_id,
            provider=r.provider or "", provider_model=r.provider_model or "",
            quality_mode=r.quality_mode or "sample",
            source_version_id=r.source_version_id,
            derivation_type=r.derivation_type,
            view_type=r.view_type.value,
            file_path=r.file_path,
            locked_regions=r.locked_regions,
            model_name=r.model_name,
            license_status=r.license_status,
            workflow_version=r.workflow_version,
            duration=r.duration,
            error_message=r.error_message,
            created_at=str(r.created_at),
        ) for r in records
    ]


@router.post("/batch-multiview", response_model=list[GenerationResponse])
async def batch_multiview(data: GenerateRequest, db: Session = Depends(get_db)):
    """一键生成三视图"""
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not data.source_version_id:
        raise HTTPException(status_code=400, detail="请先确认一个主视图版本")

    source_gen = db.query(GenerationRecord).filter(
        GenerationRecord.id == data.source_version_id
    ).first()
    if not source_gen or not source_gen.file_path:
        raise HTTPException(status_code=400, detail="源版本文件不存在")

    settings = load_settings()
    provider_id = data.provider or get_default_provider()
    if provider_id not in ("comfyui", "openai", "replicate", "mock"):
        provider_id = get_default_provider()
    quality_mode = data.quality_mode or get_default_quality()
    model_name = data.model or data.model_name or str(settings.get("default_model") or "")
    transparent_background = (
        data.transparent_background
        if data.transparent_background is not None
        else bool(settings.get("transparent_background", True))
    )
    provider = get_provider(provider_id)
    if provider_id in ("openai", "replicate"):
        health = await provider.health_check()
        if not health.configured:
            raise HTTPException(
                status_code=400,
                detail=f"{provider.name} 未配置 API Key/Token，请先在顶部“设置”里填写后再生成。",
            )
        if not health.available:
            raise HTTPException(
                status_code=400,
                detail=f"{provider.name} 认证失败或暂不可用：{health.message}",
            )
    results = []

    for view_type in ["front", "side", "back"]:
        output_dir = GENERATED_DIR / str(data.order_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = str(output_dir / f"{view_type}_{uuid.uuid4().hex[:8]}.png")

        prompt_text, negative = build_plush_prompt(order, view_type, quality_mode=quality_mode)

        record = GenerationRecord(
            order_id=data.order_id,
            source_version_id=data.source_version_id,
            derivation_type=view_type,
            view_type=ViewType(view_type),
            provider=provider_id,
            provider_model=model_name,
            quality_mode=quality_mode,
            prompt=prompt_text,
            negative_prompt=negative,
            model_name=data.model_name or "待评测",
            license_status="unreviewed",
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
                prompt=prompt_text,
                negative_prompt=negative,
                view_type=view_type,
                derivation_type=view_type,
                workflow_name="multiview.json",
                source_version_id=data.source_version_id,
                reference_images=[source_gen.file_path] if source_gen.file_path else [],
                transparent_background=transparent_background,
                output_path=filepath,
                params=data.overrides or {},
            )
            result = await provider.generate(job)
            record.file_path = result.file_path
            record.duration = result.duration
            record.provider_model = result.model
        except Exception as e:
            record.error_message = str(e)

        db.commit()
        db.refresh(record)

        results.append(GenerationResponse(
            id=record.id, order_id=record.order_id,
            provider=record.provider or "", provider_model=record.provider_model or "",
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
            created_at=str(record.created_at),
        ))

    return results


@router.post("/{generation_id}/confirm")
def confirm_version(generation_id: int, db: Session = Depends(get_db)):
    """确认版本"""
    record = db.query(GenerationRecord).filter(
        GenerationRecord.id == generation_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    if not record.file_path:
        raise HTTPException(status_code=400, detail="该生成记录没有图片，不能确认")

    order = db.query(Order).filter(Order.id == record.order_id).first()
    order.confirmed_version_id = record.id
    db.commit()

    return {"message": "版本已确认", "confirmed_version_id": record.id}
