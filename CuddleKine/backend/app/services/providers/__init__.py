"""Provider 注册中心 — 可插拔的多模型后端"""
from .base import ImageProvider, GenerateJob, GenerateResult, ProviderHealth
from .registry import get_provider, list_providers, register_provider

__all__ = [
    "ImageProvider",
    "GenerateJob",
    "GenerateResult",
    "ProviderHealth",
    "get_provider",
    "list_providers",
    "register_provider",
]
