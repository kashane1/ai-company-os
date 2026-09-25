#!/usr/bin/env python3
"""Render the HomeFromWorking Etsy icon and banner from one brand system."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CREAM = "#F6F0E7"
PAPER = "#FFFCF7"
CHARCOAL = "#2D2B28"
SAGE = "#97A486"
TERRACOTTA = "#C97858"
GOLD = "#D6B46C"
LINE = "#D8CDBE"

GEORGIA_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
GEORGIA_ITALIC = "/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf"
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"


def font(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size, index=index)


def centered_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    text_font: ImageFont.FreeTypeFont,
    fill: str,
    *,
    anchor: str = "mm",
    spacing: int = 4,
) -> None:
    draw.multiline_text(
        xy,
        text,
        font=text_font,
        fill=fill,
        anchor=anchor,
        align="center",
        spacing=spacing,
    )


def draw_spark(draw: ImageDraw.ImageDraw, x: int, y: int, r: int, fill: str) -> None:
    points = [
        (x, y - r),
        (x + r // 4, y - r // 4),
        (x + r, y),
        (x + r // 4, y + r // 4),
        (x, y + r),
        (x - r // 4, y + r // 4),
        (x - r, y),
        (x - r // 4, y - r // 4),
    ]
    draw.polygon(points, fill=fill)


def draw_leaf(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    w = int(88 * scale)
    h = int(42 * scale)
    draw.ellipse((x - w, y - h, x, y), outline=SAGE, width=max(2, int(4 * scale)))
    draw.ellipse((x, y, x + w, y + h), outline=SAGE, width=max(2, int(4 * scale)))
    draw.line((x - w + 10, y - h + 8, x + w - 10, y + h - 8), fill=SAGE, width=max(2, int(4 * scale)))


def draw_mug(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    w = int(72 * scale)
    h = int(54 * scale)
    stroke = max(2, int(4 * scale))
    draw.rounded_rectangle((x, y, x + w, y + h), radius=int(9 * scale), outline=TERRACOTTA, width=stroke)
    draw.arc((x + w - 2, y + 8, x + w + int(30 * scale), y + h - 5), 265, 95, fill=TERRACOTTA, width=stroke)
    draw.arc((x + 12, y - int(30 * scale), x + 33, y + 7), 205, 340, fill=TERRACOTTA, width=stroke)
    draw.arc((x + 36, y - int(25 * scale), x + 57, y + 10), 205, 340, fill=TERRACOTTA, width=stroke)


def render_icon(path: Path) -> None:
    size = 500
    image = Image.new("RGB", (size, size), CREAM)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((24, 24, 476, 476), radius=92, fill=PAPER, outline=LINE, width=5)
    draw.ellipse((58, 66, 118, 126), fill=GOLD)
    draw.ellipse((388, 376, 446, 434), fill=SAGE)
    draw_spark(draw, 420, 90, 23, TERRACOTTA)

    centered_text(draw, (250, 228), "HFW", font(GEORGIA_ITALIC, 150), CHARCOAL)
    draw.line((132, 310, 368, 310), fill=CHARCOAL, width=5)
    centered_text(draw, (250, 354), "SMALL LAUGHS", font(AVENIR, 24), CHARCOAL)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def render_banner(path: Path) -> None:
    width, height = 1600, 400
    image = Image.new("RGB", (width, height), CREAM)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((-120, 246, 390, 550), radius=140, fill="#EEE5D7")
    draw.rounded_rectangle((1270, -170, 1760, 155), radius=150, fill="#ECE6DA")
    draw.line((250, 60, 1350, 60), fill=LINE, width=2)
    draw.line((250, 340, 1350, 340), fill=LINE, width=2)

    draw.ellipse((282, 91, 500, 309), fill=PAPER, outline=LINE, width=4)
    centered_text(draw, (391, 183), "HFW", font(GEORGIA_ITALIC, 74), CHARCOAL)
    draw.line((334, 238, 448, 238), fill=CHARCOAL, width=3)
    centered_text(draw, (391, 264), "SMALL LAUGHS", font(AVENIR, 13), CHARCOAL)

    draw.text((545, 112), "HomeFromWorking", font=font(GEORGIA_BOLD, 67), fill=CHARCOAL)
    draw.text((550, 204), "SMALL LAUGHS FOR THOSE LONG DAYS", font=font(AVENIR, 28), fill=CHARCOAL)
    draw.text((550, 259), "funny shirts  •  curious facts  •  animal humor", font=font(AVENIR, 22), fill="#625E57")

    draw_mug(draw, 112, 258, 0.9)
    draw_leaf(draw, 1438, 91, 0.75)
    draw_spark(draw, 1398, 292, 24, GOLD)
    draw_spark(draw, 1490, 258, 13, TERRACOTTA)
    draw.ellipse((132, 84, 153, 105), fill=SAGE)
    draw.ellipse((182, 110, 196, 124), fill=TERRACOTTA)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("state/home-from-working/operations/trust-floor-20260907/assets"),
    )
    args = parser.parse_args()

    render_icon(args.output_dir / "homefromworking-etsy-icon-500.png")
    render_banner(args.output_dir / "homefromworking-etsy-banner-1600x400.png")


if __name__ == "__main__":
    main()
