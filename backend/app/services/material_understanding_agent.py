"""Material understanding for CuddleKine AI brief workflow."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image

from ..models.material import Material, MaterialType


SOURCE_TYPE_BY_MATERIAL = {
    MaterialType.TEXT: "text_description",
    MaterialType.CHAT_SCREENSHOT: "chat_screenshot",
    MaterialType.PHOTO: "real_person_photo",
    MaterialType.SKETCH: "hand_drawing",
    MaterialType.REFERENCE: "reference_image",
}


def analyze_material(material: Material) -> dict[str, Any]:
    """Return normalized observations for one material.

    This is intentionally conservative. It creates useful structure without
    over-claiming visual details when no vision model is available.
    """
    width: int | None = None
    height: int | None = None
    file_path = Path(material.file_path or "")
    if file_path.exists() and file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
        except Exception:
            width, height = None, None

    source_type = SOURCE_TYPE_BY_MATERIAL.get(material.type, "mixed")
    text = "\n".join(
        part for part in [material.original_name or "", material.ocr_text or "", material.notes or ""]
        if part
    )
    detected_subject = _detect_subject(text, source_type)
    features = _extract_visual_features(text, source_type, width, height)
    description = _build_description(source_type, detected_subject, features)

    return {
        "source_type": source_type,
        "detected_subject": detected_subject,
        "image_width": width,
        "image_height": height,
        "ai_description": description,
        "visual_features": features,
        "processing_status": "analyzed",
        "ai_model_used": "rule-based-material-v1",
    }


def analyze_materials(materials: list[Material]) -> dict[str, Any]:
    observations = [analyze_material(material) for material in materials]
    source_types = [item["source_type"] for item in observations if item.get("source_type")]
    dominant_source = source_types[0] if source_types else "mixed"
    if len(set(source_types)) > 1:
        dominant_source = "mixed"

    detected_subjects = [
        item["detected_subject"] for item in observations if item.get("detected_subject")
    ]
    source_summary = " / ".join(dict.fromkeys(detected_subjects)) or "Uploaded customer materials"

    return {
        "source_type": dominant_source,
        "source_summary": source_summary,
        "observations": observations,
        "ai_model_used": "rule-based-material-v1",
    }


def apply_material_analysis(material: Material, result: dict[str, Any]) -> None:
    material.source_type = str(result.get("source_type") or "")
    material.detected_subject = str(result.get("detected_subject") or "")
    material.image_width = result.get("image_width")
    material.image_height = result.get("image_height")
    material.ai_description = str(result.get("ai_description") or "")
    material.visual_features_json = json.dumps(
        result.get("visual_features") or {},
        ensure_ascii=False,
    )
    material.processing_status = str(result.get("processing_status") or "analyzed")


def _detect_subject(text: str, source_type: str) -> str:
    normalized = text.lower()
    if any(word in normalized for word in ["pet", "dog", "cat", "rabbit", "宠物", "猫", "狗", "兔"]):
        return "pet or animal plush subject"
    if any(word in normalized for word in ["girl", "boy", "person", "human", "真人", "女孩", "男孩", "人物"]):
        return "human doll character"
    if any(word in normalized for word in ["mascot", "ip", "logo", "吉祥物", "角色", "卡通"]):
        return "mascot or IP-style character"
    if source_type == "real_person_photo":
        return "human doll character"
    if source_type == "hand_drawing":
        return "hand-drawn plush character concept"
    if source_type == "chat_screenshot":
        return "customer chat requirements"
    return "reference subject"


def _extract_visual_features(
    text: str,
    source_type: str,
    width: int | None,
    height: int | None,
) -> dict[str, Any]:
    lowered = text.lower()
    color_words = [
        "black", "white", "brown", "yellow", "pink", "green", "blue", "red",
        "黑", "白", "棕", "黄", "粉", "绿", "蓝", "红", "紫",
    ]
    accessory_words = [
        "hat", "bag", "glasses", "flower", "shoe", "scarf",
        "帽", "包", "眼镜", "花", "鞋", "围巾", "配件",
    ]
    colors = [word for word in color_words if word in lowered]
    accessories = [word for word in accessory_words if word in lowered]

    return {
        "source_type": source_type,
        "image_size": {"width": width, "height": height},
        "text_mentions_colors": colors,
        "text_mentions_accessories": accessories,
        "raw_text_excerpt": text[:800],
    }


def _build_description(source_type: str, subject: str, features: dict[str, Any]) -> str:
    size = features.get("image_size") or {}
    size_text = ""
    if size.get("width") and size.get("height"):
        size_text = f" Image size {size['width']}x{size['height']}."
    colors = features.get("text_mentions_colors") or []
    accessories = features.get("text_mentions_accessories") or []
    detail_parts = []
    if colors:
        detail_parts.append(f"mentioned colors: {', '.join(colors)}")
    if accessories:
        detail_parts.append(f"mentioned accessories: {', '.join(accessories)}")
    detail_text = f" Detected {', '.join(detail_parts)}." if detail_parts else ""
    return f"{source_type}: {subject}.{size_text}{detail_text}"
