"""Replicate API 服务 — 云端图片生成（SDXL / Flux / ControlNet / Inpainting）

通过 Replicate.com 的托管模型生成图片，无需本地 GPU。
模型映射：
  - 文生图：flux-dev / stability-ai/sdxl
  - 图生图（草图→效果图）：SDXL + ControlNet
  - 局部修改：SDXL Inpainting
"""

import time
import base64
import httpx
from pathlib import Path
from typing import Optional

from ..config import (
    REPLICATE_API_TOKEN,
    REPLICATE_MODEL_DEFAULT,
    REPLICATE_MODEL_FLUX,
    REPLICATE_MODEL_INPAINT,
    REPLICATE_MODEL_I2I,
)
from .settings_service import get_replicate_api_token


class ReplicateError(Exception):
    """Replicate API 调用异常"""
    pass


class ReplicateService:
    """Replicate 云端生成服务

    统一的 generate() 接口，与 ComfyUIService / MockComfyUIService 签名一致，
    可在 generation.py 路由中无缝替换。
    """

    def __init__(self, api_token: str = ""):
        self.api_token = api_token
        self.base_url = "https://api.replicate.com/v1"

    # ── 公开接口 ──────────────────────────────────────

    async def health_check(self) -> bool:
        """验证 API token 是否有效"""
        if not self._api_token():
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/account",
                    headers=self._headers(),
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        workflow_name: str = "",
        overrides: Optional[dict] = None,
        output_path: Optional[str] = None,
    ) -> dict:
        """
        生成图片。

        参数语义（与 ComfyUIService 保持一致）：
          workflow_name  → 未使用（Replicate 侧由 overrides.model 决定模型）
          overrides      → {"prompt": str, "model": str, "image": str|None, ...}
          output_path    → 本地保存路径

        返回 {"file_path": str, "duration": float, "prompt_id": str}
        """
        ov = overrides or {}

        # 确定模型
        model = ov.get("model") or REPLICATE_MODEL_DEFAULT
        prompt = ov.get("prompt", "a cute plush toy, product photography")
        image_input = ov.get("image")     # URL 或本地文件路径（用于图生图）
        mask_input = ov.get("mask")        # URL 或本地文件路径（用于 inpainting）
        extra_params = {k: v for k, v in ov.items()
                        if k not in ("model", "prompt", "image", "mask")}

        # 构建 API 输入
        input_data = self._build_input(model, prompt, image_input, mask_input, extra_params)

        # 调用 Replicate
        start_time = time.time()
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{self.base_url}/predictions",
                headers={**self._headers(), "Prefer": "wait=60"},
                json={"version": model, "input": input_data},
            )

            if resp.status_code not in (200, 201):
                detail = self._safe_json(resp.text)
                raise ReplicateError(f"API 返回 {resp.status_code}: {detail}")

            result = resp.json()
        duration = time.time() - start_time

        # 提取输出图片 URL
        output_urls = result.get("output")
        error_msg = result.get("error")
        if error_msg:
            raise ReplicateError(f"模型错误: {error_msg}")
        if not output_urls:
            raise ReplicateError("生成成功但无输出图片")

        first_output = output_urls[0] if isinstance(output_urls, list) else output_urls

        # 下载到本地
        save_path = output_path or "output.png"
        if isinstance(first_output, str) and first_output.startswith("http"):
            save_path = await self._download(first_output, save_path)
        elif isinstance(first_output, str):
            # 可能是 base64 data URI
            save_path = self._save_data_uri(first_output, save_path)

        return {
            "file_path": save_path,
            "duration": round(duration, 2),
            "prompt_id": result.get("id", ""),
        }

    # ── 内部方法 ──────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_token()}",
            "Content-Type": "application/json",
        }

    def _api_token(self) -> str:
        return self.api_token or get_replicate_api_token() or REPLICATE_API_TOKEN

    def _build_input(
        self,
        model: str,
        prompt: str,
        image: Optional[str],
        mask: Optional[str],
        extra: dict,
    ) -> dict:
        """根据模型类型构建 API 输入字典"""
        input_data: dict = {}

        # --- Flux 系列 ---
        if "flux" in model.lower():
            input_data["prompt"] = prompt
            input_data["aspect_ratio"] = extra.get("aspect_ratio", "1:1")
            input_data["output_format"] = extra.get("output_format", "png")
            if extra.get("num_outputs"):
                input_data["num_outputs"] = extra["num_outputs"]
            if extra.get("go_fast"):
                input_data["go_fast"] = True
            return input_data

        # --- SDXL / SD 系列 ---
        if any(kw in model.lower() for kw in ("sdxl", "stable-diffusion", "sd3")):
            input_data["prompt"] = prompt
            negative = extra.get("negative_prompt", "")
            if negative:
                input_data["negative_prompt"] = negative
            if extra.get("num_outputs"):
                input_data["num_outputs"] = extra["num_outputs"]
            if extra.get("num_inference_steps"):
                input_data["num_inference_steps"] = extra["num_inference_steps"]
            if extra.get("guidance_scale"):
                input_data["guidance_scale"] = extra["guidance_scale"]
            if extra.get("seed"):
                input_data["seed"] = extra["seed"]

            # 图生图
            if image:
                resolved = self._resolve_image_input(image)
                if resolved:
                    input_data["image"] = resolved
            # Inpainting mask
            if mask:
                resolved = self._resolve_image_input(mask)
                if resolved:
                    input_data["mask"] = resolved
            return input_data

        # --- 通用回退 ---
        input_data["prompt"] = prompt
        input_data.update({k: v for k, v in extra.items()
                           if k not in ("model", "prompt")})
        return input_data

    def _resolve_image_input(self, image: str) -> Optional[str]:
        """将图片输入解析为 Replicate 可接受的 URI（HTTP URL 或 data URI）"""
        if not image:
            return None
        if image.startswith("http://") or image.startswith("https://"):
            return image
        if image.startswith("data:"):
            return image
        # 本地文件路径 → base64 data URI
        path = Path(image)
        if path.exists():
            return self._encode_data_uri(path)
        return None

    def _encode_data_uri(self, path: Path) -> str:
        """将本地图片编码为 data URI"""
        suffix = path.suffix.lower()
        mime_map = {
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
        }
        mime = mime_map.get(suffix, "image/png")
        data = base64.b64encode(path.read_bytes()).decode()
        return f"data:{mime};base64,{data}"

    def _save_data_uri(self, data_uri: str, save_path: str) -> str:
        """将 data URI 保存为文件"""
        header, b64 = data_uri.split(",", 1)
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(base64.b64decode(b64))
        return save_path

    async def _download(self, url: str, save_path: str) -> str:
        """下载图片到本地"""
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            Path(save_path).write_bytes(resp.content)
            return save_path

    @staticmethod
    def _safe_json(text: str) -> str:
        try:
            import json
            return json.dumps(json.loads(text), ensure_ascii=False)
        except Exception:
            return text[:500]
