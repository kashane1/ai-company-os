"""
After Plans app icon — 1024 master + iOS sizes.

Design intent:
- Theme: "after" — the glow that lingers after the moment ends.
- Composition: deep dusk blue dominates top-left, a warm afterglow blooms
  from a sun setting past the bottom-right corner. Radial — not banded.
- Wordmark: "after / plans" stacked, lowercase Avenir Next Heavy, tight,
  with a small white continuation dot after "plans".
- Subtle horizon arc echoes the sun's edge for depth, not for decoration.

Brand colors are encoded in DesignTokens.swift as Color.appAccent and
Color.appMomentum; the constants below mirror those plus a few shading
stops. Do not change brand colors without updating DesignTokens.swift.

Run from the repo root:
    .venv/bin/python infra/scripts/generate_afterplans_icon.py

Override the output path:
    AFTERPLANS_ICON_OUT=/tmp/icons python infra/scripts/generate_afterplans_icon.py
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Default output path is the iOS asset catalog. Override with
# AFTERPLANS_ICON_OUT=/path/to/dir for ad-hoc renders.
DEFAULT_OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "products", "after-plans-ios", "Sources", "Assets.xcassets",
    "AppIcon.appiconset",
)
OUT_DIR = os.environ.get("AFTERPLANS_ICON_OUT", DEFAULT_OUT)
os.makedirs(OUT_DIR, exist_ok=True)

# Brand palette (sRGB) — synced to DesignTokens.swift.
# appAccent  ≈ (0.12, 0.39, 0.78) → (31, 99, 199)
# appMomentum ≈ (0.98, 0.60, 0.18) → (250, 153, 46)
DUSK_DEEP = (8, 22, 58)        # near-black blue, top-left anchor
DUSK = (24, 70, 156)           # midnight blue
ACCENT = (31, 99, 199)         # appAccent
GLOW_WARM = (255, 178, 92)     # warm midtone
MOMENTUM = (250, 153, 46)      # appMomentum
SUN_CORE = (255, 222, 168)     # bright sun core

SIZE = 1024


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def render_master(size=SIZE):
    img = Image.new("RGB", (size, size), DUSK_DEEP)
    px = img.load()

    # Sun position: just past the bottom-right corner.
    sx, sy = size * 1.02, size * 1.05
    max_d = math.hypot(size, size) * 1.1
    # Reverse direction anchor: top-left
    tx, ty = -size * 0.05, -size * 0.05

    for y in range(size):
        for x in range(size):
            # Distance from sun (0 near sun, 1 far)
            d_sun = math.hypot(x - sx, y - sy) / max_d
            # Distance from top-left dusk anchor
            d_dusk = math.hypot(x - tx, y - ty) / max_d

            # Stops — read radially from the sun.
            if d_sun < 0.18:
                c = lerp(SUN_CORE, MOMENTUM, d_sun / 0.18)
            elif d_sun < 0.42:
                c = lerp(MOMENTUM, GLOW_WARM, (d_sun - 0.18) / 0.24)
            elif d_sun < 0.62:
                c = lerp(GLOW_WARM, ACCENT, (d_sun - 0.42) / 0.20)
            elif d_sun < 0.85:
                c = lerp(ACCENT, DUSK, (d_sun - 0.62) / 0.23)
            else:
                c = lerp(DUSK, DUSK_DEEP, (d_sun - 0.85) / 0.15)

            # Mild push toward dusk in the upper-left so the contrast holds
            blend = max(0.0, 0.55 - d_dusk) * 0.85
            c = lerp(c, DUSK_DEEP, blend)

            px[x, y] = c

    # Soft horizon arc — a thin warm rim along the sun's outer edge,
    # placed so its top sweeps across the lower-third of the icon.
    arc_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ad = ImageDraw.Draw(arc_layer)
    r = int(size * 0.78)
    cx, cy = int(sx), int(sy)
    for w, alpha in [(18, 22), (10, 55), (4, 120)]:
        ad.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(255, 230, 196, alpha), width=w,
        )
    arc_layer = arc_layer.filter(ImageFilter.GaussianBlur(radius=1.4))
    img.paste(arc_layer, (0, 0), arc_layer)

    # Soft luminance bloom around the sun — fakes scattering
    bloom = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bloom)
    for r2, a in [(int(size * 0.55), 28), (int(size * 0.32), 50), (int(size * 0.18), 70)]:
        bd.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(255, 220, 170, a))
    bloom = bloom.filter(ImageFilter.GaussianBlur(radius=70))
    img.paste(bloom, (0, 0), bloom)

    # Wordmark
    font_path = "/System/Library/Fonts/Avenir Next.ttc"
    try:
        f_main = ImageFont.truetype(font_path, 230, index=4)  # Heavy
    except Exception:
        f_main = ImageFont.truetype(font_path, 230)

    draw = ImageDraw.Draw(img, "RGBA")

    text_top, text_bot = "after", "plans"

    def metrics(t, f):
        l, t_, r, b = f.getbbox(t)
        return r - l, b - t_, l, t_

    wt, ht, lt, tt = metrics(text_top, f_main)
    wb, hb, lb, tb = metrics(text_bot, f_main)

    line_gap = 12
    total_h = ht + line_gap + hb
    x_origin = int(size * 0.115)
    y_top = int(size * 0.40) - total_h // 2
    y_bot = y_top + ht + line_gap

    # Drop shadow (warm dark)
    shadow_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_img)
    so = (0, 8)
    shadow_color = (4, 14, 38, 165)
    sd.text(
        (x_origin - lt + so[0], y_top - tt + so[1]),
        text_top, font=f_main, fill=shadow_color,
    )
    sd.text(
        (x_origin - lb + so[0], y_bot - tb + so[1]),
        text_bot, font=f_main, fill=shadow_color,
    )
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=5))
    img.paste(shadow_img, (0, 0), shadow_img)

    # Main wordmark
    draw.text((x_origin - lt, y_top - tt), text_top, font=f_main, fill=(255, 255, 255, 255))
    draw.text((x_origin - lb, y_bot - tb), text_bot, font=f_main, fill=(255, 255, 255, 255))

    # Continuation dot — warm, after "plans"
    dot_r = 28
    dot_x = x_origin + wb + 32
    dot_y = y_bot + hb - dot_r - 10
    # slight glow behind the dot
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse(
        [dot_x - dot_r * 2, dot_y - dot_r * 2, dot_x + dot_r * 2, dot_y + dot_r * 2],
        fill=(255, 200, 130, 90),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=14))
    img.paste(glow, (0, 0), glow)
    draw.ellipse(
        [dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r],
        fill=(255, 245, 220, 255),
    )

    return img


def main():
    print(f"Output: {OUT_DIR}")
    print("Rendering 1024 master…")
    master = render_master(SIZE)
    master.save(os.path.join(OUT_DIR, "AppIcon-1024.png"), "PNG", optimize=True)
    print("  saved AppIcon-1024.png")

    sizes = [
        (40,  "AppIcon-20@2x.png"),
        (60,  "AppIcon-20@3x.png"),
        (58,  "AppIcon-29@2x.png"),
        (87,  "AppIcon-29@3x.png"),
        (80,  "AppIcon-40@2x.png"),
        (120, "AppIcon-40@3x.png"),
        (120, "AppIcon-60@2x.png"),
        (180, "AppIcon-60@3x.png"),
    ]
    for px_, name in sizes:
        out = master.resize((px_, px_), Image.LANCZOS)
        out.save(os.path.join(OUT_DIR, name), "PNG", optimize=True)
        print(f"  saved {name} ({px_}x{px_})")

    print("Done.")


if __name__ == "__main__":
    main()
