"""Provider-specific short prompt builder for plush toy generation."""
from __future__ import annotations

from typing import Any

PROMPT_BUILDER_VERSION = "plush-short-prompt-v1-designer-led"

BASE_STYLE = (
    "Real plush toy product photo, full body, clean white studio background, "
    "soft stuffed fabric, visible plush texture, embroidery and applique details, "
    "cute commercial toy proportions."
)

NEGATIVE_PROMPT = (
    "illustration, drawing, painting, 3d render, CGI, anime, cartoon, plastic doll, "
    "porcelain doll, vinyl doll, realistic human, mannequin, busy background, text, logo, watermark"
)

VIEW_TASKS = {
    "main": "main product sample view",
    "front": "front view turnaround, same plush toy design",
    "side": "side view turnaround, same plush toy design",
    "back": "back view turnaround, same plush toy design",
}


def build_provider_prompt(
    structured_brief: dict[str, Any],
    provider: str,
    view_type: str = "main",
    quality_mode: str = "sample",
    modification_prompt: str = "",
    locked_regions: str = "",
) -> dict[str, str]:
    final_prompt = _build_short_prompt(
        structured_brief,
        view_type=view_type,
        quality_mode=quality_mode,
        modification_prompt=modification_prompt,
        locked_regions=locked_regions,
    )
    return {
        "version": PROMPT_BUILDER_VERSION,
        "final_prompt": final_prompt,
        "provider_prompt": final_prompt,
        "negative_prompt": NEGATIVE_PROMPT,
    }


def _build_short_prompt(
    brief: dict[str, Any],
    view_type: str,
    quality_mode: str,
    modification_prompt: str,
    locked_regions: str,
) -> str:
    parts = [
        BASE_STYLE,
        f"Task: {VIEW_TASKS.get(view_type, VIEW_TASKS['main'])}.",
    ]

    identity = _first_value(brief, "designer_prompt", "generation_prompt", "prompt", "character_identity")
    if identity:
        parts.append(f"Subject: {identity}.")

    preserve = _value(brief, "key_features_to_preserve")
    if preserve:
        parts.append(f"Preserve: {preserve}.")

    details = _compact_join(
        _value(brief, "body_proportions"),
        _value(brief, "head_features"),
        _value(brief, "face_features"),
        _value(brief, "clothing"),
    )
    if details:
        parts.append(f"Design details: {details}.")

    colors = _value(brief, "colors")
    if colors:
        parts.append(f"Colors: {colors}.")

    materials = _value(brief, "materials")
    if materials:
        parts.append(f"Materials: {materials}.")

    accessories = _value(brief, "accessories")
    if accessories:
        parts.append(f"Accessories: {accessories}.")

    forbidden = _value(brief, "forbidden_changes")
    if forbidden:
        parts.append(f"Avoid: {forbidden}.")

    if quality_mode == "final":
        parts.append("High quality final sample photo.")
    elif quality_mode == "draft":
        parts.append("Fast draft concept.")

    if modification_prompt:
        parts.append(f"Designer instruction: {modification_prompt}.")
    if locked_regions:
        parts.append(f"Keep unchanged: {locked_regions}.")

    return " ".join(part for part in parts if part)


def _value(brief: dict[str, Any], key: str) -> str:
    value = brief.get(key)
    if value is None or value == "":
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)
    if isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in value.items() if v)
    return str(value)


def _first_value(brief: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _value(brief, key)
        if value:
            return value
    return ""


def _compact_join(*values: str) -> str:
    return "; ".join(value for value in values if value)
