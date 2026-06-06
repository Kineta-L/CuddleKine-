"""Brief Agent — 从素材中整理结构化需求，列出缺失信息和冲突项"""
import json
from typing import TypedDict
from collections.abc import Sequence


class BriefResult(TypedDict):
    structured: dict
    missing_info: list[dict]
    conflicts: list[dict]
    summary: str


# 期望从素材中提取的字段
EXPECTED_FIELDS = {
    "character_type": "角色类型（如 卡通猫/动漫人物/IP角色）",
    "target_height": "目标成品高度(cm)",
    "main_proportions": "主要比例（如 头身比、四肢长度）",
    "colors": "颜色方案",
    "material_preference": "材质倾向（如 短毛绒/长毛绒/水晶超柔）",
    "accessories": "配件（如 帽子/围巾/眼镜）",
    "key_features": "关键辨识特征（不能丢失的特征）",
    "allowed_simplifications": "允许简化的细节",
    "craft_notes": "工艺备注",
}


def analyze_materials(materials: Sequence[dict]) -> BriefResult:
    """
    分析订单素材，生成结构化 brief。
    当前为规则引擎实现，后续可接入 LLM。
    """
    structured: dict = {}
    missing_info: list[dict] = []
    conflicts: list[dict] = []

    # 从 OCR 文本和人工输入中提取字段
    all_text = ""
    for mat in materials:
        text = mat.get("ocr_text", "") or mat.get("notes", "") or ""
        all_text += text + "\n"

    # 简单关键词匹配提取
    for field, description in EXPECTED_FIELDS.items():
        found = _extract_field(all_text, field)
        if found:
            structured[field] = found
        else:
            missing_info.append({
                "field": field,
                "description": description,
                "reason": "素材中未找到相关信息"
            })

    # 冲突检测
    conflicts = _detect_conflicts(all_text)

    summary = _build_summary(structured, missing_info)

    return BriefResult(
        structured=structured,
        missing_info=missing_info,
        conflicts=conflicts,
        summary=summary,
    )


def _extract_field(text: str, field: str) -> str | None:
    """简单的关键词匹配提取"""
    keywords = {
        "character_type": ["角色", "人物", "公仔", "IP", "卡通"],
        "target_height": ["高度", "厘米", "cm", "尺寸", "大小"],
        "main_proportions": ["比例", "头身", "四肢"],
        "colors": ["颜色", "配色", "色系", "色彩"],
        "material_preference": ["材质", "面料", "毛绒", "布料"],
        "accessories": ["配件", "配饰", "帽子", "围巾"],
        "key_features": ["特征", "特点", "标志", "辨识"],
        "allowed_simplifications": ["简化", "省略", "忽略"],
        "craft_notes": ["工艺", "缝制", "制作"],
    }

    kw_list = keywords.get(field, [field])
    for kw in kw_list:
        if kw in text:
            # 找到关键词所在行
            for line in text.split("\n"):
                if kw in line:
                    return line.strip()
    return None


def _detect_conflicts(text: str) -> list[dict]:
    """检测冲突项"""
    return []


def _build_summary(structured: dict, missing_info: list[dict]) -> str:
    filled = len(structured)
    total = len(EXPECTED_FIELDS)
    return (
        f"已提取 {filled}/{total} 项需求信息。"
        f"缺失 {len(missing_info)} 项，需要向客户追问。"
    )


def merge_customer_replies(
    current_structured: dict, replies: dict
) -> dict:
    """合并客户答复到 structured 中"""
    merged = dict(current_structured)
    merged.update(replies)
    return merged
