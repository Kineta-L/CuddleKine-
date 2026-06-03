"""Brief 管理 API"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models.brief import Brief
from ..models.material import Material
from ..models.order import Order, OrderStatus
from ..services.brief_agent import analyze_materials, merge_customer_replies

router = APIRouter(prefix="/api/briefs", tags=["需求整理"])


class BriefResponse(BaseModel):
    id: int
    order_id: int
    version: int
    is_confirmed: bool
    structured_content: Optional[str]
    missing_info: Optional[str]
    conflicts: Optional[str]
    customer_replies: Optional[str]
    summary: str = ""
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class CustomerReplyRequest(BaseModel):
    replies: dict  # {"character_type": "三色猫", "colors": "黑白橘"}


@router.post("/{order_id}/analyze", response_model=BriefResponse)
def create_brief(order_id: int, db: Session = Depends(get_db)):
    """分析订单素材，生成结构化 brief"""
    # 检查订单存在
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 获取素材
    materials = db.query(Material).filter(Material.order_id == order_id).all()
    if not materials:
        raise HTTPException(status_code=400, detail="请先导入素材")

    material_dicts = [
        {
            "type": m.type.value,
            "ocr_text": m.ocr_text,
            "notes": m.notes,
        }
        for m in materials
    ]

    # 分析
    result = analyze_materials(material_dicts)

    # 已确认版本号
    latest = (
        db.query(Brief)
        .filter(Brief.order_id == order_id)
        .order_by(Brief.version.desc())
        .first()
    )
    new_version = (latest.version + 1) if latest else 1

    brief = Brief(
        order_id=order_id,
        version=new_version,
        structured_content=json.dumps(result["structured"], ensure_ascii=False),
        missing_info=json.dumps(result["missing_info"], ensure_ascii=False),
        conflicts=json.dumps(result["conflicts"], ensure_ascii=False),
    )
    db.add(brief)

    # 更新订单状态
    order.status = OrderStatus.BRIEF_PENDING
    db.commit()
    db.refresh(brief)

    return BriefResponse(
        id=brief.id,
        order_id=brief.order_id,
        version=brief.version,
        is_confirmed=brief.is_confirmed,
        structured_content=brief.structured_content,
        missing_info=brief.missing_info,
        conflicts=brief.conflicts,
        customer_replies=brief.customer_replies,
        summary=result["summary"],
        created_at=str(brief.created_at),
        updated_at=str(brief.updated_at),
    )


@router.put("/{brief_id}/reply", response_model=BriefResponse)
def submit_reply(brief_id: int, data: CustomerReplyRequest, db: Session = Depends(get_db)):
    """提交客户答复，合并到 structured"""
    brief = db.query(Brief).filter(Brief.id == brief_id).first()
    if not brief:
        raise HTTPException(status_code=404, detail="Brief 不存在")

    structured = json.loads(brief.structured_content or "{}")
    merged = merge_customer_replies(structured, data.replies)

    brief.structured_content = json.dumps(merged, ensure_ascii=False)
    brief.customer_replies = json.dumps(data.replies, ensure_ascii=False)
    brief.is_confirmed = True

    # 同步关键字段到订单（安全类型转换）
    order = db.query(Order).filter(Order.id == brief.order_id).first()
    if order:
        for field in ["character_type", "target_height", "colors",
                       "material_preference", "accessories", "key_features"]:
            if field in merged:
                value = merged[field]
                if field == "target_height":
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        continue  # 跳过无法转换的值
                setattr(order, field, value)
        order.status = OrderStatus.BRIEF_CONFIRMED

    db.commit()
    db.refresh(brief)

    return BriefResponse(
        id=brief.id,
        order_id=brief.order_id,
        version=brief.version,
        is_confirmed=brief.is_confirmed,
        structured_content=brief.structured_content,
        missing_info=brief.missing_info,
        conflicts=brief.conflicts,
        customer_replies=brief.customer_replies,
        summary="客户答复已合并，brief 已确认。",
        created_at=str(brief.created_at),
        updated_at=str(brief.updated_at),
    )


@router.get("/{order_id}", response_model=list[BriefResponse])
def list_briefs(order_id: int, db: Session = Depends(get_db)):
    """获取订单的所有 brief 版本"""
    briefs = (
        db.query(Brief)
        .filter(Brief.order_id == order_id)
        .order_by(Brief.version.desc())
        .all()
    )
    return [
        BriefResponse(
            id=b.id,
            order_id=b.order_id,
            version=b.version,
            is_confirmed=b.is_confirmed,
            structured_content=b.structured_content,
            missing_info=b.missing_info,
            conflicts=b.conflicts,
            customer_replies=b.customer_replies,
            summary="",
            created_at=str(b.created_at),
            updated_at=str(b.updated_at),
        )
        for b in briefs
    ]
