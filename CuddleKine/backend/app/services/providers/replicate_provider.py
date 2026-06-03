"""Replicate Provider — 云端备用模型平台"""
import time

from .base import ImageProvider, GenerateJob, GenerateResult, ProviderHealth
from ..replicate_service import ReplicateService
from ..settings_service import get_replicate_api_token


class ReplicateProvider(ImageProvider):
    id = "replicate"
    name = "Replicate 云端备用"
    supports_text_to_image = True
    supports_image_to_image = True
    supports_inpaint = True
    supports_transparent_background = False
    models = [
        {"id": "black-forest-labs/flux-dev", "name": "Flux Dev", "quality": "high",
         "best_for": "高质量文生图"},
        {"id": "stability-ai/sdxl", "name": "SDXL", "quality": "draft",
         "best_for": "图生图 / 局部修改"},
    ]

    def __init__(self):
        self._service = ReplicateService()

    async def health_check(self) -> ProviderHealth:
        configured = bool(get_replicate_api_token())
        if not configured:
            return ProviderHealth(available=False, message="未配置 API Token", configured=False)
        try:
            ok = await self._service.health_check()
            if ok:
                return ProviderHealth(available=True, message="Replicate API 在线", configured=True)
            return ProviderHealth(available=False, message="Token 无效", configured=True)
        except Exception as e:
            return ProviderHealth(available=False, message=str(e), configured=True)

    async def generate(self, job: GenerateJob) -> GenerateResult:
        model = job.model or "black-forest-labs/flux-dev"
        overrides = job.to_overrides()
        overrides["model"] = model

        # 图生图：参考图片作为 image 参数
        if job.reference_images:
            overrides["image"] = job.reference_images[0]

        # 局部修改切 inpainting 模型
        if job.derivation_type == "local_modify":
            overrides["model"] = "stability-ai/stable-diffusion-inpainting"

        start = time.time()
        result = await self._service.generate(
            workflow_name=model,
            overrides=overrides,
            output_path=job.output_path,
        )

        return GenerateResult(
            file_path=result["file_path"],
            provider="replicate",
            model=model,
            duration=result["duration"],
            prompt=job.prompt,
            prompt_id=result.get("prompt_id", ""),
            cost_estimate=0.025,
        )
