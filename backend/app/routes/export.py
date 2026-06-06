"""Export API."""
import json
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.brief import Brief
from ..models.generation import GenerationRecord
from ..models.order import Order, OrderStatus
from ..services.export_service import export_design_board, export_factory_package, export_factory_pdf

router = APIRouter(prefix="/api/export", tags=["export"])


class ExportResponse(BaseModel):
    board_path: str
    message: str


class FactoryPdfResponse(BaseModel):
    factory_pdf_path: str
    message: str


class PackageResponse(BaseModel):
    package_path: str
    factory_pdf_path: str
    file_count: int
    message: str


@router.post("/{order_id}/board", response_model=ExportResponse)
def export_order_board(order_id: int, db: Session = Depends(get_db)):
    """Export customer-facing image board."""
    order, brief_data, main_path, views, order_info = _export_context(order_id, db)

    board_path = export_design_board(
        order_id=order_id,
        order_number=order.order_number,
        brief=brief_data,
        views=views,
        main_path=main_path,
        order_info=order_info,
    )

    order.status = OrderStatus.EXPORTED
    db.commit()
    return ExportResponse(board_path=board_path, message="客户确认图已导出")


@router.post("/{order_id}/factory-pdf", response_model=FactoryPdfResponse)
def export_order_factory_pdf(order_id: int, db: Session = Depends(get_db)):
    """Export factory-facing production PDF."""
    order, brief_data, main_path, views, order_info = _export_context(order_id, db)

    factory_pdf_path = export_factory_pdf(
        order_id=order_id,
        order_number=order.order_number,
        brief=brief_data,
        views=views,
        main_path=main_path,
        order_info=order_info,
    )

    order.status = OrderStatus.EXPORTED
    db.commit()
    return FactoryPdfResponse(factory_pdf_path=factory_pdf_path, message="工厂生产 PDF 已导出")


@router.post("/{order_id}/package", response_model=PackageResponse)
def export_order_package(order_id: int, db: Session = Depends(get_db)):
    """Export factory handoff ZIP."""
    order, brief_data, main_path, views, order_info = _export_context(order_id, db)

    factory_pdf_path = export_factory_pdf(
        order_id=order_id,
        order_number=order.order_number,
        brief=brief_data,
        views=views,
        main_path=main_path,
        order_info=order_info,
    )
    package_path = export_factory_package(
        order_id=order_id,
        order_number=order.order_number,
        brief=brief_data,
        views=views,
        main_path=main_path,
        order_info=order_info,
        factory_pdf_path=factory_pdf_path,
    )

    order.status = OrderStatus.EXPORTED
    db.commit()

    with zipfile.ZipFile(package_path, "r") as zf:
        count = len(zf.namelist())

    return PackageResponse(
        package_path=package_path,
        factory_pdf_path=factory_pdf_path,
        file_count=count,
        message=f"工厂资料包已导出，含 {count} 个文件",
    )


def _export_context(order_id: int, db: Session):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    brief = (
        db.query(Brief)
        .filter(Brief.order_id == order_id, Brief.is_confirmed == True)
        .order_by(Brief.version.desc())
        .first()
    )
    brief_data = json.loads(brief.structured_content) if brief and brief.structured_content else {}

    main_rec = (
        db.query(GenerationRecord)
        .filter(GenerationRecord.order_id == order_id, GenerationRecord.view_type == "main")
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    main_path = main_rec.file_path if main_rec else ""

    views = {}
    for view_type in ["front", "side", "back"]:
        record = (
            db.query(GenerationRecord)
            .filter(GenerationRecord.order_id == order_id, GenerationRecord.view_type == view_type)
            .order_by(GenerationRecord.created_at.desc())
            .first()
        )
        if record and record.file_path:
            views[view_type] = record.file_path

    order_info = {
        "customer_name": order.customer_name or "",
        "character_type": order.character_type or "",
        "target_height": order.target_height,
        "main_proportions": order.main_proportions or "",
        "colors": order.colors or "",
        "material_preference": order.material_preference or "",
        "accessories": order.accessories or "",
        "key_features": order.key_features or "",
        "allowed_simplifications": order.allowed_simplifications or "",
        "pending_items": order.pending_items or "",
        "craft_notes": order.craft_notes or "",
    }
    return order, brief_data, main_path, views, order_info
