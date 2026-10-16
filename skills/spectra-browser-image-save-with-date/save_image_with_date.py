#!/usr/bin/env python3
"""Save extracted browser images into date-wise folders with proper names.
Base: D:/Company work/research/spectra-browser-mcp-main/Download Image with date
Structure: <base>/YYYY-MM-DD/<sanitized-name>_HHMMSS.<ext>
Avoids generic names like gpt.png / image.png that cause confusion.
Usage:
  python save_image_with_date.py <source_file> --name "diwali-poster" [--date 2026-10-09] [--base "D:/Company work/.../Download Image with date"] [--move]
  python save_image_with_date.py --batch "D:/path/to/extracted_images" --name "chatgpt-banner"
"""
import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("D:/Company work/research/spectra-browser-mcp-main/Download Image with date")
GENERIC_NAMES = {"gpt", "chatgpt", "image", "img", "download", "screenshot", "untitled", "generated-image"}

def sanitize_name(name: str) -> str:
    name = (name or "").strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    name = re.sub(r"-{2,}", "-", name)
    words = [w for w in name.split("-") if w]
    # drop pure-generic single words -> force descriptive fallback
    if len(words) <= 1 and name in GENERIC_NAMES:
        raise ValueError(f"Too generic name '{name}'. Give 3-5 word descriptive name, e.g. 'diwali-sale-poster'.")
    if len(words) > 6:
        words = words[:6]
    clean = "-".join(words) or "browser-image"
    return clean[:80]

def dated_folder(base: Path, date_str: str | None) -> Path:
    d = date_str or datetime.now().strftime("%Y-%m-%d")
    # validate YYYY-MM-DD
    datetime.strptime(d, "%Y-%m-%d")
    folder = base / d
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def save_one(src: Path, name: str, base: Path, date_str: str | None, move: bool) -> Path:
    if not src.is_file():
        raise FileNotFoundError(f"Source not found: {src}")
    clean = sanitize_name(name)
    folder = dated_folder(base, date_str)
    stamp = datetime.now().strftime("%H%M%S")
    dest = folder / f"{clean}_{stamp}{src.suffix.lower() or '.png'}"
    i = 1
    while dest.exists():
        dest = folder / f"{clean}_{stamp}_{i}{src.suffix.lower() or '.png'}"
        i += 1
    if move:
        shutil.move(str(src), str(dest))
    else:
        shutil.copy2(str(src), str(dest))
    return dest

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", nargs="?", help="Single image file to save")
    ap.add_argument("--batch", default=None, help="Folder of images to save (all files)")
    ap.add_argument("--name", required=True, help="Descriptive image name, 3-5 words, e.g. 'diwali-sale-poster'")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD, default today")
    ap.add_argument("--base", default=str(BASE_DIR))
    ap.add_argument("--move", action="store_true", help="Move instead of copy")
    args = ap.parse_args()
    base = Path(args.base)
    base.mkdir(parents=True, exist_ok=True)
    if args.batch:
        src_dir = Path(args.batch)
        outs = []
        for f in sorted(src_dir.glob("*.*")):
            if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and f.is_file():
                outs.append(save_one(f, args.name, base, args.date, args.move))
        print(f"Saved {len(outs)} file(s):")
        for o in outs:
            print(o.as_posix())
    elif args.source:
        out = save_one(Path(args.source), args.name, base, args.date, args.move)
        print(out.as_posix())
    else:
        ap.error("Provide source file or --batch folder")

if __name__ == "__main__":
    main()
