"""OCR 服务 — 提取图片中的文字"""
from pathlib import Path


def extract_text_from_image(file_path: str) -> str:
    """
    从图片中提取文字。
    当前为 mock 实现，后续接入 Tesseract 或 PaddleOCR。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    return f"[OCR 占位] 图片 '{path.name}' 的文字待提取"


def extract_text_from_file(file_path: str) -> str:
    """根据文件类型提取文字"""
    suffix = Path(file_path).suffix.lower()
    if suffix in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
        return extract_text_from_image(file_path)
    elif suffix == ".txt":
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")
    else:
        return f"[暂不支持的文件格式: {suffix}]"
