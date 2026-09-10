"""
=============================================================================
🖼️ SpectraBrowser MCP — Media Optimizer & Smart Canvas Engine
=============================================================================
Optimizes raw heavy screenshots and extracted web images (ChatGPT, websites)
for target distribution platforms:
- INSTAGRAM (1080x1350 4:5 portrait with smart canvas fitting)
- STORY / REEL (1080x1920 9:16 vertical full screen)
- SQUARE (1080x1080 1:1 feed)
- EMAIL (Max 650px width, crisp downscale, < 150 KB for instant Gmail opening)
- BLOG / OG (1200x630 OpenGraph / Landscape hero)
- THUMBNAIL (1280x720 16:9 landscape)
- CUSTOM (user-defined width x height)

Progressively compresses down to target file size (default <= 200 KB) in WEBP / JPEG / PNG.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from PIL import Image, ImageOps

from browser_qa.config import SCREENSHOTS_DIR

OPTIMIZED_DIR = SCREENSHOTS_DIR / "optimized"
OPTIMIZED_DIR.mkdir(parents=True, exist_ok=True)


def parse_color(color: Union[str, Tuple[int, int, int]]) -> Tuple[int, int, int]:
    """Parses hex code string or RGB tuple into (R, G, B)."""
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        return (int(color[0]), int(color[1]), int(color[2]))
    if isinstance(color, str):
        c = color.strip().lstrip("#")
        if len(c) == 6:
            return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
        elif len(c) == 3:
            return (int(c[0]*2, 16), int(c[1]*2, 16), int(c[2]*2, 16))
    return (15, 23, 42)  # Default Slate Navy (#0F172A)


def get_image_size_kb(filepath: Path) -> float:
    """Returns file size in kilobytes."""
    return round(filepath.stat().st_size / 1024.0, 2)


def fit_to_canvas(
    img: Image.Image,
    target_width: int,
    target_height: int,
    background_color: Union[str, Tuple[int, int, int]] = (15, 23, 42)
) -> Image.Image:
    """
    Fits image into exact dimensions without destructive cropping:
    Scales image to fit within bounds, creates canvas, and centers cleanly.
    """
    bg_rgb = parse_color(background_color)
    canvas = Image.new("RGB", (target_width, target_height), bg_rgb)

    src_w, src_h = img.size
    ratio = min(target_width / max(1, src_w), target_height / max(1, src_h))
    new_w = max(1, int(src_w * ratio))
    new_h = max(1, int(src_h * ratio))

    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    offset_x = (target_width - new_w) // 2
    offset_y = (target_height - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas


def optimize_image(
    image_path: str,
    platform: str = "INSTAGRAM",
    max_size_kb: int = 200,
    output_format: str = "WEBP",
    background_color: str = "#0F172A",
    custom_width: Optional[int] = None,
    custom_height: Optional[int] = None,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Processes local image file, resizes to platform dimensions, and compresses to target size.
    Supported platforms: 'INSTAGRAM', 'STORY', 'SQUARE', 'EMAIL', 'BLOG', 'THUMBNAIL', 'CUSTOM'
    """
    src_path = Path(str(image_path).strip().replace('"', '').replace("'", ""))
    if not src_path.exists():
        return {
            "status": "error",
            "error": f"Image file not found at path: {src_path}"
        }

    orig_size_kb = get_image_size_kb(src_path)
    clean_platform = platform.upper().strip()
    clean_format = output_format.upper().strip()
    if clean_format not in ("WEBP", "JPEG", "JPG", "PNG"):
        clean_format = "WEBP"
    ext = "webp" if clean_format == "WEBP" else "jpg" if clean_format in ("JPEG", "JPG") else "png"

    target_out_dir = Path(output_dir) if output_dir else OPTIMIZED_DIR
    target_out_dir.mkdir(parents=True, exist_ok=True)

    try:
        with Image.open(src_path) as raw_img:
            # Auto-orient based on EXIF tag
            img = ImageOps.exif_transpose(raw_img)

            # Convert RGBA / P to RGB
            bg_rgb = parse_color(background_color)
            if img.mode in ("RGBA", "LA", "P"):
                rgb_img = Image.new("RGB", img.size, bg_rgb)
                if img.mode == "P":
                    img = img.convert("RGBA")
                rgb_img.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                img = rgb_img
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Apply Platform Presets
            if clean_platform in ("INSTAGRAM", "INSTA", "FEED"):
                # Standard 4:5 Portrait Feed (1080x1350)
                processed_img = fit_to_canvas(img, 1080, 1350, background_color)

            elif clean_platform in ("STORY", "REEL", "STATUS"):
                # 9:16 Vertical (1080x1920)
                processed_img = fit_to_canvas(img, 1080, 1920, background_color)

            elif clean_platform in ("SQUARE", "POST_1X1"):
                # 1:1 Square (1080x1080)
                processed_img = fit_to_canvas(img, 1080, 1080, background_color)

            elif clean_platform in ("EMAIL", "NEWSLETTER"):
                # Email Max Width 650px, proportional height
                target_w = 650
                ratio = target_w / float(img.size[0])
                target_h = max(1, int(float(img.size[1]) * ratio))
                processed_img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

            elif clean_platform in ("BLOG", "HERO", "OG", "OPENGRAPH"):
                # OpenGraph / Blog Standard (1200x630)
                processed_img = fit_to_canvas(img, 1200, 630, background_color)

            elif clean_platform in ("THUMBNAIL", "YOUTUBE", "BANNER"):
                # 16:9 Landscape (1280x720)
                processed_img = fit_to_canvas(img, 1280, 720, background_color)

            elif clean_platform == "CUSTOM" and custom_width and custom_height:
                processed_img = fit_to_canvas(img, int(custom_width), int(custom_height), background_color)

            else:
                # Custom/Default: Max dimension 1200px
                max_dim = 1200
                scale = min(1.0, max_dim / max(img.size[0], img.size[1]))
                new_size = (max(1, int(img.size[0] * scale)), max(1, int(img.size[1] * scale)))
                processed_img = img.resize(new_size, Image.Resampling.LANCZOS)

            stem = src_path.stem.replace(" ", "_")[:30]
            out_filename = f"{clean_platform.lower()}_{stem}_{int(time.time())}.{ext}"
            out_path = target_out_dir / out_filename

            # Progressive Compression Loop to reach target max_size_kb
            quality = 85
            while quality >= 40:
                if clean_format == "WEBP":
                    processed_img.save(out_path, format="WEBP", quality=quality, method=4)
                elif clean_format in ("JPEG", "JPG"):
                    processed_img.save(out_path, format="JPEG", quality=quality, optimize=True)
                else:
                    processed_img.save(out_path, format="PNG", optimize=True)
                    break

                current_kb = get_image_size_kb(out_path)
                if current_kb <= max_size_kb or quality <= 45:
                    break
                quality -= 8

            new_size_kb = get_image_size_kb(out_path)
            compression_ratio = round((1.0 - (new_size_kb / max(0.1, orig_size_kb))) * 100.0, 1)
            posix_path = out_path.as_posix()

            return {
                "status": "success",
                "platform": clean_platform,
                "optimized_image_path": str(out_path),
                "normalized_path": posix_path,
                "markdown_link": f"![Optimized Image](file:///{posix_path})",
                "original_size_kb": orig_size_kb,
                "optimized_size_kb": new_size_kb,
                "compression_reduction_percent": f"{compression_ratio}%",
                "dimensions": f"{processed_img.size[0]}x{processed_img.size[1]}",
                "format": clean_format
            }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to optimize image: {str(e)}"
        }


def optimize_batch(
    source_dir_or_files: Optional[Union[str, List[str]]] = None,
    platform: str = "INSTAGRAM",
    max_size_kb: int = 200,
    output_format: str = "WEBP",
    background_color: str = "#0F172A"
) -> Dict[str, Any]:
    """
    Optimizes multiple images in a directory or file list.
    If source_dir_or_files is None, it scans SCREENSHOTS_DIR / 'extracted_images'.
    """
    files_to_process: List[Path] = []

    if source_dir_or_files is None:
        extracted_dir = SCREENSHOTS_DIR / "extracted_images"
        if extracted_dir.exists():
            for f in extracted_dir.glob("*.*"):
                if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                    files_to_process.append(f)
    elif isinstance(source_dir_or_files, list):
        for item in source_dir_or_files:
            p = Path(item)
            if p.is_file():
                files_to_process.append(p)
    elif isinstance(source_dir_or_files, str):
        p = Path(source_dir_or_files)
        if p.is_dir():
            for f in p.glob("*.*"):
                if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                    files_to_process.append(f)
        elif p.is_file():
            files_to_process.append(p)

    if not files_to_process:
        return {
            "status": "success",
            "message": "No images found to optimize.",
            "total_processed": 0,
            "results": []
        }

    results = []
    total_saved_kb = 0.0

    for file_path in files_to_process:
        res = optimize_image(
            image_path=str(file_path),
            platform=platform,
            max_size_kb=max_size_kb,
            output_format=output_format,
            background_color=background_color
        )
        if res.get("status") == "success":
            diff = res.get("original_size_kb", 0) - res.get("optimized_size_kb", 0)
            total_saved_kb += max(0.0, diff)
        results.append(res)

    return {
        "status": "success",
        "total_processed": len(results),
        "total_saved_kb": round(total_saved_kb, 2),
        "results": results
    }
