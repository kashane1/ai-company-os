"""
After Plans app icon — resize a master 1024x1024 PNG to every iOS asset
catalog size.

The master image lives next to this script at
``infra/scripts/afterplans_icon_master.png`` and is version-controlled so
the iOS asset catalog can always be reproduced from a known-good source.

Workflow:

1. Drop a new 1024x1024 PNG at ``afterplans_icon_master.png``.
2. Run this script.
3. Commit the script, the master, and the regenerated assets together.

Run from the repo root:

    .venv/bin/python infra/scripts/generate_afterplans_icon.py

Override the master / output paths for ad-hoc renders:

    AFTERPLANS_ICON_MASTER=/tmp/master.png \
    AFTERPLANS_ICON_OUT=/tmp/icons \
    .venv/bin/python infra/scripts/generate_afterplans_icon.py

Constraints (Apple Human Interface Guidelines):

- The master must be 1024x1024, fully opaque (no alpha channel), with no
  pre-rendered rounded corners. iOS rounds the corners at render time.
- All derived sizes are produced via Lanczos resampling so small renders
  preserve detail (important for the bright pixel highlights at 60pt).
"""
import os
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

DEFAULT_MASTER = os.path.join(SCRIPT_DIR, "afterplans_icon_master.png")
DEFAULT_OUT = os.path.join(
    REPO_ROOT,
    "products", "after-plans-ios", "Sources", "Assets.xcassets",
    "AppIcon.appiconset",
)

MASTER = os.environ.get("AFTERPLANS_ICON_MASTER", DEFAULT_MASTER)
OUT_DIR = os.environ.get("AFTERPLANS_ICON_OUT", DEFAULT_OUT)

# (pixel size, filename) tuples for every required iOS app icon slot.
SIZES = [
    (1024, "AppIcon-1024.png"),
    (40,   "AppIcon-20@2x.png"),
    (60,   "AppIcon-20@3x.png"),
    (58,   "AppIcon-29@2x.png"),
    (87,   "AppIcon-29@3x.png"),
    (80,   "AppIcon-40@2x.png"),
    (120,  "AppIcon-40@3x.png"),
    (120,  "AppIcon-60@2x.png"),
    (180,  "AppIcon-60@3x.png"),
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    master = Image.open(MASTER).convert("RGB")
    if master.size != (1024, 1024):
        # Be permissive if the source is square but mis-sized — Apple
        # only ships the 1024 master to the App Store, so resample it
        # once to canonical 1024 then derive the rest from there.
        master = master.resize((1024, 1024), Image.LANCZOS)

    print(f"Master: {MASTER}")
    print(f"Output: {OUT_DIR}")
    for px, name in SIZES:
        out = master if px == 1024 else master.resize((px, px), Image.LANCZOS)
        out.save(os.path.join(OUT_DIR, name), "PNG", optimize=True)
        print(f"  saved {name} ({px}x{px})")
    print("Done.")


if __name__ == "__main__":
    main()
