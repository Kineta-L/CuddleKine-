"""Export service for customer previews and factory handoff files."""
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..config import OUTPUT_DIR


VIEW_LABELS = {
    "front": "正面 Front",
    "side": "侧面 Side",
    "back": "背面 Back",
}


def export_design_board(
    order_id: int,
    order_number: str,
    brief: dict,
    views: dict,
    main_path: str = "",
    order_info: dict | None = None,
    output_path: str | None = None,
) -> str:
    """Export the customer-facing board: main sample plus front/side/back only."""
    if not output_path:
        output_path = str(OUTPUT_DIR / f"board_{order_id}_{order_number}.png")

    main_img = _open_rgb(main_path)
    view_images = {name: img for name, img in ((name, _open_rgb(path)) for name, path in views.items()) if img}

    if not view_images and not main_img:
        return _generate_placeholder_board(output_path, order_number, brief)

    card_w, card_h = 360, 480
    gap = 22
    pad = 42
    title_h = 86
    ordered_images: list[tuple[str, Image.Image]] = []
    if main_img:
        ordered_images.append(("主图 Main", main_img))
    for name in ("front", "side", "back"):
        if name in view_images:
            ordered_images.append((VIEW_LABELS[name], view_images[name]))

    total_w = pad * 2 + len(ordered_images) * card_w + max(0, len(ordered_images) - 1) * gap
    total_h = pad * 2 + title_h + card_h + 42

    board = Image.new("RGB", (total_w, total_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(board)
    title_font = _font(30)
    text_font = _font(17)

    draw.text((pad, pad), "客户确认图", fill=(24, 24, 30), font=title_font)
    draw.text((pad, pad + 42), f"订单 {order_number}", fill=(90, 90, 105), font=text_font)
    draw.line([(pad, pad + 72), (total_w - pad, pad + 72)], fill=(226, 226, 234), width=2)

    y = pad + title_h
    for index, (label, img) in enumerate(ordered_images):
        x = pad + index * (card_w + gap)
        fitted, offset = _fit_image(img, (card_w, card_h), background=(255, 255, 255))
        board.paste(fitted, (x + offset[0], y + offset[1]))
        draw.rectangle([x, y, x + card_w, y + card_h], outline=(232, 232, 238), width=2)
        draw.text((x + card_w // 2, y + card_h + 12), label, fill=(75, 75, 88), anchor="mt", font=text_font)

    board.save(output_path, "PNG")
    return output_path


def export_factory_pdf(
    order_id: int,
    order_number: str,
    brief: dict,
    views: dict,
    main_path: str = "",
    order_info: dict | None = None,
    output_path: str | None = None,
) -> str:
    """Export a factory-facing PDF. Empty optional fields are intentionally hidden."""
    if not output_path:
        output_path = str(OUTPUT_DIR / f"factory_sheet_{order_number}.pdf")

    info = order_info or {}
    main_img = _open_rgb(main_path)
    view_images = {name: img for name, img in ((name, _open_rgb(path)) for name, path in views.items()) if img}
    fields = _factory_fields(info, brief)

    pages = [
        _factory_cover_page(order_number, main_img, fields),
        _factory_views_page(order_number, view_images),
    ]
    if fields:
        pages.append(_factory_detail_page(order_number, fields))

    first, *rest = pages
    first.save(output_path, "PDF", save_all=True, append_images=rest, resolution=144.0)
    return output_path


def export_factory_package(
    order_id: int,
    order_number: str,
    brief: dict,
    views: dict,
    main_path: str,
    board_path: str = "",
    order_info: dict | None = None,
    factory_pdf_path: str = "",
    output_path: str | None = None,
) -> str:
    """Export a ZIP for factory handoff: PDF, original images, brief and metadata."""
    if not output_path:
        output_path = str(OUTPUT_DIR / f"package_{order_number}.zip")

    info = order_info or {}
    if not factory_pdf_path:
        factory_pdf_path = export_factory_pdf(order_id, order_number, brief, views, main_path, info)

    base = OUTPUT_DIR / f"package_{order_number}"
    base.mkdir(parents=True, exist_ok=True)

    (base / "01_brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    if factory_pdf_path and Path(factory_pdf_path).exists():
        _copy_into(base / "02_factory_sheet.pdf", factory_pdf_path)
    if main_path and Path(main_path).exists():
        _copy_into(base / "03_main_sample.png", main_path)

    for view_name, filename in [("front", "04_front.png"), ("side", "05_side.png"), ("back", "06_back.png")]:
        if view_name in views and views[view_name] and Path(views[view_name]).exists():
            _copy_into(base / filename, views[view_name])

    (base / "07_generation_history.json").write_text(
        json.dumps({"order_id": order_id, "order_number": order_number, "views": views}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    meta = {
        "order_id": order_id,
        "order_number": order_number,
        "customer_name": info.get("customer_name", ""),
        "character_type": info.get("character_type", ""),
        "target_height": info.get("target_height"),
        "colors": info.get("colors", ""),
        "material_preference": info.get("material_preference", ""),
        "accessories": info.get("accessories", ""),
        "key_features": info.get("key_features", ""),
        "main_proportions": info.get("main_proportions", ""),
        "allowed_simplifications": info.get("allowed_simplifications", ""),
        "pending_items": info.get("pending_items", ""),
        "craft_notes": info.get("craft_notes", ""),
        "brief": brief,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
    }
    (base / "08_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(base.glob("*")):
            if file_path.is_file():
                zf.write(file_path, file_path.name)

    shutil.rmtree(base, ignore_errors=True)
    return output_path


def _factory_cover_page(order_number: str, main_img: Image.Image | None, fields: list[tuple[str, str]]) -> Image.Image:
    page = _new_page()
    draw = ImageDraw.Draw(page)
    title_font = _font(42)
    text_font = _font(22)
    small_font = _font(18)

    draw.text((70, 60), "工厂生产资料", fill=(22, 22, 28), font=title_font)
    draw.text((70, 116), f"订单 {order_number}", fill=(78, 78, 92), font=text_font)
    draw.text((70, 152), f"导出时间 {datetime.now().strftime('%Y-%m-%d %H:%M')}", fill=(120, 120, 132), font=small_font)
    draw.line([(70, 190), (1120, 190)], fill=(222, 222, 230), width=2)

    if main_img:
        _paste_fit(page, main_img, (70, 230, 680, 1030))
    else:
        _draw_empty_box(draw, (70, 230, 680, 1030), "未生成主图")

    draw.text((730, 240), "已填写信息", fill=(40, 40, 52), font=_font(28))
    if fields:
        y = 292
        for label, value in fields[:10]:
            y = _draw_wrapped_field(draw, label, value, 730, y, 360, text_font, small_font)
            y += 10
            if y > 1000:
                break
    else:
        draw.text((730, 300), "当前没有填写生产细节。PDF 仅保留图片参考。", fill=(110, 110, 122), font=small_font)

    return page


def _factory_views_page(order_number: str, view_images: dict[str, Image.Image]) -> Image.Image:
    page = _new_page()
    draw = ImageDraw.Draw(page)
    draw.text((70, 60), "三视图参考", fill=(22, 22, 28), font=_font(40))
    draw.text((70, 112), f"订单 {order_number}", fill=(78, 78, 92), font=_font(21))
    draw.line([(70, 152), (1120, 152)], fill=(222, 222, 230), width=2)

    boxes = {
        "front": (70, 200, 395, 965),
        "side": (430, 200, 755, 965),
        "back": (790, 200, 1115, 965),
    }
    for name, box in boxes.items():
        if name in view_images:
            _paste_fit(page, view_images[name], box)
        else:
            _draw_empty_box(draw, box, f"缺少{VIEW_LABELS[name]}")
        draw.text(((box[0] + box[2]) // 2, box[3] + 20), VIEW_LABELS[name], fill=(75, 75, 88), anchor="mt", font=_font(20))

    return page


def _factory_detail_page(order_number: str, fields: list[tuple[str, str]]) -> Image.Image:
    page = _new_page()
    draw = ImageDraw.Draw(page)
    draw.text((70, 60), "生产备注", fill=(22, 22, 28), font=_font(40))
    draw.text((70, 112), f"订单 {order_number}", fill=(78, 78, 92), font=_font(21))
    draw.line([(70, 152), (1120, 152)], fill=(222, 222, 230), width=2)

    y = 198
    for label, value in fields:
        y = _draw_wrapped_field(draw, label, value, 80, y, 980, _font(22), _font(19))
        y += 18
        if y > 1030:
            break
    return page


def _factory_fields(order_info: dict, brief: dict) -> list[tuple[str, str]]:
    specs = [
        ("客户", "customer_name", ("customer_name",)),
        ("角色类型", "character_type", ("character_type",)),
        ("目标高度", "target_height", ("target_height",)),
        ("整体比例", "main_proportions", ("main_proportions", "body_proportions", "proportions")),
        ("颜色", "colors", ("colors", "color_palette")),
        ("建议材质", "material_preference", ("material_preference", "materials", "fabric")),
        ("配件", "accessories", ("accessories",)),
        ("关键特征", "key_features", ("key_features", "key_features_to_preserve")),
        ("可简化项", "allowed_simplifications", ("allowed_simplifications",)),
        ("工艺备注", "craft_notes", ("craft_notes", "manufacturing_suggestions", "craft")),
        ("待确认项", "pending_items", ("pending_items", "open_questions")),
    ]
    result = []
    for label, order_key, brief_keys in specs:
        value = _first_value(order_info.get(order_key), *(brief.get(key) for key in brief_keys))
        if value:
            if order_key == "target_height" and isinstance(value, (int, float)):
                value = f"{value:g} cm"
            result.append((label, str(value)))
    return result


def _first_value(*values) -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            value = "、".join(str(item) for item in value if str(item).strip())
        elif isinstance(value, dict):
            value = "；".join(f"{key}: {val}" for key, val in value.items() if str(val).strip())
        else:
            value = str(value)
        if value.strip():
            return value.strip()
    return ""


def _draw_wrapped_field(draw: ImageDraw.ImageDraw, label: str, value: str, x: int, y: int, width: int, label_font, text_font) -> int:
    draw.text((x, y), label, fill=(42, 42, 54), font=label_font)
    y += 30
    for line in _wrap_text(value, width, text_font, draw):
        draw.text((x, y), line, fill=(92, 92, 106), font=text_font)
        y += 26
    return y


def _wrap_text(text: str, width: int, font, draw: ImageDraw.ImageDraw) -> list[str]:
    lines: list[str] = []
    for raw in str(text).splitlines() or [""]:
        current = ""
        for char in raw:
            trial = current + char
            if draw.textlength(trial, font=font) <= width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = char
        if current:
            lines.append(current)
    return lines or [""]


def _new_page() -> Image.Image:
    return Image.new("RGB", (1190, 1120), color=(255, 255, 255))


def _paste_fit(page: Image.Image, img: Image.Image, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    draw = ImageDraw.Draw(page)
    draw.rectangle([x1, y1, x2, y2], outline=(230, 230, 236), width=2)
    fitted, offset = _fit_image(img, (x2 - x1, y2 - y1), background=(255, 255, 255))
    page.paste(fitted, (x1 + offset[0], y1 + offset[1]))


def _draw_empty_box(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str) -> None:
    draw.rectangle(box, outline=(230, 230, 236), width=2)
    draw.text(((box[0] + box[2]) // 2, (box[1] + box[3]) // 2), label, fill=(150, 150, 162), anchor="mm", font=_font(20))


def _open_rgb(path: str | None) -> Image.Image | None:
    if path and Path(path).exists():
        return Image.open(path).convert("RGB")
    return None


def _fit_image(
    img: Image.Image,
    box: tuple[int, int],
    background: tuple[int, int, int] = (255, 255, 255),
) -> tuple[Image.Image, tuple[int, int]]:
    """Scale into a box without stretching, cropping, or changing proportions."""
    box_w, box_h = box
    src_w, src_h = img.size
    if src_w <= 0 or src_h <= 0:
        return Image.new("RGB", box, color=background), (0, 0)
    scale = min(box_w / src_w, box_h / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    return resized, ((box_w - new_w) // 2, (box_h - new_h) // 2)


def _generate_placeholder_board(output_path: str, order_number: str, brief: dict) -> str:
    w, h = 1400, 620
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((w // 2, 100), f"客户确认图 - {order_number}", fill=(60, 60, 70), anchor="mt", font=_font(30))
    draw.text((w // 2, 245), "请先生成主图和三视图", fill=(150, 150, 170), anchor="mt", font=_font(22))
    if brief.get("character_type"):
        draw.text((w // 2, 292), f"角色: {brief.get('character_type')}", fill=(100, 100, 120), anchor="mt", font=_font(18))
    img.save(output_path, "PNG")
    return output_path


def _font(size: int):
    for path in (
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _copy_into(dst: Path, src: str) -> None:
    """Copy a file and overwrite any previous export artifact."""
    shutil.copy(src, dst)
