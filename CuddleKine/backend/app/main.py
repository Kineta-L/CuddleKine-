"""FastAPI 应用入口"""
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess
from .database import init_db
from .config import (
    API_HOST,
    API_PORT,
    COMFYUI_BASE_URL,
    COMFYUI_DIR,
    COMFYUI_INPUT_DIR,
    COMFYUI_UV_EXE,
    COMFYUI_WORKFLOW_DIR,
    CORS_ORIGINS,
    DATA_DIR,
    GENERATION_PROVIDER,
    OUTPUT_DIR,
)
from .services.comfyui_service import ComfyUIService
from .services.settings_service import get_comfyui_base_url, get_comfyui_input_dir, get_default_provider

app = FastAPI(
    title="CuddleKine",
    description="CuddleKine — 本地毛绒玩具打样工作台后端服务",
    version="0.1.0",
)

# CORS — 允许 Tauri 桌面端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from .routes import orders, materials, briefs, generation, export, files, settings

app.include_router(orders.router)
app.include_router(materials.router)
app.include_router(briefs.router)
app.include_router(generation.router)
app.include_router(export.router)
app.include_router(files.router)
app.include_router(settings.router)

_comfyui_process: subprocess.Popen | None = None


@app.on_event("startup")
def on_startup():
    """启动时初始化数据库"""
    init_db()


@app.get("/api/health")
def health_check():
    """健康检查"""
    return {"status": "ok", "service": "CuddleKine"}


@app.get("/api/status")
async def system_status():
    """桌面端启动页使用的系统状态"""
    comfyui_input_dir = get_comfyui_input_dir()
    comfyui_available = await ComfyUIService(get_comfyui_base_url()).health_check()
    return {
        "backend": {
            "status": "ok",
            "host": API_HOST,
            "port": API_PORT,
        },
        "generation": {
            "provider": get_default_provider(),
        },
        "comfyui": {
            "status": "ok" if comfyui_available else "offline",
            "base_url": COMFYUI_BASE_URL,
            "dir": str(COMFYUI_DIR),
            "dir_exists": COMFYUI_DIR.exists(),
            "uv_exe": str(COMFYUI_UV_EXE),
            "uv_exe_exists": COMFYUI_UV_EXE.exists(),
            "input_dir": str(comfyui_input_dir),
            "input_dir_exists": comfyui_input_dir.exists(),
            "workflow_dir": str(COMFYUI_WORKFLOW_DIR),
            "workflow_dir_exists": COMFYUI_WORKFLOW_DIR.exists(),
        },
        "storage": {
            "data_dir": str(DATA_DIR),
            "output_dir": str(OUTPUT_DIR),
            "data_dir_exists": DATA_DIR.exists(),
            "output_dir_exists": OUTPUT_DIR.exists(),
        },
    }


@app.post("/api/comfyui/start")
async def start_comfyui():
    """尝试启动本机 ComfyUI API 服务"""
    global _comfyui_process

    if await ComfyUIService(get_comfyui_base_url()).health_check():
        return {"status": "already_running", "message": "ComfyUI 已在线"}

    if _comfyui_process and _comfyui_process.poll() is None:
        return {"status": "starting", "message": "ComfyUI 正在启动"}

    if not COMFYUI_DIR.exists():
        return {
            "status": "error",
            "message": f"ComfyUI 目录不存在: {COMFYUI_DIR}",
        }

    if COMFYUI_UV_EXE.exists() and COMFYUI_UV_EXE.name.lower() == "uv.exe":
        command = [
            str(COMFYUI_UV_EXE),
            "run",
            "--directory",
            str(COMFYUI_DIR),
            "python",
            "main.py",
            "--listen",
            "0.0.0.0",
            "--port",
            "8188",
        ]
        cwd = COMFYUI_DIR
    else:
        command = [
            str(COMFYUI_UV_EXE) if COMFYUI_UV_EXE.exists() else "python",
            "main.py",
            "--listen",
            "0.0.0.0",
            "--port",
            "8188",
        ]
        cwd = COMFYUI_DIR

    creationflags = subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0
    try:
        _comfyui_process = subprocess.Popen(
            command,
            cwd=str(cwd),
            creationflags=creationflags,
        )
    except Exception as exc:
        return {"status": "error", "message": f"启动失败: {exc}"}

    return {
        "status": "starting",
        "message": "ComfyUI 启动中，请等待 10-30 秒后重试检测",
        "pid": _comfyui_process.pid,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
