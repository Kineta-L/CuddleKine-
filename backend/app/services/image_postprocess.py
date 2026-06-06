"""生成图片后处理"""
from collections import deque
from pathlib import Path
from PIL import Image, ImageFilter


TURNAROUND_CANVAS_SIZE = (1024, 1536)


def make_background_transparent(image_path: str, tolerance: int = 28) -> str:
    """将与图片边缘相连的纯色/浅色背景转为透明，并裁掉多余透明画布。"""
    path = Path(image_path)
    with Image.open(path) as img:
        rgba = _remove_edge_background(img.convert("RGBA"), tolerance)
        rgba = _crop_to_alpha(rgba, padding_ratio=0.04)
        rgba = _soften_alpha(rgba)
        rgba.save(path, "PNG")
    return str(path)


def prepare_reference_subject(
    source_path: str,
    output_path: str | Path,
    size: int = 1024,
    tolerance: int = 22,
) -> str:
    """从参考图中保守分离主体，居中放入白底方图供 img2img 使用。"""
    output = Path(output_path)
    with Image.open(source_path) as img:
        original = img.convert("RGBA")
        rgba = _remove_edge_background(original, tolerance)
        subject = _crop_to_alpha(rgba, padding_ratio=0.18)
        if _subject_area_ratio(subject) < 0.12:
            subject = original
        subject.thumbnail((int(size * 0.82), int(size * 0.82)), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
        x = (size - subject.width) // 2
        y = (size - subject.height) // 2
        canvas.alpha_composite(subject, (x, y))
        canvas.convert("RGB").save(output, "PNG")
    return str(output)


def normalize_turnaround_canvas(
    image_path: str,
    size: tuple[int, int] = TURNAROUND_CANVAS_SIZE,
    background: tuple[int, int, int, int] = (255, 255, 255, 255),
) -> str:
    """Center an output image on a fixed canvas without stretching its proportions."""
    path = Path(image_path)
    with Image.open(path) as img:
        subject = img.convert("RGBA")
        subject.thumbnail(size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", size, background)
        x = (size[0] - subject.width) // 2
        y = (size[1] - subject.height) // 2
        canvas.alpha_composite(subject, (x, y))
        canvas.convert("RGB").save(path, "PNG")
    return str(path)


def _subject_area_ratio(img: Image.Image) -> float:
    alpha = img.getchannel("A")
    visible = sum(1 for value in alpha.getdata() if value > 12)
    return visible / max(1, img.width * img.height)


def _remove_edge_background(img: Image.Image, tolerance: int) -> Image.Image:
    rgba = img.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    bg = _estimate_background_color(rgba)
    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(height):
        queue.append((0, y))
        queue.append((width - 1, y))

    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        visited.add((x, y))
        if not _is_background_pixel(pixels[x, y], bg, tolerance):
            continue
        pixels[x, y] = (pixels[x, y][0], pixels[x, y][1], pixels[x, y][2], 0)
        if x > 0:
            queue.append((x - 1, y))
        if x < width - 1:
            queue.append((x + 1, y))
        if y > 0:
            queue.append((x, y - 1))
        if y < height - 1:
            queue.append((x, y + 1))

    return rgba


def _crop_to_alpha(img: Image.Image, padding_ratio: float) -> Image.Image:
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        return img
    width, height = img.size
    left, top, right, bottom = bbox
    pad = int(max(right - left, bottom - top) * padding_ratio)
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(width, right + pad)
    bottom = min(height, bottom + pad)
    return img.crop((left, top, right, bottom))


def _soften_alpha(img: Image.Image) -> Image.Image:
    alpha = img.getchannel("A").filter(ImageFilter.GaussianBlur(radius=0.6))
    img.putalpha(alpha)
    return img


def _estimate_background_color(img: Image.Image) -> tuple[int, int, int]:
    width, height = img.size
    samples = []
    for x, y in (
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
        (width // 2, 0),
        (width // 2, height - 1),
        (0, height // 2),
        (width - 1, height // 2),
    ):
        samples.append(img.getpixel((x, y))[:3])
    return tuple(sorted(channel)[len(channel) // 2] for channel in zip(*samples))


def _is_background_pixel(
    pixel: tuple[int, int, int, int],
    bg: tuple[int, int, int],
    tolerance: int,
) -> bool:
    if pixel[3] == 0:
        return True
    return sum(abs(pixel[i] - bg[i]) for i in range(3)) <= tolerance * 3
