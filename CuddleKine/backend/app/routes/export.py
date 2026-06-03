"""导出 API"""
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models.order import Order, OrderStatus
from ..models.brief import Brief
from ..models.generation import GenerationRecord
from ..config import OUTPUT_DIR
from ..services.export_service import export_design_board, export_factory_package

router = APIRouter(prefix="/api/export", tags=["导出"])


class ExportResponse(BaseModel):
    board_path: str
    message: str


class PackageResponse(BaseModel):
    package_path: str
    file_count: int
    message: str


@router.post("/{order_id}/board", response_model=ExportResponse)
def export_order_board(order_id: int, db: Session = Depends(get_db)):
    """导出客户确认板"""
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

    # 主视图
    main_rec = (
        db.query(GenerationRecord)
        .filter(GenerationRecord.order_id == order_id, GenerationRecord.view_type == "main")
        .order_by(GenerationRecord.created_at.desc())
        .first()
    )
    main_path = main_rec.file_path if main_rec else ""

    # 多视图
    views = {}
    for view_type in ["front", "side", "back"]:
        record = (
            db.query(GenerationRecord)
            .filter(
                GenerationRecord.order_id == order_id,
                GenerationRecord.view_type == view_type,
            )
            .order_by(GenerationRecord.created_at.desc())
            .first()
        )
        if record and record.file_path:
            views[view_type] = record.file_path

    order_info = {
        "customer_name": order.customer_name or "",
        "character_type": order.character_type or "",
        "target_height": order.target_height,
        "colors": order.colors or "",
        "material_preference": order.material_preference or "",
        "accessories": order.accessories or "",
        "key_features": order.key_features or "",
    }

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

    return ExportResponse(board_path=board_path, message="客户确认板已导出")


@router.post("/{order_id}/package", response_model=PackageResponse)
def export_order_package(order_id: int, db: Session = Depends(get_db)):
    """导出工厂打样资料包 ZIP"""
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
    for vt in ["front", "side", "back"]:
        r = (
            db.query(GenerationRecord)
            .filter(GenerationRecord.order_id == order_id, GenerationRecord.view_type == vt)
            .order_by(GenerationRecord.created_at.desc())
            .first()
        )
        if r and r.file_path:
            views[vt] = r.file_path

    order_info = {
        "customer_name": order.customer_name or "",
        "character_type": order.character_type or "",
        "target_height": order.target_height,
        "colors": order.colors or "",
        "material_preference": order.material_preference or "",
        "accessories": order.accessories or "",
        "key_features": order.key_features or "",
    }

    # 先生成确认板
    board_path = export_design_board(
        order_id=order_id,
        order_number=order.order_number,
        brief=brief_data,
        views=views,
        main_path=main_path,
        order_info=order_info,
    )

    # 再打包 ZIP
    package_path = export_factory_package(
        order_id=order_id,
        order_number=order.order_number,
        brief=brief_data,
        views=views,
        main_path=main_path,
        board_path=board_path,
        order_info=order_info,
    )

    order.status = OrderStatus.EXPORTED
    db.commit()

    # 统计文件数
    import zipfile
    count = 0
    with zipfile.ZipFile(package_path, "r") as zf:
        count = len(zf.namelist())

    return PackageResponse(
        package_path=package_path,
        file_count=count,
        message=f"工厂打样资料包已导出，含 {count} 个文件",
    )
