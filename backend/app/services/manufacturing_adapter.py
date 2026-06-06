"""Convert visual/customer features into plush-manufacturable language."""
from __future__ import annotations

from typing import Any


DEFAULT_MATERIALS = [
    "short plush fabric for skin or smooth body areas",
    "long plush or curled plush for fluffy hair and ears",
    "embroidery for eyes, brows, mouth, and small symbols",
    "applique fabric panels for clothing graphics",
    "soft filled fabric accessories instead of hard plastic parts",
]


def manufacturing_suggestions(observations: list[dict[str, Any]]) -> list[str]:
    suggestions = list(DEFAULT_MATERIALS)
    combined = " ".join(str(item.get("ai_description") or "") for item in observations).lower()
    combined += " " + " ".join(
        str((item.get("visual_features") or {}).get("raw_text_excerpt") or "")
        for item in observations
    ).lower()

    if any(word in combined for word in ["hair", "头发", "卷发", "辫子"]):
        suggestions.append(
            "Represent hair with plush hair blocks, embroidered hair lines, or layered fabric pieces."
        )
    if any(word in combined for word in ["logo", "文字", "text", "字"]):
        suggestions.append(
            "Simplify tiny text into embroidered symbols or color blocks unless the customer requires exact text."
        )
    if any(word in combined for word in ["metal", "glass", "金属", "玻璃"]):
        suggestions.append(
            "Convert hard metal or glass details into fabric, applique, or embroidery."
        )
    if any(word in combined for word in ["bag", "包", "hat", "帽", "flower", "花"]):
        suggestions.append(
            "Make important accessories as separate soft fabric pieces when scale allows."
        )

    return _dedupe(suggestions)


def risk_notes(observations: list[dict[str, Any]], structured: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    source_types = {item.get("source_type") for item in observations}
    if "mixed" in source_types or len(source_types) > 1:
        notes.append("Multiple material types were provided; designer should confirm which source has priority.")
    if not structured.get("target_height"):
        notes.append("Target finished height is missing; plush construction detail depends on scale.")
    if not structured.get("key_features_to_preserve"):
        notes.append("Key identity features are not fully confirmed; resemblance may drift during generation.")
    if not structured.get("forbidden_changes"):
        notes.append("Forbidden changes are not specified; confirm what must never be changed.")
    return notes


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(v for v in values if v))
