"""Order management API."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.order import Order, OrderStatus

router = APIRouter(prefix="/api/orders", tags=["orders"])


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


class OrderUpdate(OrderCreate):
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
    brief_status: str = "not_started"
    confirmed_brief_id: Optional[int] = None
    source_summary: str = ""
    customer_question_status: str = "not_needed"
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


def _order_response(order: Order) -> OrderResponse:
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
        brief_status=order.brief_status or "not_started",
        confirmed_brief_id=order.confirmed_brief_id,
        source_summary=order.source_summary or "",
        customer_question_status=order.customer_question_status or "not_needed",
        created_at=str(order.created_at),
        updated_at=str(order.updated_at),
    )


@router.get("/", response_model=list[OrderResponse])
def list_orders(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Order).order_by(Order.created_at.desc())
    if status:
        query = query.filter(Order.status == status)
    return [_order_response(order) for order in query.all()]


@router.post("/", response_model=OrderResponse)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    order = Order(
        order_number=f"PT-{uuid.uuid4().hex[:8].upper()}",
        **data.model_dump(exclude_none=True),
        status=OrderStatus.DRAFT,
        brief_status="not_started",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _order_response(order)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_response(order)


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, data: OrderUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(order, key, value)
    db.commit()
    db.refresh(order)
    return _order_response(order)


@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return {"message": "Order deleted"}
