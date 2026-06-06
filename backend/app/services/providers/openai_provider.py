"""OpenAI Image Provider — high quality plush sample images."""
import json
import time

from .base import ImageProvider, GenerateJob, GenerateResult, ProviderHealth
from ..openai_image_service import OpenAIImageService
from ..settings_service import get_openai_api_key


class OpenAIProvider(ImageProvider):
    id = "openai"
    name = "GPT 样品图模式（推荐最终效果）"
    supports_text_to_image = True
    supports_image_to_image = True      # GPT-4o 支持参考图
    supports_inpaint = False
    supports_transparent_background = True
    models = [
        {"id": "gpt-image-1.5", "name": "GPT Image 1.5", "quality": "high",
         "best_for": "真实商品毛绒玩具样品照 / 高还原 / 参考图输入"},
        {"id": "gpt-image-1", "name": "GPT Image 1", "quality": "high",
         "best_for": "高质量样品图 / 参考图输入"},
        {"id": "gpt-image-1-mini", "name": "GPT Image 1 mini", "quality": "medium",
         "best_for": "低成本快速预览"},
        {"id": "dall-e-3", "name": "DALL·E 3", "quality": "high",
         "best_for": "高质量文生图（不推荐参考图还原）"},
    ]

    def __init__(self):
        self._service = OpenAIImageService()

    async def health_check(self) -> ProviderHealth:
        configured = bool(get_openai_api_key())
        if not configured:
            return ProviderHealth(available=False, message="未配置 API Key", configured=False)
        try:
            ok = await self._service.health_check()
            if ok:
                return ProviderHealth(available=True, message="OpenAI API 在线", configured=True)
            return ProviderHealth(available=False, message="Key 无效或无权限", configured=True)
        except Exception as e:
            return ProviderHealth(available=False, message=str(e), configured=True)

    async def generate(self, job: GenerateJob) -> GenerateResult:
        overrides = {
            "prompt": job.prompt,
            "quality_mode": job.quality_mode,
            "size": _default_size(job.view_type),
            "transparent_background": False,
            "reference_images": job.reference_images if self.supports_image_to_image else [],
        }

        start = time.time()
        result = await self._service.generate(
            workflow_name=job.model or "gpt-image-1.5",
            overrides=overrides,
            output_path=job.output_path,
        )

        return GenerateResult(
            file_path=result["file_path"],
            provider="openai",
            model=result.get("model", job.model or "gpt-image-1.5"),
            duration=result["duration"],
            prompt=job.prompt,
            prompt_id=result.get("prompt_id", ""),
            cost_estimate=result.get("cost_estimate", 0.0),
            raw_response=json.dumps(result.get("raw_response", {}), ensure_ascii=False),
        )


def _default_size(view_type: str) -> str:
    return "1024x1536"
