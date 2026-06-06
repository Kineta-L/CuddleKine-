"""ImageProvider 抽象基类 + 统一数据模型"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ── 统一数据模型 ──────────────────────────────────

@dataclass
class GenerateJob:
    """统一生成请求——所有 provider 通用"""
    order_id: int
    provider: str = "comfyui"          # provider id
    model: str = ""                     # 具体模型名
    quality_mode: str = "sample"        # draft | sample | final
    prompt: str = ""
    negative_prompt: str = ""
    view_type: str = "main"             # main | front | side | back
    derivation_type: str = "main_view_candidate"
    workflow_name: str = "main_view.json"
    source_version_id: Optional[int] = None
    reference_material_id: Optional[int] = None
    reference_images: list[str] = field(default_factory=list)  # 本地文件路径列表
    locked_regions: Optional[str] = None
    transparent_background: bool = False
    output_path: str = ""
    params: dict = field(default_factory=dict)    # 额外参数透传

    def to_overrides(self) -> dict:
        """转为 provider 通用的 overrides dict（兼容旧代码）"""
        return {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "model": self.model or None,
            "quality_mode": self.quality_mode,
            "view_type": self.view_type,
            "derivation_type": self.derivation_type,
            "reference_images": self.reference_images,
            "transparent_background": self.transparent_background,
            "num_outputs": 4 if self.derivation_type == "main_view_candidate" else 1,
            **self.params,
        }


@dataclass
class GenerateResult:
    """统一生成结果"""
    file_path: str = ""
    provider: str = ""
    model: str = ""
    duration: float = 0.0
    prompt: str = ""
    raw_response: str = ""              # API 原始响应 JSON 摘要
    cost_estimate: float = 0.0
    prompt_id: str = ""


@dataclass
class ProviderHealth:
    """Provider 健康状态"""
    available: bool = False
    message: str = ""
    configured: bool = False            # API Key / 路径是否已配


@dataclass
class ProviderInfo:
    """Provider 展示信息（用于 GET /api/providers）"""
    id: str
    name: str
    enabled: bool = True
    configured: bool = False
    supports_text_to_image: bool = True
    supports_image_to_image: bool = False
    supports_inpaint: bool = False
    supports_transparent_background: bool = False
    models: list[dict] = field(default_factory=list)


# ── 抽象基类 ─────────────────────────────────────

class ImageProvider(ABC):
    """所有图像生成 provider 的抽象基类"""

    id: str = ""
    name: str = ""
    supports_text_to_image: bool = True
    supports_image_to_image: bool = False
    supports_inpaint: bool = False
    supports_transparent_background: bool = False

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """检查 provider 是否可用"""
        ...

    @abstractmethod
    async def generate(self, job: GenerateJob) -> GenerateResult:
        """执行生成——所有 provider 统一入口"""
        ...
