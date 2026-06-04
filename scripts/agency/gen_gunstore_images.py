#!/usr/bin/env python3
"""Generate imagery for the Blue Ridge Gun & Ammo portfolio demo via Gemini.

Hunting & sporting heritage look (Dahlonega, GA). By design the scenes do NOT
depend on firearm close-ups — landscape hero, warm outfitter interior, optics
wall, boxed ammunition, gunsmith bench, field gear. Each asset has a firearm-free
FALLBACK prompt; if Gemini's safety filter refuses the primary, we drop to the
fallback and record the substitution.

    python scripts/agency/gen_gunstore_images.py

Output: products/better-business-web/portfolio/gun_store/dist/assets/<name>.jpg
Raw PNGs from Gemini are downscaled + JPEG-encoded (max 1600px wide, q82).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.tools.content_tools.gemini_images import generate_image  # noqa: E402

ASSETS = REPO / "products" / "better-business-web" / "portfolio" / "gun_store" / "dist" / "assets"

# (name, aspect, primary_prompt, fallback_prompt_no_firearms)
PHOTO_STYLE = (
    "Photorealistic, editorial photography, warm natural light, rich earthy "
    "color grade, shallow depth of field, rustic North Georgia mountain-town "
    "character, inviting and trustworthy."
)

JOBS = [
    (
        "hero", "16:9",
        "Sweeping Blue Ridge Mountains in north Georgia at golden hour: layered "
        "blue ridgelines fading into mist, autumn hardwood forest in the "
        "foreground, soft warm sunlight. Cinematic landscape. " + PHOTO_STYLE,
        "Sweeping Blue Ridge Mountains at golden hour, layered misty ridgelines, "
        "autumn forest. Cinematic landscape. " + PHOTO_STYLE,
    ),
    (
        "store-interior", "3:4",
        "Interior of a cozy family-owned hunting outfitter and gun shop in a "
        "Georgia mountain town: warm wood-paneled walls, a long glass display "
        "counter, mounted whitetail deer antlers on the wall, hanging blaze-orange "
        "vests and field jackets, soft daylight through a front window. Wide "
        "welcoming interior, no people. " + PHOTO_STYLE,
        "Interior of a cozy rustic outdoor outfitter store: warm wood-paneled "
        "walls, glass display counter, mounted whitetail deer antlers, hanging "
        "field jackets and blaze-orange vests, soft daylight. No people. " + PHOTO_STYLE,
    ),
    (
        "counter", "4:3",
        "Close view of a warm wooden retail sales counter in a hunting outfitter: "
        "a glass display case holding binoculars and rangefinders, a brass cash "
        "register, neat stacks of paperwork, warm task lighting. No people. " + PHOTO_STYLE,
        "Warm wooden retail sales counter with a glass case of binoculars and "
        "rangefinders, brass register, warm lighting. No people. " + PHOTO_STYLE,
    ),
    (
        "optics-wall", "4:3",
        "A tidy retail wall display of hunting optics — rifle scopes, binoculars, "
        "spotting scopes and rangefinders — arranged on warm wooden pegboard "
        "shelving in a sporting goods store, price tags, warm lighting. " + PHOTO_STYLE,
        "Retail wall of binoculars, spotting scopes and rangefinders on warm "
        "wooden shelving in a sporting goods store. " + PHOTO_STYLE,
    ),
    (
        "gunsmith-bench", "4:3",
        "A gunsmith's tidy wooden workbench in a mountain-town shop: hand tools "
        "laid out, a bench vise, cleaning brushes and solvent bottles, brass "
        "punches, a green cutting mat, warm focused task light. No firearms, tools "
        "only. " + PHOTO_STYLE,
        "A craftsman's tidy wooden workbench: hand tools, a bench vise, brushes "
        "and solvent bottles, brass punches, green mat, warm task light. " + PHOTO_STYLE,
    ),
    (
        "ammo-shelf", "4:3",
        "Retail shelving neatly stocked with boxed ammunition cartons organized by "
        "caliber in a sporting goods store, colorful cardboard boxes, price labels "
        "on the shelf edge, warm lighting. Boxes only, no loose rounds. " + PHOTO_STYLE,
        "Retail shelving stocked with rows of colorful boxed cartons organized by "
        "category in a sporting goods store, price labels, warm lighting. " + PHOTO_STYLE,
    ),
    (
        "gear", "4:3",
        "A flat-lay of hunting field gear on weathered rustic wood: a folded "
        "blaze-orange vest, turkey and deer game calls, a canvas backpack, leather "
        "boots, a knife in a sheath, and a thermos. Warm morning light. " + PHOTO_STYLE,
        "A flat-lay of outdoor field gear on weathered rustic wood: a folded "
        "blaze-orange vest, a canvas backpack, leather boots, a knife in a sheath, "
        "a thermos. Warm morning light. " + PHOTO_STYLE,
    ),
]


def _encode(raw: bytes, mime: str, dest: Path) -> None:
    """Downscale to max 1600px wide and JPEG-encode at q82."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    suffix = ".png" if "png" in mime else ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)
    # sips: resize longest dimension down to <=1600, then format jpeg.
    subprocess.run(
        ["sips", "-Z", "1600", "-s", "format", "jpeg", "-s", "formatOptions", "82",
         str(tmp_path), "--out", str(dest)],
        check=True, capture_output=True,
    )
    tmp_path.unlink(missing_ok=True)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    subs: list[str] = []
    for name, aspect, primary, fallback in JOBS:
        dest = ASSETS / f"{name}.jpg"
        used = "primary"
        img = None
        for attempt, prompt in (("primary", primary), ("fallback", fallback)):
            try:
                img = generate_image(prompt, aspect_ratio=aspect)
                used = attempt
                break
            except Exception as e:  # noqa: BLE001 — safety-block or transient
                print(f"  ! {name} [{attempt}] failed: {str(e)[:120]}")
                time.sleep(2)
        if img is None:
            print(f"  ✗ {name}: BOTH prompts failed — left missing")
            subs.append(f"{name}: MISSING (both filtered)")
            continue
        _encode(img.data, img.mime_type, dest)
        kb = dest.stat().st_size / 1024
        flag = "" if used == "primary" else "  ⟵ FELL BACK to firearm-free prompt"
        print(f"  ✓ {name:16s} [{used:8s}] {kb:5.0f} KB{flag}")
        if used == "fallback":
            subs.append(f"{name}: used firearm-free fallback")
        time.sleep(1)  # be gentle with the free-tier rate limit

    print("\n--- substitution log ---")
    print("\n".join(subs) if subs else "none — all primary prompts succeeded")


if __name__ == "__main__":
    main()
