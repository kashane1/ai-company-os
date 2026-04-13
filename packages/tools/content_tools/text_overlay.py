"""Pillow-based text overlay compositor for social media slides.

Deterministic, no AI, no API calls. Takes a background image and a text
config, produces a finished slide with clean typography.

Design decisions (from brainstorm 2026-04-12):
- Montserrat Bold for all text
- Semi-transparent dark overlay for legibility on any background
- Dynamic font sizing via binary search
- Safe zones: 120px top, 200px bottom, 80px sides
- Output: 1080x1920 JPEG quality=90
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Canvas dimensions (TikTok / Instagram Reels / Shorts)
CANVAS_W, CANVAS_H = 1080, 1920

# Safe zones — avoid platform UI elements
SAFE_TOP = 120
SAFE_BOTTOM = 200
MARGIN = 80
TEXT_AREA_W = CANVAS_W - 2 * MARGIN
TEXT_AREA_H = CANVAS_H - SAFE_TOP - SAFE_BOTTOM

# Typography
LINE_SPACING = 8
BLOCK_SPACING = 32
DEFAULT_OVERLAY_ALPHA = 115  # ~45% opacity — lets background show through

# Font path (bundled in repo)
FONT_DIR = Path(__file__).parent / "fonts"
DEFAULT_FONT = FONT_DIR / "Montserrat-Bold.ttf"


@dataclass
class SlideTextConfig:
    """Text content for a single slide. All fields optional — the overlay
    renders whichever fields are present."""
    headline: str | None = None
    subhead: str | None = None
    bullets: list[str] | None = None
    body: str | None = None


@lru_cache(maxsize=16)
def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a TrueType font, cached to avoid repeated disk reads."""
    return ImageFont.truetype(path, size=size)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int,
               draw: ImageDraw.ImageDraw) -> str:
    """Word-wrap text to fit within max_width. Preserves existing newlines
    (e.g. bullet lists) — each input line is wrapped independently."""
    output_lines: list[str] = []

    for input_line in text.split("\n"):
        words = input_line.split()
        if not words:
            output_lines.append("")
            continue
        current: list[str] = []
        for word in words:
            test = " ".join(current + [word])
            if draw.textlength(test, font=font) <= max_width:
                current.append(word)
            else:
                if current:
                    output_lines.append(" ".join(current))
                current = [word]
        if current:
            output_lines.append(" ".join(current))

    return "\n".join(output_lines)


def _fit_font_size(text: str, font_path: str, max_width: int, max_height: int,
                   draw: ImageDraw.ImageDraw, lo: int = 28, hi: int = 96) -> int:
    """Binary search for the largest font size where wrapped text fits."""
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        font = _load_font(font_path, mid)
        wrapped = _wrap_text(text, font, max_width, draw)
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font,
                                       spacing=LINE_SPACING)
        total_h = bbox[3] - bbox[1]
        if total_h <= max_height:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def _measure_text_block(text: str, font: ImageFont.FreeTypeFont,
                        draw: ImageDraw.ImageDraw) -> tuple[int, int]:
    """Measure the width and height of a wrapped text block."""
    bbox = draw.multiline_textbbox((0, 0), text, font=font,
                                   spacing=LINE_SPACING)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_centered_text(draw: ImageDraw.ImageDraw, text: str,
                        font: ImageFont.FreeTypeFont, y: int,
                        fill: tuple = (255, 255, 255, 255)) -> int:
    """Draw text centered horizontally at the given y position.
    Returns the height consumed."""
    w, h = _measure_text_block(text, font, draw)
    x = (CANVAS_W - w) // 2
    draw.multiline_text((x, y), text, font=font, fill=fill,
                        spacing=LINE_SPACING, align="center")
    return h


def overlay_text(
    background_path: Path,
    text_config: SlideTextConfig,
    output_path: Path,
    overlay_alpha: int = DEFAULT_OVERLAY_ALPHA,
    target_size: tuple[int, int] = (CANVAS_W, CANVAS_H),
) -> Path:
    """Composite text onto a background image with a dark overlay.

    Args:
        background_path: Path to the background image (any format Pillow reads).
        text_config: SlideTextConfig with the text fields to render.
        output_path: Where to save the finished slide (JPEG).
        overlay_alpha: 0-255 opacity for the dark overlay (178 = ~70%).
        target_size: Output dimensions (default 1080x1920).

    Returns:
        The output_path for chaining.
    """
    font_path = str(DEFAULT_FONT)

    # Load and resize background
    base = Image.open(background_path).resize(target_size).convert("RGBA")

    # Create semi-transparent dark overlay (20%–60% from top of image)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    shadow_top = int(CANVAS_H * 0.20)   # 20% from top
    shadow_bottom = int(CANVAS_H * 0.60) # 60% from top
    overlay_region = (0, shadow_top, CANVAS_W, shadow_bottom)
    overlay_draw.rectangle(overlay_region, fill=(0, 0, 0, overlay_alpha))
    base = Image.alpha_composite(base, overlay)

    draw = ImageDraw.Draw(base)

    # Build text blocks from config
    blocks: list[tuple[str, int, int]] = []  # (text, min_size, max_size)

    if text_config.headline:
        blocks.append((text_config.headline, 48, 96))

    if text_config.bullets:
        bullet_text = "\n".join(f"  {b}" for b in text_config.bullets)
        blocks.append((bullet_text, 28, 44))
    elif text_config.body:
        blocks.append((text_config.body, 28, 40))

    if text_config.subhead:
        blocks.append((text_config.subhead, 36, 56))

    if not blocks:
        # Nothing to render — save background as-is
        output_path.parent.mkdir(parents=True, exist_ok=True)
        base.convert("RGB").save(str(output_path), "JPEG", quality=90)
        return output_path

    # Fit font sizes and measure total height
    fitted: list[tuple[str, ImageFont.FreeTypeFont, int]] = []  # (wrapped, font, height)
    for text, lo, hi in blocks:
        # Allocate height proportionally
        block_max_h = TEXT_AREA_H // len(blocks) - BLOCK_SPACING
        size = _fit_font_size(text, font_path, TEXT_AREA_W, block_max_h,
                              draw, lo=lo, hi=hi)
        font = _load_font(font_path, size)
        wrapped = _wrap_text(text, font, TEXT_AREA_W, draw)
        _, h = _measure_text_block(wrapped, font, draw)
        fitted.append((wrapped, font, h))

    total_h = sum(h for _, _, h in fitted) + BLOCK_SPACING * (len(fitted) - 1)

    # Vertically center in the shadow region (20%–60% from top)
    region_top = int(CANVAS_H * 0.20)
    region_bottom = int(CANVAS_H * 0.60)
    region_h = region_bottom - region_top
    start_y = region_top + max(0, (region_h - total_h) // 2)

    # Draw each block
    y = start_y
    for i, (wrapped, font, h) in enumerate(fitted):
        # Slightly dimmer for non-headline blocks
        fill = (255, 255, 255, 255) if i == 0 else (255, 255, 255, 220)
        y += _draw_centered_text(draw, wrapped, font, y, fill=fill)
        y += BLOCK_SPACING

    # Save as JPEG
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(str(output_path), "JPEG", quality=90)
    logger.info("Composed slide: %s", output_path)
    return output_path


def compose_post(
    backgrounds: list[Path],
    text_configs: list[SlideTextConfig],
    output_dir: Path,
    item_number: int,
) -> list[Path]:
    """Compose a full multi-slide post from backgrounds + text configs.

    Args:
        backgrounds: List of background image paths (one per slide).
        text_configs: List of SlideTextConfig (one per slide, same length
                      as backgrounds).
        output_dir: Where to save the finished slides.
        item_number: Backlog item number (for file naming).

    Returns:
        List of output file paths.
    """
    if len(backgrounds) != len(text_configs):
        raise ValueError(
            f"Mismatched lengths: {len(backgrounds)} backgrounds vs "
            f"{len(text_configs)} text configs"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []

    for i, (bg, tc) in enumerate(zip(backgrounds, text_configs), start=1):
        out = output_dir / f"item_{item_number:03d}_slide_{i}.jpg"
        overlay_text(bg, tc, out)
        output_paths.append(out)

    logger.info("Composed %d slides for item %d in %s",
                len(output_paths), item_number, output_dir)
    return output_paths
