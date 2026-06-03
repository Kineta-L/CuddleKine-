"""导出服务 — 客户确认板 + 工厂资料包"""
import json
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from ..config import OUTPUT_DIR


def export_design_board(
    order_id: int,
    order_number: str,
    brief: dict,
    views: dict,
    main_path: str = "",
    order_info: dict | None = None,
    output_path: str | None = None,
) -> str:
    """
    导出客户确认板：主视图 + 正面/侧面/背面三视图 + 订单信息。
    Pillow 排版实现。
    """
    if not output_path:
        output_path = str(OUTPUT_DIR / f"board_{order_id}_{order_number}.png")

    # 加载图片
    main_img = None
    if main_path and Path(main_path).exists():
        main_img = Image.open(main_path).convert("RGB")

    view_images = {}
    for vn, vp in views.items():
        if vp and Path(vp).exists():
            view_images[vn] = Image.open(vp).convert("RGB")

    if not view_images and not main_img:
        return _generate_placeholder_board(output_path, order_number, brief)

    info = order_info or {}
    has_main = main_img is not None
    has_views = len(view_images) > 0

    # 布局
    card_w, card_h = 380, 380        # 每个视图卡片尺寸
    gap = 16
    pad = 32
    info_w = 300
    info_area_h = 120

    if has_main and has_views:
        cols = 1 + len(view_images)   # main + front/side/back
    elif has_main:
        cols = 1
    else:
        cols = len(view_images)

    total_w = pad * 2 + info_w + gap + card_w * cols + gap * (cols - 1) if has_main and has_views else (
        pad * 2 + card_w * cols + gap * (cols - 1)
    )
    total_h = pad * 2 + info_area_h + card_h + pad

    board = Image.new("RGB", (total_w, total_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(board)

    # 信息区
    lines = [f"订单: {order_number}"]
    if info.get("customer_name"):
        lines.append(f"客户: {info['customer_name']}")
    if info.get("character_type") or brief.get("character_type"):
        lines.append(f"角色: {info.get('character_type') or brief.get('character_type', '')}")
    if info.get("target_height"):
        lines.append(f"高度: {info['target_height']} cm")
    if info.get("colors"):
        lines.append(f"颜色: {info['colors']}")
    if info.get("material_preference"):
        lines.append(f"材质: {info['material_preference']}")
    if info.get("accessories"):
        lines.append(f"配件: {info['accessories']}")
    if info.get("key_features"):
        lines.append(f"关键特征: {info['key_features']}")

    # 标题
    draw.text((pad, pad), "客户确认板", fill=(30, 30, 40))
    draw.line([(pad, pad + 28), (pad + 100, pad + 28)], fill=(74, 74, 255), width=3)

    # 信息文字
    y = pad + 44
    for line in lines:
        draw.text((pad, y), line, fill=(60, 60, 70))
        y += 20

    # 视图区域
    content_x = pad + info_w + gap if (has_main and has_views) else pad
    content_y = pad + info_area_h

    view_order = ["front", "side", "back"]
    col = 0

    if has_main:
        # 主视图（更大）
        mw, mh = card_w, card_h
        main_resized = main_img.resize((mw, mh))
        board.paste(main_resized, (content_x, content_y))
        # 标签
        tx = content_x + mw // 2
        ty = content_y + mh + 6
        draw.text((tx, ty), "主视图 Main", fill=(80, 80, 80), anchor="mt")
        # 外框
        draw.rectangle([content_x - 2, content_y - 2, content_x + mw + 2, content_y + mh + 2], outline=(74, 74, 255), width=3)
        col = 1

    for vn in view_order:
        if vn in view_images:
            img = view_images[vn].resize((card_w, card_h))
            x = content_x + col * (card_w + gap)
            y = content_y
            board.paste(img, (x, y))
            draw.text((x + card_w // 2, y + card_h + 6),
                      {"front": "正面 Front", "side": "侧面 Side", "back": "背面 Back"}[vn],
                      fill=(80, 80, 80), anchor="mt")
            col += 1

    board.save(output_path, "PNG")
    return output_path


def _generate_placeholder_board(output_path: str, order_number: str, brief: dict) -> str:
    """生成占位确认板"""
    w, h = 1400, 600
    img = Image.new("RGB", (w, h), color=(250, 250, 252))
    draw = ImageDraw.Draw(img)
    draw.text((w // 2, 80), f"客户确认板 — {order_number}", fill=(60, 60, 70), anchor="mt")
    draw.text((w // 2, 200), "[请先生成主视图 + 正/侧/背三视图]", fill=(150, 150, 170), anchor="mt")
    draw.text((w // 2, 260), f"角色: {brief.get('character_type', '待确认')}", fill=(100, 100, 120), anchor="mt")
    img.save(output_path, "PNG")
    return output_path


def export_factory_package(
    order_id: int,
    order_number: str,
    brief: dict,
    views: dict,
    main_path: str,
    board_path: str,
    order_info: dict,
    output_path: str | None = None,
) -> str:
    """
    导出工厂打样资料包 ZIP。

    内容：
      01_brief.json          — 结构化需求
      02_customer_board.png  — 客户确认板
      03_main_sample.png     — 主视图
      04_front.png           — 正面
      05_side.png            — 侧面
      06_back.png             — 背面
      07_generation_history.json — 生成历史
      08_metadata.json       — 订单元数据
    """
    if not output_path:
        output_path = str(OUTPUT_DIR / f"package_{order_number}.zip")

    base = OUTPUT_DIR / f"package_{order_number}"
    base.mkdir(parents=True, exist_ok=True)

    files_written = 0

    # 01 — Brief JSON
    (base / "01_brief.json").write_text(
        json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    files_written += 1

    # 02 — 确认板
    if board_path and Path(board_path).exists():
        _copy_into(base / "02_customer_board.png", board_path)
        files_written += 1

    # 03 — 主视图
    if main_path and Path(main_path).exists():
        _copy_into(base / "03_main_sample.png", main_path)
        files_written += 1

    # 04/05/06 — 三视图
    for vn, fn in [("front", "04_front.png"), ("side", "05_side.png"), ("back", "06_back.png")]:
        if vn in views and views[vn] and Path(views[vn]).exists():
            _copy_into(base / fn, views[vn])
            files_written += 1

    # 07 — 生成历史（含所有版本记录摘要）
    (base / "07_generation_history.json").write_text(
        json.dumps({"order_id": order_id, "order_number": order_number, "views": views}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    files_written += 1

    # 08 — 元数据
    meta = {
        "order_id": order_id,
        "order_number": order_number,
        "customer_name": order_info.get("customer_name", ""),
        "character_type": order_info.get("character_type", ""),
        "target_height": order_info.get("target_height"),
        "colors": order_info.get("colors", ""),
        "material_preference": order_info.get("material_preference", ""),
        "accessories": order_info.get("accessories", ""),
        "key_features": order_info.get("key_features", ""),
        "brief": brief,
        "exported_at": str(__import__("datetime").datetime.now()),
    }
    (base / "08_metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    files_written += 1

    # 打包 ZIP
    import shutil
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(base.glob("*")):
            if f.is_file():
                zf.write(f, f.name)

    # 清理临时目录
    shutil.rmtree(base, ignore_errors=True)

    return output_path


def _copy_into(dst: Path, src: str):
    """简单复制，覆盖已存在文件"""
    import shutil
    shutil.copy(src, dst)
