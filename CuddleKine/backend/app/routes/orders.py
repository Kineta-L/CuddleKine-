"""订单管理 API"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from ..database import get_db
from ..models.order import Order, OrderStatus

router = APIRouter(prefix="/api/orders", tags=["订单管理"])


# ========== Pydantic Schemas ==========

class OrderCreate(BaseModel):
    customer_name: Optional[str] = None
    character_type: Optional[str] = None
    target_height: Optional[float] = None
    main_proportions: Optional[str] = None
    colors: Optional[str] = None
    material_preference: Optional[str] = None
    accessories: Optional[str] = None
    key_features: Optional[str] = None
    allowed_simplifications: Optional[str] = None
    pending_items: Optional[str] = None
    craft_notes: Optional[str] = None


class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    character_type: Optional[str] = None
    target_height: Optional[float] = None
    main_proportions: Optional[str] = None
    colors: Optional[str] = None
    material_preference: Optional[str] = None
    accessories: Optional[str] = None
    key_features: Optional[str] = None
    allowed_simplifications: Optional[str] = None
    pending_items: Optional[str] = None
    craft_notes: Optional[str] = None
    status: Optional[OrderStatus] = None


class OrderResponse(BaseModel):
    id: int
    order_number: str
    customer_name: Optional[str]
    character_type: Optional[str]
    target_height: Optional[float]
    main_proportions: Optional[str]
    colors: Optional[str]
    material_preference: Optional[str]
    accessories: Optional[str]
    key_features: Optional[str]
    allowed_simplifications: Optional[str]
    pending_items: Optional[str]
    craft_notes: Optional[str]
    status: OrderStatus
    confirmed_version_id: Optional[int]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ========== Routes ==========

@router.get("/", response_model=list[OrderResponse])
def list_orders(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取订单列表，可按状态过滤"""
    query = db.query(Order).order_by(Order.created_at.desc())
    if status:
        query = query.filter(Order.status == status)
    orders = query.all()
    return [
        OrderResponse(
            id=o.id,
            order_number=o.order_number,
            customer_name=o.customer_name,
            character_type=o.character_type,
            target_height=o.target_height,
            main_proportions=o.main_proportions,
            colors=o.colors,
            material_preference=o.material_preference,
            accessories=o.accessories,
            key_features=o.key_features,
            allowed_simplifications=o.allowed_simplifications,
            pending_items=o.pending_items,
            craft_notes=o.craft_notes,
            status=o.status,
            confirmed_version_id=o.confirmed_version_id,
            created_at=str(o.created_at),
            updated_at=str(o.updated_at),
        )
        for o in orders
    ]


@router.post("/", response_model=OrderResponse)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    """创建新订单"""
    order = Order(
        order_number=f"PT-{uuid.uuid4().hex[:8].upper()}",
        **data.model_dump(exclude_none=True),
        status=OrderStatus.DRAFT,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        customer_name=order.customer_name,
        character_type=order.character_type,
        target_height=order.target_height,
        main_proportions=order.main_proportions,
        colors=order.colors,
        material_preference=order.material_preference,
        accessories=order.accessories,
        key_features=order.key_features,
        allowed_simplifications=order.allowed_simplifications,
        pending_items=order.pending_items,
        craft_notes=order.craft_notes,
        status=order.status,
        confirmed_version_id=order.confirmed_version_id,
        created_at=str(order.created_at),
        updated_at=str(order.updated_at),
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """获取订单详情"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        customer_name=order.customer_name,
        character_type=order.character_type,
        target_height=order.target_height,
        main_proportions=order.main_proportions,
        colors=order.colors,
        material_preference=order.material_preference,
        accessories=order.accessories,
        key_features=order.key_features,
        allowed_simplifications=order.allowed_simplifications,
        pending_items=order.pending_items,
        craft_notes=order.craft_notes,
        status=order.status,
        confirmed_version_id=order.confirmed_version_id,
        created_at=str(order.created_at),
        updated_at=str(order.updated_at),
    )


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, data: OrderUpdate, db: Session = Depends(get_db)):
    """更新订单"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(order, key, value)
    db.commit()
    db.refresh(order)
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        customer_name=order.customer_name,
        character_type=order.character_type,
        target_height=order.target_height,
        main_proportions=order.main_proportions,
        colors=order.colors,
        material_preference=order.material_preference,
        accessories=order.accessories,
        key_features=order.key_features,
        allowed_simplifications=order.allowed_simplifications,
        pending_items=order.pending_items,
        craft_notes=order.craft_notes,
        status=order.status,
        confirmed_version_id=order.confirmed_version_id,
        created_at=str(order.created_at),
        updated_at=str(order.updated_at),
    )


@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """删除订单"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    db.delete(order)
    db.commit()
    return {"message": "订单已删除"}
