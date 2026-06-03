"""Mock Provider — 永远可用的占位生成器"""
import time

from .base import ImageProvider, GenerateJob, GenerateResult, ProviderHealth
from ..comfyui_service import MockComfyUIService


class MockProvider(ImageProvider):
    id = "mock"
    name = "Mock 占位生成"
    supports_text_to_image = True
    supports_image_to_image = True
    supports_inpaint = True
    supports_transparent_background = False
    models = [
        {"id": "mock-placeholder", "name": "Mock 占位图", "quality": "draft",
         "best_for": "离线测试 / 无模型可用时回退"},
    ]

    def __init__(self):
        self._service = MockComfyUIService()

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(available=True, message="Mock 永远可用", configured=True)

    async def generate(self, job: GenerateJob) -> GenerateResult:
        overrides = {"prompt": job.prompt or "plush toy placeholder"}

        start = time.time()
        result = await self._service.generate(
            workflow_name="mock",
            overrides=overrides,
            output_path=job.output_path,
        )

        return GenerateResult(
            file_path=result["file_path"],
            provider="mock",
            model="mock-placeholder",
            duration=result["duration"],
            prompt=job.prompt,
            prompt_id=result.get("prompt_id", ""),
        )
