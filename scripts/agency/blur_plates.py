#!/usr/bin/env python3
"""Blur license plates (and other PII regions) into prospect demo-site photos.

Privacy/safety: gathered Google photos often show readable license plates. We bake
an irreversible blur+pixelate into the asset itself (NOT a CSS overlay) so plates
can't be recovered. Originals are backed up once to ``<assets>/_orig/`` so the op
is reproducible/reversible at source.

Regions are given as FRACTIONAL boxes (x0,y0,x1,y1 as fractions of width/height) so
they're resolution-independent — read them off any preview of the image.

One entry per site in SITES (keyed by place_id → assets dir + per-file boxes).
Edit/extend SITES below, then: python scripts/agency/blur_plates.py
"""
from __future__ import annotations
import shutil
from pathlib import Path
from PIL import Image, ImageFilter

SITES_ROOT = Path("/Users/kashane/dev/ai-company-os/state/prospects/sites")

# place_id -> { filename: [ (x0,y0,x1,y1) fractional boxes ] }
SITES: dict[str, dict[str, list[tuple[float, float, float, float]]]] = {
    # Motor City Auto Repair (Dallas)
    "ChIJoa9yFfaYToYRTQDyXQvKrEw": {
        "hero.jpg": [
            (0.66, 0.78, 0.80, 0.855),    # Bentley rear plate (center-bottom)
            (0.835, 0.585, 0.945, 0.642), # Porsche plate (right)
        ],
        "storefront-wide.jpg": [
            (0.555, 0.80, 0.672, 0.862),  # Bentley rear plate
            (0.722, 0.680, 0.822, 0.732), # Porsche plate
        ],
        "lift-bay.jpg": [
            (0.888, 0.556, 0.974, 0.606), # Lexus rear plate (far right of frame)
        ],
        "sign.jpg": [
            (0.215, 0.696, 0.328, 0.742), # green sedan front plate
            (0.560, 0.690, 0.678, 0.737), # black SUV rear plate
        ],
    },
    # Nashville Auto Care (Nashville) — auto branch
    # hero.jpg = storefront photo_01 cropped to drop the burned-in timestamp (top 90%).
    # counter.jpg = photo_03 cropped (x .06..1, y .02...71) to drop a customer's foot.
    # Run AFTER those crops exist so _orig backs up the cropped pristine versions.
    "ChIJf9s1im9oZIgRXrA7I4ooKY0": {
        "hero.jpg": [
            (0.378, 0.532, 0.428, 0.568),  # Chevy Avalanche rear plate (center)
            (0.383, 0.654, 0.425, 0.686),  # yellow plate lying on the wet lot
        ],
        "counter.jpg": [
            (0.525, 0.200, 0.615, 0.305),  # seated staff member's face (consent)
        ],
    },
    # Houston Mobile Mechanic & Diesel Repair (Houston)
    "ChIJcV_ilnrBQIYR62xFJZfYb-A": {
        "diesel-rig.jpg": [
            (0.335, 0.595, 0.485, 0.637),  # Peterbilt front plate (between OVER/SIZE)
        ],
        "night-work.jpg": [
            (0.165, 0.344, 0.250, 0.390),  # background grey Accord rear plate
            (0.010, 0.350, 0.085, 0.396),  # far-left dark blue sedan rear plate
        ],
        "fleet-work.jpg": [
            (0.035, 0.742, 0.155, 0.808),  # F-250 front bumper plate (lower-left)
        ],
    },
}


def obscure(img: Image.Image, box_frac: tuple[float, float, float, float]) -> None:
    w, h = img.size
    x0, y0, x1, y1 = box_frac
    px = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
    region = img.crop(px)
    # pixelate: downscale hard then upscale (destroys characters), then soften
    small = region.resize((max(1, region.width // 18), max(1, region.height // 18)), Image.BILINEAR)
    pix = small.resize(region.size, Image.NEAREST)
    pix = pix.filter(ImageFilter.GaussianBlur(6))
    img.paste(pix, px[:2])


def main() -> None:
    for place_id, regions in SITES.items():
        assets = SITES_ROOT / place_id / "dist-v2" / "assets"
        backup = assets / "_orig"
        backup.mkdir(parents=True, exist_ok=True)
        print(f"# {place_id}")
        for name, boxes in regions.items():
            src = assets / name
            if not src.is_file():
                print(f"  ! missing {name}")
                continue
            bak = backup / name
            if not bak.is_file():
                shutil.copy2(src, bak)  # one-time backup of the pristine original
            img = Image.open(bak).convert("RGB")  # always start from the pristine copy
            for b in boxes:
                obscure(img, b)
            # high quality + no chroma subsampling so the re-encode is visually lossless
            # (only the plate region changes; the rest of the photo stays sharp)
            img.save(src, "JPEG", quality=95, subsampling=0, optimize=True)
            print(f"  ✓ {name}: blurred {len(boxes)} region(s)  ({img.width}x{img.height})")
    print("done.")


if __name__ == "__main__":
    main()
