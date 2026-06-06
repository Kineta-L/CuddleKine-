"""文件服务路由 — 提供静态文件访问"""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from ..config import MATERIAL_DIR, GENERATED_DIR, OUTPUT_DIR

router = APIRouter(prefix="/api/file", tags=["文件服务"])

SAFE_ROOTS = [MATERIAL_DIR, GENERATED_DIR, OUTPUT_DIR]


@router.get("")
def serve_file(path: str = Query(...)):
    """提供本地文件访问（仅限素材、生成图、导出目录）"""
    file_path = Path(path).resolve()
    for root in SAFE_ROOTS:
        root_path = root.resolve()
        try:
            file_path.relative_to(root_path)
            if file_path.exists() and file_path.is_file():
                media_type = _guess_media_type(file_path.suffix)
                return FileResponse(str(file_path), media_type=media_type)
        except ValueError:
            continue
    raise HTTPException(status_code=404, detail="文件不存在或无权访问")


def _guess_media_type(suffix: str) -> str:
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
    }
    return mapping.get(suffix.lower(), "application/octet-stream")
