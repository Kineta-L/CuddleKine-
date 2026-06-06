"""ComfyUI 服务 — 调用本地 ComfyUI API 生成图片"""
import json
import time
import httpx
from pathlib import Path
from ..config import COMFYUI_BASE_URL, COMFYUI_WORKFLOW_DIR
from .settings_service import get_comfyui_base_url
from .image_postprocess import make_background_transparent


class ComfyUIError(Exception):
    """ComfyUI 调用异常"""
    pass


class ComfyUIService:
    """ComfyUI API 封装"""

    def __init__(self, base_url: str = ""):
        self.base_url = (base_url or get_comfyui_base_url() or COMFYUI_BASE_URL).rstrip("/")

    async def health_check(self) -> bool:
        """检查 ComfyUI 是否可用"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/system_stats")
                return resp.status_code == 200
        except Exception:
            return False

    async def load_workflow(self, workflow_name: str) -> dict:
        """加载工作流 JSON"""
        path = COMFYUI_WORKFLOW_DIR / workflow_name
        if not path.exists():
            path = COMFYUI_WORKFLOW_DIR / f"{workflow_name}.json"
        if not path.exists():
            raise ComfyUIError(f"工作流文件不存在: {workflow_name}")
        return json.loads(path.read_text(encoding="utf-8"))

    async def queue_prompt(self, workflow: dict) -> str:
        """提交工作流到队列，返回 prompt_id"""
        payload = {"prompt": workflow}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self.base_url}/prompt", json=payload)
            if resp.status_code != 200:
                raise ComfyUIError(f"提交失败: {resp.text}")
            return resp.json()["prompt_id"]

    async def wait_for_result(
        self, prompt_id: str, poll_interval: float = 2.0, timeout: float = 300
    ) -> dict:
        """轮询等待生成完成"""
        start = time.time()
        async with httpx.AsyncClient(timeout=30) as client:
            while time.time() - start < timeout:
                resp = await client.get(f"{self.base_url}/history/{prompt_id}")
                if resp.status_code != 200:
                    raise ComfyUIError(f"查询历史失败: {resp.text}")
                data = resp.json()
                if prompt_id in data:
                    return data[prompt_id]
                await _async_sleep(poll_interval)
        raise ComfyUIError(f"生成超时 ({timeout}s)")

    async def download_output(
        self, filename: str, subfolder: str, output_type: str, save_path: str
    ) -> str:
        """下载生成的图片"""
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": output_type,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(f"{self.base_url}/view", params=params)
            if resp.status_code != 200:
                raise ComfyUIError(f"下载失败: {resp.text}")
            Path(save_path).write_bytes(resp.content)
            return make_background_transparent(save_path)

    async def generate(
        self,
        workflow_name: str,
        overrides: dict | None = None,
        output_path: str | None = None,
    ) -> dict:
        """
        完整生成流程：加载工作流 → 应用覆盖 → 提交 → 等待 → 下载
        返回 {"file_path": str, "duration": float, "prompt_id": str}
        """
        workflow = await self.load_workflow(workflow_name)
        if overrides:
            workflow = _apply_overrides(workflow, overrides)

        start_time = time.time()
        prompt_id = await self.queue_prompt(workflow)
        result = await self.wait_for_result(prompt_id)
        duration = time.time() - start_time

        # 提取输出文件
        outputs = result.get("outputs", {})
        file_path = ""
        for node_id, node_output in outputs.items():
            images = node_output.get("images", [])
            if images:
                img = images[0]
                if output_path:
                    file_path = await self.download_output(
                        img["filename"], img.get("subfolder", ""),
                        img.get("type", "output"), output_path
                    )
                break

        if not file_path:
            raise ComfyUIError("ComfyUI 生成完成，但未返回可下载图片")

        return {
            "file_path": file_path,
            "duration": round(duration, 2),
            "prompt_id": prompt_id,
        }


# ==================== Mock 模式 ====================

class MockComfyUIService(ComfyUIService):
    """Mock 实现 — ComfyUI 不可用时使用"""

    async def health_check(self) -> bool:
        return False  # Mock 表示不可用

    async def generate(
        self,
        workflow_name: str,
        overrides: dict | None = None,
        output_path: str | None = None,
    ) -> dict:
        """Mock 生成：创建占位图片"""
        from PIL import Image, ImageDraw, ImageFont

        width, height = 512, 512
        img = Image.new("RGB", (width, height), color=(240, 240, 245))
        draw = ImageDraw.Draw(img)

        # 绘制占位信息
        draw.rectangle([50, 180, 462, 350], outline=(180, 180, 200), width=3)
        draw.text(
            (256, 200), "CuddleKine",
            fill=(100, 100, 120), anchor="mt",
        )
        draw.text(
            (256, 240), f"工作流: {workflow_name}",
            fill=(130, 130, 150), anchor="mt",
        )
        draw.text(
            (256, 280), "[Mock 占位图 — ComfyUI 未就绪]",
            fill=(150, 150, 170), anchor="mt",
        )
        draw.text(
            (256, 320), "请配置 ComfyUI 后重新生成",
            fill=(150, 150, 170), anchor="mt",
        )

        path = Path(output_path) if output_path else Path("output.png")
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path)

        import time
        return {
            "file_path": str(path),
            "duration": round(time.time() - time.time() + 0.5, 2),
            "prompt_id": "mock-0000",
        }


def _apply_overrides(workflow: dict, overrides: dict) -> dict:
    """将覆盖参数应用到工作流"""
    result = dict(workflow)
    for node_id, params in overrides.items():
        if node_id in result:
            result[node_id]["inputs"].update(params)
    return result


async def _async_sleep(seconds: float):
    import asyncio
    await asyncio.sleep(seconds)
