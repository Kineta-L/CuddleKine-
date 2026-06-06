"""Agnes Image Provider — cloud image model for low-cost tests."""

import json
import time

from .base import GenerateJob, GenerateResult, ImageProvider, ProviderHealth
from ..agnes_image_service import AgnesImageService
from ..settings_service import get_agnes_api_key


class AgnesProvider(ImageProvider):
    id = "agnes"
    name = "Agnes 云端图片（低成本测试）"
    supports_text_to_image = True
    supports_image_to_image = True
    supports_inpaint = False
    supports_transparent_background = False
    models = [
        {
            "id": "agnes-image-2.1-flash",
            "name": "Agnes Image 2.1 Flash",
            "quality": "medium",
            "best_for": "当前图片生成模型 / 文生图优先尝试",
        },
        {
            "id": "agnes-image-2.0-flash",
            "name": "Agnes Image 2.0 Flash",
            "quality": "medium",
            "best_for": "图片生成备选模型",
        },
        {
            "id": "agnes-image-1.2",
            "name": "Agnes Image 1.2",
            "quality": "medium",
            "best_for": "官方参数表小写模型名 / 若账号通道支持可用",
        },
    ]

    def __init__(self):
        self._service = AgnesImageService()

    async def health_check(self) -> ProviderHealth:
        configured = bool(get_agnes_api_key())
        if not configured:
            return ProviderHealth(available=False, message="未配置 API Key", configured=False)
        return ProviderHealth(available=True, message="Agnes API Key 已配置", configured=True)

    async def generate(self, job: GenerateJob) -> GenerateResult:
        overrides = {
            "prompt": job.prompt,
            "model": job.model or "agnes-image-2.1-flash",
            "size": _default_size(job.view_type),
            "reference_images": job.reference_images,
        }
        start = time.time()
        result = await self._service.generate(
            workflow_name=job.model or "agnes-image-2.1-flash",
            overrides=overrides,
            output_path=job.output_path,
        )
        return GenerateResult(
            file_path=result["file_path"],
            provider="agnes",
            model=result.get("model", job.model or "agnes-image-2.1-flash"),
            duration=result.get("duration", round(time.time() - start, 2)),
            prompt=job.prompt,
            prompt_id=result.get("prompt_id", ""),
            cost_estimate=result.get("cost_estimate", 0.0),
            raw_response=json.dumps(result.get("raw_response", {}), ensure_ascii=False),
        )


def _default_size(view_type: str) -> str:
    return "1024x1536"
