"""ComfyUI Provider — Phase 3: 质量模式 + 参考图预处理"""
import time
import random
import uuid
from pathlib import Path

from .base import ImageProvider, GenerateJob, GenerateResult, ProviderHealth
from ..comfyui_service import ComfyUIService, MockComfyUIService
from ..image_postprocess import prepare_reference_subject
from ...config import GENERATION_PROVIDER
from ..settings_service import get_comfyui_input_dir


# ── 质量参数表 ─────────────────────────────────────

QUALITY_PARAMS = {
    "draft":  {"steps": 15, "cfg": 6.0,  "denoise": 0.70},
    "sample": {"steps": 25, "cfg": 7.5,  "denoise": 0.65},
    "final":  {"steps": 35, "cfg": 8.5,  "denoise": 0.60},
}

class ComfyUIProvider(ImageProvider):
    id = "comfyui"
    name = "ComfyUI 本地草稿 (SDXL)"
    supports_text_to_image = True
    supports_image_to_image = True
    supports_inpaint = False
    supports_transparent_background = False
    models = [
        {"id": "sd_xl_base_1.0", "name": "SDXL Base 1.0", "quality": "draft",
         "best_for": "低成本草稿 / 本地离线"},
    ]

    def __init__(self):
        if GENERATION_PROVIDER == "comfyui":
            self._service = ComfyUIService()
            self._use_mock = False
        else:
            self._service = MockComfyUIService()
            self._use_mock = True

    async def health_check(self) -> ProviderHealth:
        if self._use_mock:
            return ProviderHealth(available=True, message="Mock 模式", configured=True)
        try:
            ok = await self._service.health_check()
            if ok:
                return ProviderHealth(available=True, message="ComfyUI 在线", configured=True)
            return ProviderHealth(available=False, message="ComfyUI 无响应", configured=True)
        except Exception as e:
            return ProviderHealth(available=False, message=str(e), configured=True)

    async def generate(self, job: GenerateJob) -> GenerateResult:
        qp = QUALITY_PARAMS.get(job.quality_mode, QUALITY_PARAMS["sample"])
        seed = random.randint(1, 2_147_483_647)
        is_multiview = job.view_type in ("front", "side", "back")
        has_reference = bool(job.reference_images)

        # ── 参考图预处理（Phase 3 增强） ──
        ref_name = ""
        if has_reference:
            ref_path = job.reference_images[0]
            job.workflow_name = "multiview.json"  # 切 img2img 工作流
            comfyui_input_dir = get_comfyui_input_dir()
            comfyui_input_dir.mkdir(parents=True, exist_ok=True)
            if is_multiview:
                # 多视图：直接复制原图
                ref_name = f"ref_{job.order_id}_{job.source_version_id or 'mat'}_{uuid.uuid4().hex[:8]}.png"
                target = comfyui_input_dir / ref_name
                import shutil
                shutil.copy(ref_path, target)
            else:
                # 主视图有参考图：提取主体，去背景
                ref_name = f"ref_{job.order_id}_subject_{uuid.uuid4().hex[:8]}.png"
                target = comfyui_input_dir / ref_name
                try:
                    prepare_reference_subject(ref_path, target)
                except Exception:
                    import shutil
                    shutil.copy(ref_path, target)

        # ── 构建工作流参数 ──
        if is_multiview and ref_name:
            view_prompts = {
                "front": f"{job.prompt}, exact front view, facing camera directly",
                "side": f"{job.prompt}, exact side profile, 90-degree rotation",
                "back": f"{job.prompt}, exact back view, 180-degree rotation",
            }
            overrides = {
                "2": {"text": view_prompts.get(job.view_type, job.prompt)},
                "3": {"text": job.negative_prompt or "ugly, blurry, low quality"},
                "4": {"image": ref_name},
                "6": {
                    "seed": seed,
                    "steps": qp["steps"],
                    "cfg": qp["cfg"],
                    "denoise": qp["denoise"],
                },
            }
        elif ref_name:
            # 主视图有参考图 → img2img
            overrides = {
                "2": {"text": job.prompt},
                "3": {"text": job.negative_prompt or "ugly, blurry, low quality"},
                "4": {"image": ref_name},
                "6": {
                    "seed": seed,
                    "steps": qp["steps"],
                    "cfg": qp["cfg"],
                    "denoise": qp["denoise"],
                },
            }
        else:
            # 纯文生图
            overrides = {
                "2": {"text": job.prompt or "cute plush toy, product photo, white background"},
                "3": {"text": job.negative_prompt or "ugly, blurry, low quality"},
                "5": {
                    "seed": seed,
                    "steps": qp["steps"],
                    "cfg": qp["cfg"],
                    "denoise": 1.0,
                },
            }

        start = time.time()
        result = await self._service.generate(
            workflow_name=job.workflow_name,
            overrides=overrides,
            output_path=job.output_path,
        )

        return GenerateResult(
            file_path=result["file_path"],
            provider="comfyui",
            model=job.model or "sd_xl_base_1.0",
            duration=result["duration"],
            prompt=job.prompt,
            prompt_id=result.get("prompt_id", ""),
        )
