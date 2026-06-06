"""Material management API."""
import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import ALLOWED_UPLOAD_EXTENSIONS, MATERIAL_DIR, MAX_UPLOAD_BYTES
from ..database import get_db
from ..models.material import Material, MaterialType
from ..models.order import Order, OrderStatus
from ..services.material_understanding_agent import analyze_material, apply_material_analysis
from ..services.ocr_service import extract_text_from_file

router = APIRouter(prefix="/api/materials", tags=["materials"])


class MaterialResponse(BaseModel):
    id: int
    order_id: int
    type: str
    file_path: Optional[str]
    original_name: Optional[str]
    ocr_text: Optional[str]
    notes: Optional[str]
    source_type: str = ""
    detected_subject: str = ""
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    ai_description: str = ""
    visual_features_json: str = ""
    processing_status: str = "pending"
    created_at: str

    model_config = {"from_attributes": True}


def _material_response(material: Material) -> MaterialResponse:
    return MaterialResponse(
        id=material.id,
        order_id=material.order_id,
        type=material.type.value,
        file_path=material.file_path,
        original_name=material.original_name,
        ocr_text=material.ocr_text,
        notes=material.notes,
        source_type=material.source_type or "",
        detected_subject=material.detected_subject or "",
        image_width=material.image_width,
        image_height=material.image_height,
        ai_description=material.ai_description or "",
        visual_features_json=material.visual_features_json or "",
        processing_status=material.processing_status or "pending",
        created_at=str(material.created_at),
    )


@router.get("/{order_id}", response_model=list[MaterialResponse])
def list_materials(order_id: int, db: Session = Depends(get_db)):
    materials = (
        db.query(Material)
        .filter(Material.order_id == order_id)
        .order_by(Material.created_at.asc())
        .all()
    )
    return [_material_response(material) for material in materials]


@router.post("/{order_id}/upload", response_model=MaterialResponse)
async def upload_material(
    order_id: int,
    file: UploadFile = File(...),
    material_type: str = Form(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if material_type not in [t.value for t in MaterialType]:
        raise HTTPException(status_code=400, detail=f"Invalid material type: {material_type}")

    original_name = Path(file.filename or "upload").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix or 'none'}")

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
                        detail=f"File too large. Max {MAX_UPLOAD_BYTES // 1024 // 1024}MB.",
                    )
                f.write(chunk)
    except HTTPException:
        if file_path.exists():
            file_path.unlink()
        raise

    material = Material(
        order_id=order_id,
        type=MaterialType(material_type),
        file_path=str(file_path),
        original_name=original_name,
        ocr_text=extract_text_from_file(str(file_path)),
        notes=notes,
        processing_status="pending",
    )
    db.add(material)
    order.status = OrderStatus.MATERIAL_IMPORTED
    db.commit()
    db.refresh(material)
    return _material_response(material)


@router.post("/{material_id}/analyze", response_model=MaterialResponse)
def analyze_single_material(material_id: int, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    try:
        result = analyze_material(material)
        apply_material_analysis(material, result)
    except Exception as exc:
        material.processing_status = "error"
        material.ai_description = str(exc)
    db.commit()
    db.refresh(material)
    return _material_response(material)


@router.delete("/{material_id}")
def delete_material(material_id: int, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if material.file_path and Path(material.file_path).exists():
        Path(material.file_path).unlink()
    db.delete(material)
    db.commit()
    return {"message": "Material deleted"}
