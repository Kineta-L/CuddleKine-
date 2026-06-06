"""Provider 注册中心 — 管理所有图像生成后端"""
from __future__ import annotations

import importlib
from typing import Optional

from .base import ImageProvider, GenerateJob, GenerateResult, ProviderHealth, ProviderInfo


# ── 注册表 ────────────────────────────────────────

_registry: dict[str, ImageProvider] = {}


def register_provider(provider: ImageProvider) -> None:
    """注册一个 provider 实例"""
    _registry[provider.id] = provider


def get_provider(provider_id: str | None = None) -> ImageProvider:
    """
    根据 provider_id 获取对应后端实例。
    如果未指定，返回默认 provider（mock）。
    """
    if provider_id and provider_id in _registry:
        return _registry[provider_id]

    # 回退到默认（mock 永远可用）
    if "mock" in _registry:
        return _registry["mock"]

    raise ValueError(f"Provider '{provider_id}' 未注册，且没有回退 provider")


def list_providers() -> list[ProviderInfo]:
    """列出所有已注册 provider 的展示信息"""
    result: list[ProviderInfo] = []
    for pid, p in _registry.items():
        model_list: list[dict] = []
        if hasattr(p, "models"):
            model_list = getattr(p, "models")
        result.append(ProviderInfo(
            id=p.id,
            name=p.name,
            enabled=True,
            configured=True,  # 需异步检测, 调用时替换
            supports_text_to_image=p.supports_text_to_image,
            supports_image_to_image=p.supports_image_to_image,
            supports_inpaint=p.supports_inpaint,
            supports_transparent_background=p.supports_transparent_background,
            models=model_list,
        ))
    return result


def _get_registry() -> dict:
    """调试用：暴露内部注册表"""
    return _registry
