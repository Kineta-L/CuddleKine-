"""毛绒玩具样品图 Prompt 模板系统

三层 Prompt 架构（参考 plush_toy_sampling_workbench_plan.txt 第五章）：
  第 1 层：全局强制规则（STYLE + LOCK）  — 所有 provider 共享
  第 2 层：订单 brief 字段               — 从 Order 对象动态拼接
  第 3 层：当前任务约束                    — view_type + derivation_type 决定
"""

from __future__ import annotations
from typing import Optional
from ..models.order import Order


# ── 第 1 层：全局强制规则 ───────────────────────────

STRICT_PRODUCT_BRIEF = (
    "STRICT PRODUCT BRIEF: "
    "Create a professional manufacturable plush toy prototype sample. "
    "Full body centered, product catalog sample quality. "
    "Use real soft plush fabric, visible fibers, embroidered eyes, "
    "stitched facial details, fabric clothing, fabric accessories, "
    "soft stuffed rounded limbs, visible seams, factory-sample construction."
)

REFERENCE_LOCK_RULES = (
    "MUST preserve the reference subject identity, species, gender impression, "
    "silhouette, hairstyle or ears, face shape, outfit, colors, shoes, bag, "
    "accessories, symbols and signature details. "
    "Do not reinterpret hair buns as animal ears. "
    "Do not change a human/person/doll character into an animal, bear, "
    "mouse, mascot or monster."
)

DEFAULT_NEGATIVE = (
    "ugly, deformed, noisy, blurry, distorted, disfigured, bad anatomy, "
    "extra limbs, watermark, text, logo, signature, low quality, jpeg artifacts, "
    "cropped, out of frame, busy background, colored background, fantasy scene, "
    "hard plastic, metal toy, porcelain doll, real human, mannequin, 3d render, "
    "anime drawing, wrong character, changed identity, animal if the reference is human, "
    "bear, mouse, mascot, hair buns turned into ears, missing accessories, wrong outfit colors"
)


# ── 第 3 层：任务约束 ──────────────────────────────

VIEW_CONSTRAINTS: dict[str, str] = {
    "main": (
        "final main sample view, full body visible, centered, "
        "isolated subject, no background, product catalog photo"
    ),
    "front": (
        "exact front orthographic view, full body visible, "
        "same character as the main sample, isolated subject, no background"
    ),
    "side": (
        "exact side profile orthographic view, 90-degree rotation, "
        "full body visible, same character as the main sample, isolated subject, no background"
    ),
    "back": (
        "exact back orthographic view, 180-degree rotation, "
        "full body visible, same character as the main sample, isolated subject, no background"
    ),
}

# 局部修改约束
LOCAL_MODIFY_CONSTRAINT = (
    "apply ONLY the requested change, keep locked regions and all other "
    "features (identity, colors, accessories, proportions) completely unchanged"
)


# ── 第 2 层：订单字段拼接 ──────────────────────────

def _order_to_lines(order: Order | None) -> list[str]:
    """从订单对象提取 brief 字段，转成 prompt 行"""
    if not order:
        return []
    lines: list[str] = []
    if order.character_type:
        lines.append(f"Character identity / subject type: {order.character_type}")
    if order.key_features:
        lines.append(f"Must preserve key visual features: {order.key_features}")
    if order.colors:
        lines.append(f"Must preserve color palette: {order.colors}")
    if order.material_preference:
        lines.append(f"Preferred plush materials: {order.material_preference}")
    if order.accessories:
        lines.append(f"Must preserve accessories: {order.accessories}")
    if order.target_height:
        lines.append(f"Target height: {order.target_height} cm")
    if order.main_proportions:
        lines.append(f"Proportions: {order.main_proportions}")
    if order.allowed_simplifications:
        lines.append(f"Allowed simplifications: {order.allowed_simplifications}")
    return lines


# ── 主函数：构建完整 prompt ────────────────────────

def build_plush_prompt(
    order: Order | None,
    view_type: str = "main",
    modification_prompt: str = "",
    locked_regions: str = "",
    quality_mode: str = "sample",
) -> tuple[str, str]:
    """
    构建毛绒玩具样品图的正向 + 负向 prompt。

    参数：
      order: 订单对象（含 brief 字段）
      view_type: main | front | side | back
      modification_prompt: 局部修改描述
      locked_regions: 锁定区域描述
      quality_mode: draft | sample | final

    返回：(prompt, negative_prompt)
    """
    parts: list[str] = []

    # 第 1 层：全局规则
    parts.append(STRICT_PRODUCT_BRIEF)
    parts.append(REFERENCE_LOCK_RULES)

    # 第 2 层：订单字段
    parts.extend(_order_to_lines(order))

    # 质量模式增强
    if quality_mode in ("sample", "final"):
        parts.append(
            "High quality product sample photo, professional commercial photography, "
            "sharp focus, even studio lighting, visible fabric texture and plush nap"
        )
    if quality_mode == "final":
        parts.append(
            "FINAL production-ready sample, every detail refined, "
            "suitable for client approval and factory reference"
        )

    # 第 3 层：任务约束
    constraint = VIEW_CONSTRAINTS.get(view_type, VIEW_CONSTRAINTS["main"])
    parts.append(constraint)

    if modification_prompt:
        parts.append(LOCAL_MODIFY_CONSTRAINT)
        parts.append(f"Requested modification: {modification_prompt}")
    if locked_regions:
        parts.append(f"Keep these regions unchanged: {locked_regions}")

    prompt = ", ".join(p for p in parts if p)
    return prompt, DEFAULT_NEGATIVE


# ── GPT 专用精简 prompt（GPT-4o 生图对短 prompt 响应更好） ──

def build_gpt_image_prompt(
    order: Order | None,
    view_type: str = "main",
    quality_mode: str = "sample",
) -> str:
    """为 GPT-4o 生图构建精简 prompt（400 字符以内，英文）"""
    parts: list[str] = []

    parts.append(
        "Plush toy prototype sample, product photography, "
        "white background, soft plush fabric texture, embroidered details"
    )

    if order:
        if order.character_type:
            identity = order.character_type[:80]
            parts.append(f"Character: {identity}")
        if order.key_features:
            features = order.key_features[:100]
            parts.append(f"Key features: {features}")
        if order.colors:
            parts.append(f"Colors: {order.colors[:60]}")
        if order.material_preference:
            parts.append(f"Material: {order.material_preference[:60]}")
        if order.accessories:
            parts.append(f"Accessories: {order.accessories[:60]}")

    if quality_mode in ("sample", "final"):
        parts.append("High quality, detailed, commercial sample photo")

    constraint = VIEW_CONSTRAINTS.get(view_type, VIEW_CONSTRAINTS["main"])
    parts.append(constraint)

    # 保留角色身份的关键约束
    parts.append(
        "Preserve character identity exactly, do not change species or gender, "
        "keep all accessories and outfit details"
    )

    return ". ".join(parts)
