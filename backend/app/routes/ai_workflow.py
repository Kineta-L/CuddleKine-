"""AI application workflow endpoints."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.brief import Brief
from ..models.material import Material
from ..models.order import Order
from ..services.material_understanding_agent import analyze_materials, apply_material_analysis
from ..services.prompt_builder import build_provider_prompt
from .briefs import brief_response, confirm_brief_in_db, create_brief_for_order

router = APIRouter(prefix="/api", tags=["ai-workflow"])


class ConfirmBriefBody(BaseModel):
    edits: dict[str, Any] = {}


class PromptPreviewBody(BaseModel):
    order_id: int
    brief_id: int | None = None
    provider: str = "openai"
    view_type: str = "main"
    quality_mode: str = "sample"
    modification_prompt: str = ""
    locked_regions: str = ""


@router.post("/orders/{order_id}/analyze-materials")
def analyze_order_materials(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    materials = db.query(Material).filter(Material.order_id == order_id).all()
    if not materials:
        raise HTTPException(status_code=400, detail="Please upload materials before analysis.")

    result = analyze_materials(materials)
    for material, material_result in zip(materials, result.get("observations") or []):
        apply_material_analysis(material, material_result)
    order.source_summary = str(result.get("source_summary") or "")
    order.brief_status = "analyzing"
    db.commit()
    return result


@router.post("/orders/{order_id}/briefs/generate")
def generate_order_brief(order_id: int, db: Session = Depends(get_db)):
    brief = create_brief_for_order(order_id, db)
    return brief_response(brief, "Structured brief generated.")


@router.post("/orders/{order_id}/briefs/{brief_id}/confirm")
def confirm_order_brief(
    order_id: int,
    brief_id: int,
    body: ConfirmBriefBody,
    db: Session = Depends(get_db),
):
    brief = confirm_brief_in_db(brief_id, body.edits, db)
    if brief.order_id != order_id:
        raise HTTPException(status_code=400, detail="Brief does not belong to this order.")
    return brief_response(brief, "Brief confirmed.")


@router.post("/orders/{order_id}/questions/generate")
def generate_questions(order_id: int, db: Session = Depends(get_db)):
    brief = (
        db.query(Brief)
        .filter(Brief.order_id == order_id)
        .order_by(Brief.version.desc())
        .first()
    )
    if not brief:
        raise HTTPException(status_code=404, detail="No brief found for this order.")
    return {
        "order_id": order_id,
        "brief_id": brief.id,
        "questions": json.loads(brief.pending_questions or "[]"),
        "risk_notes": json.loads(brief.risk_notes or "[]"),
    }


@router.post("/prompts/preview")
def prompt_preview(body: PromptPreviewBody, db: Session = Depends(get_db)):
    brief = _resolve_brief(body.order_id, body.brief_id, db)
    structured = json.loads(brief.structured_content or "{}")
    prompt = build_provider_prompt(
        structured,
        provider=body.provider,
        view_type=body.view_type,
        quality_mode=body.quality_mode,
        modification_prompt=body.modification_prompt,
        locked_regions=body.locked_regions,
    )
    return {
        "order_id": body.order_id,
        "brief_id": brief.id,
        "is_confirmed": bool(brief.is_confirmed),
        **prompt,
    }


def _resolve_brief(order_id: int, brief_id: int | None, db: Session) -> Brief:
    query = db.query(Brief).filter(Brief.order_id == order_id)
    if brief_id:
        brief = query.filter(Brief.id == brief_id).first()
    else:
        brief = query.filter(Brief.is_confirmed == True).order_by(Brief.version.desc()).first()  # noqa: E712
        if not brief:
            brief = query.order_by(Brief.version.desc()).first()
    if not brief:
        raise HTTPException(status_code=404, detail="No brief found for this order.")
    return brief
