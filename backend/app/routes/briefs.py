"""Structured brief management API."""
from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.brief import Brief
from ..models.material import Material
from ..models.order import Order, OrderStatus
from ..services.brief_builder import (
    build_structured_brief,
    merge_designer_edits,
    missing_info,
    sync_order_from_brief,
)
from ..services.material_understanding_agent import (
    analyze_materials,
    apply_material_analysis,
)

router = APIRouter(prefix="/api/briefs", tags=["briefs"])


class BriefResponse(BaseModel):
    id: int
    order_id: int
    version: int
    is_confirmed: bool
    structured_content: Optional[str]
    missing_info: Optional[str]
    conflicts: Optional[str]
    customer_replies: Optional[str]
    source_material_ids: str = ""
    source_type: str = ""
    pending_questions: str = ""
    risk_notes: str = ""
    designer_edits: str = ""
    ai_model_used: str = "rule-based"
    prompt_version: str = "plush-prompt-v1"
    summary: str = ""
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class CustomerReplyRequest(BaseModel):
    replies: dict[str, Any]


class ConfirmBriefRequest(BaseModel):
    edits: dict[str, Any] = {}


def brief_response(brief: Brief, summary: str = "") -> BriefResponse:
    return BriefResponse(
        id=brief.id,
        order_id=brief.order_id,
        version=brief.version,
        is_confirmed=bool(brief.is_confirmed),
        structured_content=brief.structured_content,
        missing_info=brief.missing_info,
        conflicts=brief.conflicts,
        customer_replies=brief.customer_replies,
        source_material_ids=brief.source_material_ids or "",
        source_type=brief.source_type or "",
        pending_questions=brief.pending_questions or "",
        risk_notes=brief.risk_notes or "",
        designer_edits=brief.designer_edits or "",
        ai_model_used=brief.ai_model_used or "rule-based",
        prompt_version=brief.prompt_version or "plush-prompt-v1",
        summary=summary,
        created_at=str(brief.created_at),
        updated_at=str(brief.updated_at),
    )


def create_brief_for_order(order_id: int, db: Session) -> Brief:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    materials = db.query(Material).filter(Material.order_id == order_id).all()
    if not materials:
        raise HTTPException(status_code=400, detail="Please upload materials before analysis.")

    material_result = analyze_materials(materials)
    material_results_by_index = material_result.get("observations") or []
    for material, result in zip(materials, material_results_by_index):
        apply_material_analysis(material, result)

    structured = build_structured_brief(order, material_result)
    missing = missing_info(structured)
    questions = structured.get("pending_questions") or []
    risks = structured.get("risk_notes") or []

    latest = (
        db.query(Brief)
        .filter(Brief.order_id == order_id)
        .order_by(Brief.version.desc())
        .first()
    )
    brief = Brief(
        order_id=order_id,
        version=(latest.version + 1) if latest else 1,
        structured_content=json.dumps(structured, ensure_ascii=False),
        missing_info=json.dumps(missing, ensure_ascii=False),
        conflicts=json.dumps([], ensure_ascii=False),
        source_material_ids=json.dumps([m.id for m in materials]),
        source_type=str(material_result.get("source_type") or ""),
        pending_questions=json.dumps(questions, ensure_ascii=False),
        risk_notes=json.dumps(risks, ensure_ascii=False),
        ai_model_used=str(material_result.get("ai_model_used") or "rule-based"),
        prompt_version="plush-brief-prompt-v1",
    )
    db.add(brief)
    order.status = OrderStatus.BRIEF_PENDING
    order.brief_status = "pending"
    order.source_summary = str(material_result.get("source_summary") or "")
    order.customer_question_status = "pending" if questions else "not_needed"
    db.commit()
    db.refresh(brief)
    return brief


def confirm_brief_in_db(brief_id: int, edits: dict[str, Any], db: Session) -> Brief:
    brief = db.query(Brief).filter(Brief.id == brief_id).first()
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    order = db.query(Order).filter(Order.id == brief.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    structured = json.loads(brief.structured_content or "{}")
    merged = merge_designer_edits(structured, edits)
    risks = merged.get("risk_notes") or []
    questions = merged.get("pending_questions") or []

    brief.structured_content = json.dumps(merged, ensure_ascii=False)
    brief.designer_edits = json.dumps(edits, ensure_ascii=False)
    brief.missing_info = json.dumps(missing_info(merged), ensure_ascii=False)
    brief.pending_questions = json.dumps(questions, ensure_ascii=False)
    brief.risk_notes = json.dumps(risks, ensure_ascii=False)
    brief.is_confirmed = True
    sync_order_from_brief(order, merged)
    order.status = OrderStatus.BRIEF_CONFIRMED
    order.brief_status = "confirmed"
    order.confirmed_brief_id = brief.id
    order.customer_question_status = "answered"
    db.commit()
    db.refresh(brief)
    return brief


@router.post("/{order_id}/analyze", response_model=BriefResponse)
def create_brief(order_id: int, db: Session = Depends(get_db)):
    brief = create_brief_for_order(order_id, db)
    return brief_response(brief, "Structured brief generated from customer materials.")


@router.put("/{brief_id}/reply", response_model=BriefResponse)
def submit_reply(brief_id: int, data: CustomerReplyRequest, db: Session = Depends(get_db)):
    brief = confirm_brief_in_db(brief_id, data.replies, db)
    brief.customer_replies = json.dumps(data.replies, ensure_ascii=False)
    db.commit()
    db.refresh(brief)
    return brief_response(brief, "Customer replies merged and brief confirmed.")


@router.post("/{brief_id}/confirm", response_model=BriefResponse)
def confirm_brief(brief_id: int, data: ConfirmBriefRequest, db: Session = Depends(get_db)):
    brief = confirm_brief_in_db(brief_id, data.edits, db)
    return brief_response(brief, "Brief confirmed.")


@router.get("/{order_id}", response_model=list[BriefResponse])
def list_briefs(order_id: int, db: Session = Depends(get_db)):
    briefs = (
        db.query(Brief)
        .filter(Brief.order_id == order_id)
        .order_by(Brief.version.desc())
        .all()
    )
    return [brief_response(brief) for brief in briefs]
