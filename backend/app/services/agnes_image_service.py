"""Agnes image generation service."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Optional

import httpx

from ..config import AGNES_API_KEY, AGNES_BASE_URL
from .settings_service import get_agnes_api_key


class AgnesImageError(Exception):
    pass


class AgnesImageService:
    """Small wrapper around the Agnes OpenAI-compatible Images API."""

    COST_PER_IMAGE = {
        "agnes-image-2.1-flash": 0.0,
        "agnes-image-2.0-flash": 0.0,
        "agnes-image-1.2": 0.008,
    }

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = AGNES_BASE_URL.rstrip("/")

    async def health_check(self) -> bool:
        return bool(self._api_key())

    async def generate(
        self,
        workflow_name: str = "",
        overrides: Optional[dict] = None,
        output_path: Optional[str] = None,
    ) -> dict:
        ov = overrides or {}
        requested_model = workflow_name or ov.get("model") or "agnes-image-2.1-flash"
        prompt = ov.get("prompt", "a realistic plush toy product photo")
        size = ov.get("size", "1024x1024")
        reference_images = [
            p for p in ov.get("reference_images", [])
            if self._is_valid_reference(p)
        ]

        start_time = time.time()
        model, result = await self._generate_with_fallback(requested_model, prompt, size, reference_images)
        mode = "img2img" if reference_images else "generate"

        save_path = output_path or "output.png"
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        await self._save_image_payload(result, save_path)

        return {
            "file_path": save_path,
            "duration": round(time.time() - start_time, 2),
            "prompt_id": result.get("id", ""),
            "model": model,
            "cost_estimate": self.COST_PER_IMAGE.get(model, 0.0),
            "raw_response": {
                "mode": mode,
                "model": model,
                "size": size,
                "reference_count": len(reference_images),
            },
        }

    def _parse_response(self, resp: httpx.Response) -> dict:
        if resp.status_code != 200:
            detail = self._safe_json(resp.text)
            if "model_not_found" in detail or "No available channel" in detail:
                raise AgnesImageError(
                    "Agnes 当前账号通道没有可用图片模型。请在设置中尝试切换 Agnes 模型，"
                    f"或到 Agnes 控制台确认该 API Key 已开通图片模型。原始错误: {detail}"
                )
            raise AgnesImageError(f"Agnes API returned {resp.status_code}: {detail}")
        payload = resp.json()
        data = payload.get("data", [])
        if not data:
            raise AgnesImageError("Agnes API returned no image data")
        item = data[0]
        item["id"] = payload.get("id") or str(payload.get("created", ""))
        return item

    async def _save_image_payload(self, item: dict, save_path: str) -> None:
        b64_data = item.get("b64_json", "")
        if b64_data:
            Path(save_path).write_bytes(base64.b64decode(b64_data))
            return

        image_url = item.get("url", "")
        if not image_url:
            raise AgnesImageError("Agnes API returned neither b64_json nor url")

        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            Path(save_path).write_bytes(resp.content)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }

    def _api_key(self) -> str:
        return self.api_key or get_agnes_api_key() or AGNES_API_KEY

    async def _generate_with_fallback(
        self,
        requested_model: str,
        prompt: str,
        size: str,
        reference_images: list[str] | None = None,
    ) -> tuple[str, dict]:
        candidates = [requested_model]
        for model in ("agnes-image-2.1-flash", "agnes-image-2.0-flash", "agnes-image-1.2"):
            if model not in candidates:
                candidates.append(model)

        last_error = ""
        async with httpx.AsyncClient(timeout=180) as client:
            for model in candidates:
                body = self._build_generation_body(model, prompt, size, reference_images or [])
                resp = await client.post(
                    f"{self.base_url}/images/generations",
                    headers=self._headers(),
                    json=body,
                )
                if resp.status_code == 200:
                    return model, self._parse_response(resp)
                last_error = self._safe_json(resp.text)
                if "model_not_found" not in last_error and "No available channel" not in last_error:
                    self._parse_response(resp)

        raise AgnesImageError(
            "Agnes 当前账号通道没有可用图片模型。已尝试 agnes-image-2.1-flash、agnes-image-2.0-flash 和 agnes-image-1.2。"
            f"请到 Agnes 控制台确认 API Key 的图片模型权限。最后错误: {last_error}"
        )

    def _build_generation_body(
        self,
        model: str,
        prompt: str,
        size: str,
        reference_images: list[str],
    ) -> dict:
        body: dict = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }
        if reference_images:
            body["tags"] = ["img2img"]
            body["extra_body"] = {
                "image": [self._resolve_reference_image(path) for path in reference_images[:4]],
                "response_format": "url",
            }
        return body

    @staticmethod
    def _is_valid_reference(file_path: str) -> bool:
        p = Path(file_path)
        return p.exists() and p.stat().st_size <= 50 * 1024 * 1024

    @staticmethod
    def _mime_type(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            return "image/jpeg"
        if suffix == ".webp":
            return "image/webp"
        return "image/png"

    def _resolve_reference_image(self, file_path: str) -> str:
        if file_path.startswith(("http://", "https://", "data:")):
            return file_path
        path = Path(file_path)
        if not path.exists():
            raise AgnesImageError(f"Reference image does not exist: {file_path}")
        return self._encode_data_uri(path)

    def _encode_data_uri(self, path: Path) -> str:
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{self._mime_type(path)};base64,{data}"

    @staticmethod
    def _safe_json(text: str) -> str:
        try:
            return json.dumps(json.loads(text), ensure_ascii=False)
        except Exception:
            return text[:500]
