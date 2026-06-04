#!/usr/bin/env python3
"""Turn a tall full-page screenshot into a small, crisp WebP thumbnail.

The BBW landing page only ever shows the *top* of each demo screenshot
(`object-fit: cover; object-position: top`), in two places:

  - portfolio card        16 / 10  (1.60)
  - hero browser mockup     4 / 3.1 (1.29, the taller crop)

Shipping the raw 2880xN full-page PNG (8-13 MB each) means the browser
downscales a ~14000px-tall image ~8x into a tiny card — slow *and* grainy.
This script crops the top region to the taller (4:3.1) consumer, downscales
to a sane display width, and encodes WebP. Result: ~100-250 KB, sharp.

    python scripts/web/make_thumb.py <src.png> <dest.webp>
    python scripts/web/make_thumb.py <src.png> <dest.webp> --width 1440 --quality 80

Requires `cwebp` (brew install webp) and `sips` (macOS, preinstalled).
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Tallest crop the page displays (hero browser mockup is 4 / 3.1). Cropping to
# this height covers both consumers; the wider 16:10 card just shows less of it.
CROP_ASPECT_W = 4.0
CROP_ASPECT_H = 3.1


def _require(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        sys.exit(f"make_thumb: missing required tool '{tool}'. brew install webp")
    return path


def _dimensions(src: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(src)],
        capture_output=True, text=True, check=True,
    ).stdout
    w = int(re.search(r"pixelWidth:\s*(\d+)", out).group(1))
    h = int(re.search(r"pixelHeight:\s*(\d+)", out).group(1))
    return w, h


def make_thumb(src: Path, dest: Path, *, width: int = 1440, quality: int = 80) -> Path:
    """Crop top, downscale, WebP-encode. Returns dest."""
    _require("cwebp")
    _require("sips")
    src_w, src_h = _dimensions(src)
    crop_h = min(src_h, round(src_w * CROP_ASPECT_H / CROP_ASPECT_W))
    dest.parent.mkdir(parents=True, exist_ok=True)
    # cwebp applies -crop before -resize, so we crop in source pixels then
    # downscale to the target display width (height auto from aspect: 0).
    subprocess.run(
        [
            "cwebp", "-quiet",
            "-crop", "0", "0", str(src_w), str(crop_h),
            "-resize", str(width), "0",
            "-q", str(quality),
            str(src), "-o", str(dest),
        ],
        check=True,
    )
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dest", type=Path)
    ap.add_argument("--width", type=int, default=1440, help="output display width (px)")
    ap.add_argument("--quality", type=int, default=80, help="WebP quality 0-100")
    args = ap.parse_args()
    if not args.src.is_file():
        sys.exit(f"make_thumb: no such file: {args.src}")
    out = make_thumb(args.src, args.dest, width=args.width, quality=args.quality)
    kb = out.stat().st_size / 1024
    print(f"✓ {args.src.name} → {out} ({kb:.0f} KB)")


if __name__ == "__main__":
    main()
