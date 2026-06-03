"""素材管理 API"""
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models.material import Material, MaterialType
from ..config import ALLOWED_UPLOAD_EXTENSIONS, MATERIAL_DIR, MAX_UPLOAD_BYTES
from ..services.ocr_service import extract_text_from_file

router = APIRouter(prefix="/api/materials", tags=["素材管理"])


class MaterialResponse(BaseModel):
    id: int
    order_id: int
    type: str
    file_path: Optional[str]
    original_name: Optional[str]
    ocr_text: Optional[str]
    notes: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/{order_id}", response_model=list[MaterialResponse])
def list_materials(order_id: int, db: Session = Depends(get_db)):
    """获取订单的所有素材"""
    materials = (
        db.query(Material)
        .filter(Material.order_id == order_id)
        .order_by(Material.created_at.asc())
        .all()
    )
    return [
        MaterialResponse(
            id=m.id,
            order_id=m.order_id,
            type=m.type.value,
            file_path=m.file_path,
            original_name=m.original_name,
            ocr_text=m.ocr_text,
            notes=m.notes,
            created_at=str(m.created_at),
        )
        for m in materials
    ]


@router.post("/{order_id}/upload", response_model=MaterialResponse)
async def upload_material(
    order_id: int,
    file: UploadFile = File(...),
    material_type: str = Form(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """上传素材文件"""
    if material_type not in [t.value for t in MaterialType]:
        raise HTTPException(status_code=400, detail=f"无效的素材类型: {material_type}")

    original_name = Path(file.filename or "upload").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {suffix or '无扩展名'}")

    # 保存文件：使用安全文件名，避免重名覆盖和路径穿越
    order_dir = MATERIAL_DIR / str(order_id)
    order_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:12]}{suffix}"
    file_path = order_dir / safe_name
    written = 0
    try:
        with open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件过大，最大允许 {MAX_UPLOAD_BYTES // 1024 // 1024}MB",
                    )
                f.write(chunk)
    except HTTPException:
        if file_path.exists():
            file_path.unlink()
        raise

    # OCR 提取文字
    ocr_text = extract_text_from_file(str(file_path))

    material = Material(
        order_id=order_id,
        type=MaterialType(material_type),
        file_path=str(file_path),
        original_name=original_name,
        ocr_text=ocr_text,
        notes=notes,
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    return MaterialResponse(
        id=material.id,
        order_id=material.order_id,
        type=material.type.value,
        file_path=material.file_path,
        original_name=material.original_name,
        ocr_text=material.ocr_text,
        notes=material.notes,
        created_at=str(material.created_at),
    )


@router.delete("/{material_id}")
def delete_material(material_id: int, db: Session = Depends(get_db)):
    """删除素材"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    # 删除文件
    if material.file_path and Path(material.file_path).exists():
        Path(material.file_path).unlink()
    db.delete(material)
    db.commit()
    return {"message": "素材已删除"}
