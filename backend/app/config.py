"""应用配置"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"


def _first_existing(*paths: str) -> Path:
    for path in paths:
        candidate = Path(path)
        if candidate.exists():
            return candidate
    return Path(paths[0])

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("PTD_DATABASE_URL", f"sqlite:///{DATA_DIR / 'orders.db'}")

# ComfyUI 配置
COMFYUI_BASE_URL = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
COMFYUI_WORKFLOW_DIR = BASE_DIR / "comfyui" / "workflows"
COMFYUI_DIR = Path(
    os.getenv(
        "COMFYUI_DIR",
        str(_first_existing(
            "E:/TaiShen/ComfyUI/resources/ComfyUI",
            "E:/TaiShen/ComfyUI_standalone/ComfyUI-master",
        )),
    )
)
COMFYUI_UV_EXE = Path(
    os.getenv(
        "COMFYUI_UV_EXE",
        str(_first_existing(
            "E:/TaiShen/ComfyUI/resources/uv/win/uv.exe",
            "E:/TaiShen/ComfyUI_standalone/python_embeded/python.exe",
        )),
    )
)
COMFYUI_INPUT_DIR = Path(
    os.getenv("COMFYUI_INPUT_DIR", str(COMFYUI_DIR / "input"))
)

# 服务配置
API_HOST = os.getenv("PTD_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("PTD_API_PORT", "8765"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "PTD_CORS_ORIGINS",
        "http://localhost:1420,http://127.0.0.1:1420,http://tauri.localhost,tauri://localhost",
    ).split(",")
    if origin.strip()
]

# 素材存储
MATERIAL_DIR = DATA_DIR / "materials"
GENERATED_DIR = OUTPUT_DIR / "generated"

MATERIAL_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = int(os.getenv("PTD_MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
ALLOWED_UPLOAD_EXTENSIONS = {
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
}

# ── 生成后端选择 ──────────────────────────────────
# 可选: openai | replicate | comfyui | mock
GENERATION_PROVIDER = os.getenv("PTD_GENERATION_PROVIDER", "comfyui")

# ── OpenAI / DALL·E 3 配置 ────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── Replicate 配置 ────────────────────────────────
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")

AGNES_API_KEY = os.getenv("AGNES_API_KEY", "")
AGNES_BASE_URL = os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")

# 文生图模型（主视图候选、多视图）
REPLICATE_MODEL_DEFAULT = os.getenv(
    "REPLICATE_MODEL_DEFAULT",
    "black-forest-labs/flux-dev",
)
# Flux 高质量模型（用于最终确认版）
REPLICATE_MODEL_FLUX = os.getenv(
    "REPLICATE_MODEL_FLUX",
    "black-forest-labs/flux-dev",
)
# 图生图模型（草图→效果图，含 ControlNet）
REPLICATE_MODEL_I2I = os.getenv(
    "REPLICATE_MODEL_I2I",
    "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
)
# Inpainting 模型（局部修改）
REPLICATE_MODEL_INPAINT = os.getenv(
    "REPLICATE_MODEL_INPAINT",
    "stability-ai/stable-diffusion-inpainting",
)

# 模型许可证白名单（商用许可审核通过的模型）
LICENSED_MODELS = [
    # 格式: "模型名称"
    # 评测通过后添加
]
