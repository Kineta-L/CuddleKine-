"""OpenAI image generation service for plush toy sample images."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Optional

import httpx

from ..config import OPENAI_API_KEY
from .settings_service import get_openai_api_key


class OpenAIImageError(Exception):
    pass


class OpenAIImageService:
    """Small wrapper around OpenAI image generation and image editing APIs."""

    COST_PER_IMAGE = {
        "gpt-image-1.5": 0.08,
        "gpt-image-1": 0.04,
        "gpt-image-1-mini": 0.015,
        "dall-e-3": 0.04,
    }

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"

    async def health_check(self) -> bool:
        if not self._api_key():
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/models", headers=self._headers())
                return resp.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        workflow_name: str = "",
        overrides: Optional[dict] = None,
        output_path: Optional[str] = None,
    ) -> dict:
        ov = overrides or {}
        model = self._normalize_model(workflow_name or ov.get("model") or "gpt-image-1.5")
        prompt = ov.get("prompt", "a cute plush toy prototype sample")
        size = ov.get("size", "1024x1536")
        quality = self._quality(ov.get("quality_mode", "sample"), model)
        transparent = bool(ov.get("transparent_background", True))
        reference_images = [
            p for p in ov.get("reference_images", [])
            if self._is_valid_reference(p)
        ]

        start_time = time.time()
        if reference_images and model != "dall-e-3":
            result_data = await self._edit_image(
                model=model,
                prompt=prompt,
                reference_images=reference_images,
                size=size,
                quality=quality,
                transparent=transparent,
            )
            mode = "edit"
        else:
            result_data = await self._generate_image(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                transparent=transparent and model != "dall-e-3",
            )
            mode = "generate"

        save_path = output_path or "output.png"
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        self._save_image_payload(result_data, save_path)

        duration = round(time.time() - start_time, 2)
        return {
            "file_path": save_path,
            "duration": duration,
            "prompt_id": result_data.get("id", ""),
            "model": model,
            "cost_estimate": self.COST_PER_IMAGE.get(model, 0.0),
            "raw_response": {
                "mode": mode,
                "model": model,
                "size": size,
                "quality": quality,
                "reference_count": len(reference_images),
            },
        }

    async def _generate_image(
        self,
        model: str,
        prompt: str,
        size: str,
        quality: str,
        transparent: bool,
    ) -> dict:
        body: dict = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024" if model == "dall-e-3" else size,
        }
        if model == "dall-e-3":
            body["quality"] = "hd" if quality == "high" else "standard"
        else:
            body.update({
                "quality": quality,
                "output_format": "png",
            })
            if transparent:
                body["background"] = "transparent"

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{self.base_url}/images/generations",
                headers=self._headers(),
                json=body,
            )
        return self._parse_response(resp, "OpenAI image generation failed")

    async def _edit_image(
        self,
        model: str,
        prompt: str,
        reference_images: list[str],
        size: str,
        quality: str,
        transparent: bool,
    ) -> dict:
        data = {
            "model": model,
            "prompt": prompt,
            "n": "1",
            "size": size,
            "quality": quality,
            "output_format": "png",
        }
        if transparent:
            data["background"] = "transparent"

        files = []
        handles = []
        try:
            for path in reference_images[:4]:
                p = Path(path)
                fh = p.open("rb")
                handles.append(fh)
                files.append(("image", (p.name, fh, self._mime_type(p))))

            async with httpx.AsyncClient(timeout=240) as client:
                resp = await client.post(
                    f"{self.base_url}/images/edits",
                    headers={"Authorization": f"Bearer {self._api_key()}"},
                    data=data,
                    files=files,
                )
        finally:
            for fh in handles:
                fh.close()

        return self._parse_response(resp, "OpenAI image edit failed")

    def _parse_response(self, resp: httpx.Response, message: str) -> dict:
        if resp.status_code != 200:
            raise OpenAIImageError(f"{message} ({resp.status_code}): {self._safe_json(resp.text)}")
        result = resp.json()
        data = result.get("data", [])
        if not data:
            raise OpenAIImageError("OpenAI API returned no image data")
        item = data[0]
        item["id"] = result.get("id") or str(result.get("created", ""))
        return item

    def _save_image_payload(self, item: dict, save_path: str) -> None:
        b64_data = item.get("b64_json", "")
        if b64_data:
            Path(save_path).write_bytes(base64.b64decode(b64_data))
            return

        image_url = item.get("url", "")
        if not image_url:
            raise OpenAIImageError("OpenAI API returned neither b64_json nor url")

        with httpx.Client(timeout=60) as client:
            resp = client.get(image_url)
            resp.raise_for_status()
            Path(save_path).write_bytes(resp.content)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _normalize_model(model: str) -> str:
        if model in ("", "gpt-4o", "gpt-4o-image"):
            return "gpt-image-1.5"
        allowed = {"gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini", "dall-e-3"}
        return model if model in allowed else "gpt-image-1.5"

    @staticmethod
    def _quality(quality_mode: str, model: str) -> str:
        if model == "gpt-image-1-mini":
            return "medium"
        if quality_mode == "draft":
            return "low"
        if quality_mode == "final":
            return "high"
        return "medium"

    @staticmethod
    def _is_valid_reference(file_path: str) -> bool:
        p = Path(file_path)
        return p.exists() and p.stat().st_size <= 20 * 1024 * 1024

    @staticmethod
    def _mime_type(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            return "image/jpeg"
        if suffix == ".webp":
            return "image/webp"
        return "image/png"

    @staticmethod
    def _safe_json(text: str) -> str:
        try:
            return json.dumps(json.loads(text), ensure_ascii=False)
        except Exception:
            return text[:500]

    def _api_key(self) -> str:
        return self.api_key or get_openai_api_key() or OPENAI_API_KEY
