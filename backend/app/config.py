"""Application configuration."""
import os
from pathlib import Path

BASE_DIR = Path(os.getenv("CUDDLEKINE_APP_ROOT", str(Path(__file__).resolve().parent.parent.parent)))
RESOURCE_DIR = Path(os.getenv("CUDDLEKINE_RESOURCE_DIR", str(BASE_DIR)))
DATA_DIR = Path(os.getenv("CUDDLEKINE_DATA_DIR", str(BASE_DIR / "data")))
OUTPUT_DIR = Path(os.getenv("CUDDLEKINE_OUTPUT_DIR", str(BASE_DIR / "outputs")))


def _first_existing(*paths: str) -> Path:
    for path in paths:
        candidate = Path(path)
        if candidate.exists():
            return candidate
    return Path(paths[0])


# Ensure local storage directories exist.
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("PTD_DATABASE_URL", f"sqlite:///{DATA_DIR / 'orders.db'}")

# ComfyUI configuration.
COMFYUI_BASE_URL = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
COMFYUI_WORKFLOW_DIR = Path(
    os.getenv("COMFYUI_WORKFLOW_DIR", str(RESOURCE_DIR / "comfyui" / "workflows"))
)
COMFYUI_DIR = Path(
    os.getenv(
        "COMFYUI_DIR",
        str(
            _first_existing(
                "E:/TaiShen/ComfyUI/resources/ComfyUI",
                "E:/TaiShen/ComfyUI_standalone/ComfyUI-master",
            )
        ),
    )
)
COMFYUI_UV_EXE = Path(
    os.getenv(
        "COMFYUI_UV_EXE",
        str(
            _first_existing(
                "E:/TaiShen/ComfyUI/resources/uv/win/uv.exe",
                "E:/TaiShen/ComfyUI_standalone/python_embeded/python.exe",
            )
        ),
    )
)
COMFYUI_INPUT_DIR = Path(os.getenv("COMFYUI_INPUT_DIR", str(COMFYUI_DIR / "input")))

# API server configuration.
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

# Material and generated image storage.
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

# Generation provider selection: openai | replicate | comfyui | mock | agnes.
GENERATION_PROVIDER = os.getenv("PTD_GENERATION_PROVIDER", "comfyui")

# OpenAI configuration.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Replicate and Agnes configuration.
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "")
AGNES_BASE_URL = os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")

# Text-to-image model used for main candidates and multiview generation.
REPLICATE_MODEL_DEFAULT = os.getenv(
    "REPLICATE_MODEL_DEFAULT",
    "black-forest-labs/flux-dev",
)
# High-quality Flux model used for confirmed versions.
REPLICATE_MODEL_FLUX = os.getenv(
    "REPLICATE_MODEL_FLUX",
    "black-forest-labs/flux-dev",
)
# Image-to-image model used for sketch/reference to sample conversion.
REPLICATE_MODEL_I2I = os.getenv(
    "REPLICATE_MODEL_I2I",
    "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
)
# Inpainting model used for local revisions.
REPLICATE_MODEL_INPAINT = os.getenv(
    "REPLICATE_MODEL_INPAINT",
    "stability-ai/stable-diffusion-inpainting",
)

# Commercially approved model allowlist.
LICENSED_MODELS = [
    # Format: "model-name"
    # Add models after review.
]
