"""Short prompt helpers for legacy order-based generation."""

from __future__ import annotations

from ..models.order import Order


BASE_STYLE = (
    "Real plush toy product photo, full body, clean white studio background, "
    "soft stuffed fabric, visible plush texture, embroidery and applique details, "
    "cute commercial toy proportions."
)

DEFAULT_NEGATIVE = (
    "illustration, drawing, painting, 3d render, CGI, anime, cartoon, plastic doll, "
    "porcelain doll, vinyl doll, realistic human, mannequin, busy background, text, logo, watermark"
)

VIEW_CONSTRAINTS: dict[str, str] = {
    "main": "main product sample view",
    "front": "front view turnaround, same plush toy design",
    "side": "side view turnaround, same plush toy design",
    "back": "back view turnaround, same plush toy design",
}


def build_plush_prompt(
    order: Order | None,
    view_type: str = "main",
    modification_prompt: str = "",
    locked_regions: str = "",
    quality_mode: str = "sample",
) -> tuple[str, str]:
    parts = [BASE_STYLE, f"Task: {VIEW_CONSTRAINTS.get(view_type, VIEW_CONSTRAINTS['main'])}."]
    if order:
        if order.character_type:
            parts.append(f"Subject: {order.character_type}.")
        if order.key_features:
            parts.append(f"Preserve: {order.key_features}.")
        if order.colors:
            parts.append(f"Colors: {order.colors}.")
        if order.material_preference:
            parts.append(f"Materials: {order.material_preference}.")
        if order.accessories:
            parts.append(f"Accessories: {order.accessories}.")
        if order.main_proportions:
            parts.append(f"Design details: {order.main_proportions}.")
        if order.allowed_simplifications:
            parts.append(f"Allowed simplification: {order.allowed_simplifications}.")

    if quality_mode == "final":
        parts.append("High quality final sample photo.")
    elif quality_mode == "draft":
        parts.append("Fast draft concept.")
    if modification_prompt:
        parts.append(f"Designer instruction: {modification_prompt}.")
    if locked_regions:
        parts.append(f"Keep unchanged: {locked_regions}.")

    return " ".join(parts), DEFAULT_NEGATIVE


def build_gpt_image_prompt(
    order: Order | None,
    view_type: str = "main",
    quality_mode: str = "sample",
) -> str:
    prompt, _ = build_plush_prompt(order, view_type=view_type, quality_mode=quality_mode)
    return prompt
