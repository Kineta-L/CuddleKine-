"""Provider registration bootstrap."""
from __future__ import annotations

from .agnes_provider import AgnesProvider
from .comfyui_provider import ComfyUIProvider
from .mock_provider import MockProvider
from .openai_provider import OpenAIProvider
from .registry import has_provider, register_provider
from .replicate_provider import ReplicateProvider


def ensure_provider_registry() -> None:
    """Register built-in providers once."""
    for provider in (
        ComfyUIProvider(),
        OpenAIProvider(),
        ReplicateProvider(),
        AgnesProvider(),
        MockProvider(),
    ):
        if not has_provider(provider.id):
            register_provider(provider)
