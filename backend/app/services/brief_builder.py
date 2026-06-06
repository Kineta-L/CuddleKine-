"""Build structured plush toy briefs from material understanding results."""
from __future__ import annotations

from typing import Any

from ..models.order import Order
from .manufacturing_adapter import manufacturing_suggestions, risk_notes
from .question_agent import build_pending_questions

BRIEF_SCHEMA_FIELDS = [
    "order_intent",
    "source_type",
    "toy_category",
    "character_identity",
    "target_height",
    "body_proportions",
    "head_features",
    "face_features",
    "clothing",
    "colors",
    "materials",
    "accessories",
    "key_features_to_preserve",
    "allowed_simplifications",
    "forbidden_changes",
    "manufacturing_suggestions",
    "pending_questions",
    "risk_notes",
]


def build_structured_brief(order: Order, material_result: dict[str, Any]) -> dict[str, Any]:
    observations = material_result.get("observations") or []
    source_type = material_result.get("source_type") or "mixed"
    source_summary = material_result.get("source_summary") or "customer reference materials"

    structured: dict[str, Any] = {
        "order_intent": _order_intent(order, source_summary),
        "source_type": source_type,
        "toy_category": _toy_category(order, source_type, source_summary),
        "character_identity": order.character_type or source_summary,
        "target_height": order.target_height,
        "body_proportions": order.main_proportions or "",
        "head_features": _feature_text(observations, "head"),
        "face_features": _feature_text(observations, "face"),
        "clothing": _feature_text(observations, "clothing"),
        "colors": order.colors or _colors_from_observations(observations),
        "materials": order.material_preference or "",
        "accessories": order.accessories or _accessories_from_observations(observations),
        "key_features_to_preserve": order.key_features or source_summary,
        "allowed_simplifications": order.allowed_simplifications or (
            "Simplify tiny text, complex prints, hard objects, and overly thin details into plush-safe fabric or embroidery."
        ),
        "forbidden_changes": "",
    }
    structured["manufacturing_suggestions"] = manufacturing_suggestions(observations)
    structured["risk_notes"] = risk_notes(observations, structured)
    structured["pending_questions"] = build_pending_questions(
        structured,
        structured["risk_notes"],
    )
    return structured


def missing_info(structured: dict[str, Any]) -> list[dict[str, str]]:
    required = {
        "toy_category": "玩具品类",
        "character_identity": "角色身份描述",
        "target_height": "目标成品高度",
        "body_proportions": "头身比例和四肢比例",
        "colors": "主要颜色方案",
        "materials": "面料和工艺偏好",
        "key_features_to_preserve": "必须保留的辨识特征",
        "forbidden_changes": "不能改变的内容",
    }
    return [
        {
            "field": field,
            "description": description,
            "reason": "当前 brief 中缺少该信息或需要客户确认",
        }
        for field, description in required.items()
        if not structured.get(field)
    ]


def merge_designer_edits(structured: dict[str, Any], edits: dict[str, Any]) -> dict[str, Any]:
    merged = dict(structured)
    for key in BRIEF_SCHEMA_FIELDS:
        if key in edits:
            merged[key] = edits[key]
    return merged


def sync_order_from_brief(order: Order, structured: dict[str, Any]) -> None:
    order.character_type = str(structured.get("character_identity") or order.character_type or "")
    target_height = structured.get("target_height")
    if target_height not in (None, ""):
        try:
            order.target_height = float(target_height)
        except (TypeError, ValueError):
            pass
    order.main_proportions = _stringify(structured.get("body_proportions"))
    order.colors = _stringify(structured.get("colors"))
    order.material_preference = _stringify(structured.get("materials"))
    order.accessories = _stringify(structured.get("accessories"))
    order.key_features = _stringify(structured.get("key_features_to_preserve"))
    order.allowed_simplifications = _stringify(structured.get("allowed_simplifications"))
    order.pending_items = _stringify(structured.get("pending_questions"))
    order.craft_notes = _stringify(structured.get("manufacturing_suggestions"))


def _order_intent(order: Order, source_summary: str) -> str:
    height = f" {order.target_height:g}cm" if order.target_height else ""
    return f"Turn {source_summary} into a{height} manufacturable plush toy sample."


def _toy_category(order: Order, source_type: str, source_summary: str) -> str:
    text = f"{order.character_type or ''} {source_summary}".lower()
    if "pet" in text or "animal" in text or source_type == "pet_photo":
        return "animal_plush"
    if "human" in text or "person" in text or source_type == "real_person_photo":
        return "human_doll"
    if "mascot" in text or "ip" in text:
        return "mascot"
    return "unknown"


def _feature_text(observations: list[dict[str, Any]], feature_type: str) -> str:
    excerpts = []
    for item in observations:
        features = item.get("visual_features") or {}
        text = str(features.get("raw_text_excerpt") or "").strip()
        if text:
            excerpts.append(text[:160])
    if not excerpts:
        return ""
    return f"Inferred from materials for {feature_type}: " + " / ".join(excerpts[:2])


def _colors_from_observations(observations: list[dict[str, Any]]) -> str:
    colors: list[str] = []
    for item in observations:
        features = item.get("visual_features") or {}
        colors.extend(features.get("text_mentions_colors") or [])
    return ", ".join(dict.fromkeys(colors))


def _accessories_from_observations(observations: list[dict[str, Any]]) -> str:
    accessories: list[str] = []
    for item in observations:
        features = item.get("visual_features") or {}
        accessories.extend(features.get("text_mentions_accessories") or [])
    return ", ".join(dict.fromkeys(accessories))


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(item) for item in value if item)
    if isinstance(value, dict):
        return "\n".join(f"{k}: {v}" for k, v in value.items())
    return str(value)
