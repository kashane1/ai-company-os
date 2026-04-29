"""
Generate concept app-icon options for After Plans.

These are non-destructive design explorations. They write 1024px masters and a
contact sheet under docs/products/after-plans/app-icon-options/.

Run from the repo root:
    python3 infra/scripts/generate_afterplans_icon_options.py
"""

import math
import os
from dataclasses import dataclass
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, "docs", "products", "after-plans", "app-icon-options")
SIZE = 1024

DUSK_DEEP = (7, 18, 48)
DUSK = (22, 65, 150)
ACCENT = (31, 99, 199)
CYAN = (105, 222, 255)
MOMENTUM = (250, 153, 46)
GLOW = (255, 204, 128)
CREAM = (255, 248, 232)
WHITE = (255, 255, 255)
INK = (5, 14, 36)


@dataclass(frozen=True)
class IconOption:
    slug: str
    label: str
    renderer: callable


def clamp(value: float) -> int:
    return max(0, min(255, int(value)))


def lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(clamp(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient(size: int, stops: Iterable[tuple[float, tuple[int, int, int]]]) -> Image.Image:
    stops = sorted(stops, key=lambda item: item[0])
    img = Image.new("RGB", (size, size), DUSK_DEEP)
    px = img.load()
    sun_x, sun_y = size * 0.88, size * 0.78
    cool_x, cool_y = size * 0.05, size * 0.05
    max_d = math.hypot(size, size)

    for y in range(size):
        for x in range(size):
            warm = math.hypot(x - sun_x, y - sun_y) / (max_d * 0.78)
            cool = math.hypot(x - cool_x, y - cool_y) / max_d
            t = max(0.0, min(1.0, warm))

            left = stops[0]
            right = stops[-1]
            for index in range(len(stops) - 1):
                if stops[index][0] <= t <= stops[index + 1][0]:
                    left, right = stops[index], stops[index + 1]
                    break

            local_t = (t - left[0]) / max(0.001, right[0] - left[0])
            color = lerp(left[1], right[1], local_t)
            vignette = max(0, cool - 0.56) * 0.28
            color = lerp(color, DUSK_DEEP, vignette)
            px[x, y] = color

    return img


def rounded_rect_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, size, size], radius=radius, fill=255)
    return mask


def add_bloom(base: Image.Image, center: tuple[int, int], color: tuple[int, int, int], radii: list[tuple[int, int]]) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = center
    for radius, alpha in radii:
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(*color, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=52))
    base.alpha_composite(layer)


def add_glass_highlights(base: Image.Image) -> None:
    size = base.size[0]
    shine = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shine)

    draw.ellipse(
        [int(size * -0.10), int(size * -0.18), int(size * 0.74), int(size * 0.45)],
        fill=(255, 255, 255, 54),
    )
    draw.rounded_rectangle(
        [int(size * 0.12), int(size * 0.10), int(size * 0.68), int(size * 0.18)],
        radius=42,
        fill=(255, 255, 255, 72),
    )
    draw.rounded_rectangle(
        [int(size * 0.22), int(size * 0.20), int(size * 0.46), int(size * 0.24)],
        radius=20,
        fill=(255, 255, 255, 42),
    )
    draw.arc(
        [int(size * 0.44), int(size * 0.16), int(size * 1.16), int(size * 0.88)],
        start=205,
        end=304,
        fill=(255, 255, 255, 82),
        width=10,
    )
    shine = shine.filter(ImageFilter.GaussianBlur(radius=1.3))
    base.alpha_composite(shine)


def prismatic_fill(mask: Image.Image, light_background: bool = False) -> Image.Image:
    size = mask.size[0]
    img = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    px = img.load()
    mask_px = mask.load()
    colors = [
        (33, 18, 64),
        (18, 210, 255),
        (255, 246, 122),
        (255, 63, 162),
        (42, 12, 82),
        (255, 138, 42),
    ]

    for y in range(size):
        for x in range(size):
            alpha = mask_px[x, y]
            if alpha == 0:
                continue
            t = ((x * 0.72 + y * 0.54) / size + math.sin((x - y) / 58) * 0.12) % 1.0
            segment = min(len(colors) - 2, int(t * (len(colors) - 1)))
            local = t * (len(colors) - 1) - segment
            color = lerp(colors[segment], colors[segment + 1], local)
            shade = 0.78 + 0.34 * math.sin((x + y) / 82) + 0.18 * math.cos((x * 1.8 - y) / 94)
            if light_background:
                shade += 0.08
            px[x, y] = tuple(clamp(channel * shade) for channel in color) + (alpha,)

    return img


def light_glass_background() -> Image.Image:
    base = Image.new("RGBA", (SIZE, SIZE), (248, 249, 248, 255))
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse([-210, -120, 680, 540], fill=(255, 255, 255, 220))
    draw.ellipse([420, 420, 1190, 1120], fill=(255, 213, 142, 42))
    draw.ellipse([120, 560, 760, 1160], fill=(100, 218, 255, 34))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=58))
    base.alpha_composite(layer)

    border = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(border)
    draw.rounded_rectangle([34, 34, 990, 990], radius=196, outline=(255, 255, 255, 210), width=14)
    draw.rounded_rectangle([58, 58, 966, 966], radius=176, outline=(210, 214, 220, 70), width=5)
    base.alpha_composite(border)
    return base


def sparkle_mask(points: list[tuple[int, int]]) -> Image.Image:
    mask = Image.new("L", (SIZE, SIZE), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(points, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.35))
    return mask


def shadowed_layer(size: int, blur: int = 28, offset: tuple[int, int] = (0, 22)) -> Image.Image:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse([180 + offset[0], 210 + offset[1], 844 + offset[0], 874 + offset[1]], fill=(0, 0, 0, 82))
    return layer.filter(ImageFilter.GaussianBlur(radius=blur))


def font(size: int, heavy: bool = True) -> ImageFont.FreeTypeFont:
    path = "/System/Library/Fonts/Avenir Next.ttc"
    try:
        return ImageFont.truetype(path, size, index=4 if heavy else 1)
    except OSError:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)


def render_momentum_orb() -> Image.Image:
    base = gradient(SIZE, [(0.0, GLOW), (0.23, MOMENTUM), (0.50, ACCENT), (0.82, DUSK), (1.0, DUSK_DEEP)]).convert("RGBA")
    add_bloom(base, (770, 700), GLOW, [(360, 70), (240, 90), (120, 130)])

    base.alpha_composite(shadowed_layer(SIZE))
    orb = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(orb)
    draw.ellipse([190, 170, 834, 814], fill=(255, 255, 255, 36), outline=(255, 255, 255, 130), width=5)
    draw.ellipse([228, 210, 796, 778], fill=(255, 255, 255, 34))
    draw.arc([245, 225, 780, 760], 196, 316, fill=(255, 255, 255, 150), width=18)
    draw.arc([274, 260, 734, 720], 25, 124, fill=(255, 232, 190, 120), width=12)
    orb = orb.filter(ImageFilter.GaussianBlur(radius=0.3))
    base.alpha_composite(orb)

    draw = ImageDraw.Draw(base)
    f = font(258)
    text = "AP"
    bbox = draw.textbbox((0, 0), text, font=f)
    x = (SIZE - (bbox[2] - bbox[0])) // 2 - 6
    y = (SIZE - (bbox[3] - bbox[1])) // 2 - 20
    draw.text((x + 5, y + 12), text, font=f, fill=(0, 0, 0, 72))
    draw.text((x, y), text, font=f, fill=CREAM)
    draw.ellipse([654, 606, 722, 674], fill=CREAM)
    add_glass_highlights(base)
    return base.convert("RGB")


def render_continuation_ring() -> Image.Image:
    base = gradient(SIZE, [(0.0, CREAM), (0.20, GLOW), (0.46, MOMENTUM), (0.65, ACCENT), (1.0, DUSK_DEEP)]).convert("RGBA")
    add_bloom(base, (690, 420), CYAN, [(320, 35), (180, 60)])

    ring = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ring)
    draw.ellipse([176, 176, 848, 848], outline=(255, 255, 255, 130), width=58)
    draw.ellipse([238, 238, 786, 786], outline=(255, 246, 224, 50), width=26)
    draw.arc([164, 164, 860, 860], 206, 40, fill=(255, 255, 255, 210), width=70)
    draw.arc([164, 164, 860, 860], 44, 130, fill=(82, 220, 255, 180), width=42)
    draw.ellipse([690, 305, 812, 427], fill=CREAM, outline=(255, 255, 255, 190), width=5)
    ring = ring.filter(ImageFilter.GaussianBlur(radius=0.5))
    base.alpha_composite(ring)

    draw = ImageDraw.Draw(base)
    f = font(156)
    text = "after"
    bbox = draw.textbbox((0, 0), text, font=f)
    x = (SIZE - (bbox[2] - bbox[0])) // 2
    y = 432 - (bbox[3] - bbox[1]) // 2
    draw.text((x + 3, y + 7), text, font=f, fill=(0, 0, 0, 78))
    draw.text((x, y), text, font=f, fill=CREAM)
    add_glass_highlights(base)
    return base.convert("RGB")


def render_glass_ticket() -> Image.Image:
    base = gradient(SIZE, [(0.0, GLOW), (0.28, MOMENTUM), (0.55, ACCENT), (0.80, DUSK), (1.0, DUSK_DEEP)]).convert("RGBA")
    add_bloom(base, (330, 720), MOMENTUM, [(300, 65), (170, 100)])

    panel = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle([190, 236, 834, 772], radius=116, fill=(255, 255, 255, 46), outline=(255, 255, 255, 150), width=5)
    draw.rounded_rectangle([232, 280, 792, 728], radius=92, fill=(255, 255, 255, 28))
    draw.line([320, 342, 320, 666], fill=(255, 255, 255, 104), width=8)
    for y in (370, 456, 542, 628):
        draw.ellipse([288, y, 352, y + 64], fill=(*INK, 62))
    draw.rounded_rectangle([398, 372, 706, 430], radius=28, fill=CREAM)
    draw.rounded_rectangle([398, 486, 650, 534], radius=24, fill=(255, 255, 255, 188))
    draw.rounded_rectangle([398, 598, 704, 646], radius=24, fill=(255, 255, 255, 128))
    draw.arc([610, 500, 772, 662], 214, 34, fill=(255, 226, 176, 210), width=22)
    draw.polygon([(745, 568), (690, 526), (695, 610)], fill=(255, 226, 176, 230))
    panel = panel.filter(ImageFilter.GaussianBlur(radius=0.2))
    base.alpha_composite(panel)
    add_glass_highlights(base)
    return base.convert("RGB")


def render_prism_spark() -> Image.Image:
    base = light_glass_background()
    points = [(512, 132), (610, 420), (896, 512), (610, 604), (512, 892), (414, 604), (128, 512), (414, 420)]
    mask = sparkle_mask(points)

    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.polygon([(x, y + 18) for x, y in points], fill=(0, 0, 0, 72))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=28))
    base.alpha_composite(shadow)

    gem = prismatic_fill(mask, light_background=True)
    edge = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(edge)
    draw.polygon(points, outline=(24, 17, 44, 185), width=16)
    draw.line([128, 512, 512, 512, 896, 512], fill=(255, 255, 255, 116), width=9)
    draw.line([512, 132, 512, 892], fill=(255, 255, 255, 96), width=7)
    draw.line([414, 420, 610, 604], fill=(255, 255, 255, 74), width=6)
    draw.line([610, 420, 414, 604], fill=(10, 12, 36, 70), width=7)
    draw.ellipse([388, 244, 596, 452], fill=(255, 255, 255, 66))
    edge = edge.filter(ImageFilter.GaussianBlur(radius=0.8))
    base.alpha_composite(gem)
    base.alpha_composite(edge)
    return base.convert("RGB")


def render_after_prism_dot() -> Image.Image:
    base = light_glass_background()
    points = [(486, 156), (600, 386), (812, 486), (606, 590), (508, 830), (398, 596), (180, 506), (394, 386)]
    mask = sparkle_mask(points)
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.polygon([(x + 8, y + 24) for x, y in points], fill=(0, 0, 0, 82))
    shadow_draw.ellipse([660, 650, 800, 790], fill=(0, 0, 0, 46))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=26))
    base.alpha_composite(shadow)

    gem = prismatic_fill(mask, light_background=True)
    base.alpha_composite(gem)

    draw = ImageDraw.Draw(base)
    draw.polygon(points, outline=(18, 15, 42, 166), width=12)
    draw.line([180, 506, 812, 486], fill=(255, 255, 255, 122), width=8)
    draw.line([486, 156, 508, 830], fill=(255, 255, 255, 82), width=8)
    draw.arc([284, 262, 696, 674], 210, 318, fill=(255, 255, 255, 170), width=14)
    draw.ellipse([660, 650, 790, 780], fill=(255, 252, 232, 255), outline=(255, 255, 255, 235), width=8)
    return base.convert("RGB")


def render_liquid_glass_ap() -> Image.Image:
    base = light_glass_background()
    panel = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle([210, 210, 814, 814], radius=178, fill=(255, 255, 255, 74), outline=(255, 255, 255, 190), width=8)
    draw.rounded_rectangle([248, 248, 776, 776], radius=146, fill=(255, 255, 255, 28))
    panel = panel.filter(ImageFilter.GaussianBlur(radius=0.5))
    base.alpha_composite(panel)

    mask = Image.new("L", (SIZE, SIZE), 0)
    draw_mask = ImageDraw.Draw(mask)
    f = font(282)
    text = "AP"
    bbox = draw_mask.textbbox((0, 0), text, font=f)
    draw_mask.text(((SIZE - (bbox[2] - bbox[0])) // 2 - 8, 352), text, font=f, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.2))
    fill = prismatic_fill(mask, light_background=True)
    base.alpha_composite(fill)

    draw = ImageDraw.Draw(base)
    draw.text(((SIZE - (bbox[2] - bbox[0])) // 2 - 8, 352), text, font=f, fill=(255, 255, 255, 54))
    draw.rounded_rectangle([294, 266, 604, 318], radius=26, fill=(255, 255, 255, 118))
    draw.ellipse([648, 654, 756, 762], fill=(255, 246, 220, 255))
    draw.arc([262, 244, 766, 750], 204, 310, fill=(255, 255, 255, 132), width=12)
    return base.convert("RGB")


def render_after_spark() -> Image.Image:
    base = gradient(SIZE, [(0.0, CREAM), (0.18, GLOW), (0.42, MOMENTUM), (0.64, ACCENT), (0.88, DUSK), (1.0, DUSK_DEEP)]).convert("RGBA")
    add_bloom(base, (530, 500), WHITE, [(310, 56), (150, 86)])

    mark = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(mark)
    draw.ellipse([266, 266, 758, 758], fill=(255, 255, 255, 34), outline=(255, 255, 255, 135), width=5)
    for angle in range(0, 360, 45):
        r1 = 94
        r2 = 242 if angle % 90 == 0 else 190
        a = math.radians(angle - 90)
        x1 = 512 + math.cos(a) * r1
        y1 = 512 + math.sin(a) * r1
        x2 = 512 + math.cos(a) * r2
        y2 = 512 + math.sin(a) * r2
        draw.line([x1, y1, x2, y2], fill=(255, 255, 255, 180), width=22)
    draw.ellipse([408, 408, 616, 616], fill=CREAM)
    draw.ellipse([458, 458, 566, 566], fill=(255, 184, 80, 230))
    draw.ellipse([642, 642, 726, 726], fill=CREAM)
    mark = mark.filter(ImageFilter.GaussianBlur(radius=0.4))
    base.alpha_composite(mark)
    add_glass_highlights(base)
    return base.convert("RGB")


def save_icon(img: Image.Image, slug: str) -> str:
    path = os.path.join(OUT_DIR, f"afterplans-icon-{slug}-1024.png")
    img.save(path, "PNG", optimize=True)
    return path


def make_contact_sheet(options: list[tuple[IconOption, Image.Image]]) -> str:
    cell = 320
    padding = 36
    label_h = 56
    sheet = Image.new("RGB", (padding + len(options) * (cell + padding), cell + label_h + padding * 2), (246, 247, 250))
    draw = ImageDraw.Draw(sheet)
    label_font = font(24, heavy=False)

    for index, (option, img) in enumerate(options):
        x = padding + index * (cell + padding)
        y = padding
        preview = img.resize((cell, cell), Image.LANCZOS)
        mask = rounded_rect_mask(cell, 72)
        shadow = Image.new("RGBA", (cell + 30, cell + 30), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle([15, 15, cell + 15, cell + 15], radius=72, fill=(0, 0, 0, 48))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=14))
        sheet.paste(shadow.convert("RGB"), (x - 15, y - 5), shadow)
        sheet.paste(preview, (x, y), mask)
        label = option.label
        bbox = draw.textbbox((0, 0), label, font=label_font)
        draw.text((x + (cell - (bbox[2] - bbox[0])) / 2, y + cell + 22), label, font=label_font, fill=(28, 34, 46))

    path = os.path.join(OUT_DIR, "afterplans-icon-options-contact-sheet.png")
    sheet.save(path, "PNG", optimize=True)
    return path


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    options = [
        IconOption("momentum-orb", "Momentum Orb", render_momentum_orb),
        IconOption("continuation-ring", "Continuation Ring", render_continuation_ring),
        IconOption("glass-ticket", "Glass Ticket", render_glass_ticket),
        IconOption("after-spark", "After Spark", render_after_spark),
        IconOption("prism-spark", "Prism Spark", render_prism_spark),
        IconOption("after-prism-dot", "Prism Dot", render_after_prism_dot),
        IconOption("liquid-glass-ap", "Glass AP", render_liquid_glass_ap),
    ]

    rendered = []
    for option in options:
        img = option.renderer()
        path = save_icon(img, option.slug)
        print(path)
        rendered.append((option, img))

    print(make_contact_sheet(rendered))


if __name__ == "__main__":
    main()
