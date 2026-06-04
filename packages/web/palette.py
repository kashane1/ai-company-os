"""Palette intelligence for web sites — colors, contrast, and derivation.

Three things live here, all stdlib-only (``re`` + ``colorsys``), no network:

* :data:`GENRE_PALETTES` — the machine-readable form of
  ``design_reference/palettes.md`` (curated from UI UX Pro Max, MIT; see that
  directory's ``ATTRIBUTION.md``). Keep the two in sync.
* WCAG contrast primitives (:func:`parse_color`, :func:`relative_luminance`,
  :func:`contrast_ratio`, :func:`passes_aa`) used by the web gate.
* :func:`derive_palette` — a deterministic HSL synthesizer (split-complement
  default, WCAG-gated accent) for genres without a curated row.

Colors are returned as opaque ``(r, g, b)`` 0-255 tuples or ``#rrggbb`` strings.
Anything we can't resolve to an opaque literal raises :class:`Unresolvable`
rather than guessing — a reported skip is honest; a guessed pass is dangerous.
"""

from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass

# --------------------------------------------------------------------------
# WCAG contrast primitives
# --------------------------------------------------------------------------

RGB = tuple[int, int, int]

# AA thresholds (WCAG 2.x §1.4.3 / §1.4.11).
AA_NORMAL = 4.5
AA_LARGE = 3.0  # large text (>=24px, or >=18.66px bold) and UI components


class Unresolvable(ValueError):
    """A color value we refuse to guess: var(), color-mix(), alpha<1, etc."""


_HEX_RE = re.compile(r"#([0-9a-fA-F]{3,8})\Z")


def parse_color(value: str) -> RGB:
    """Parse an opaque CSS color literal to ``(r, g, b)`` 0-255.

    Supports hex (``#rgb``/``#rgba``/``#rrggbb``/``#rrggbbaa``), ``rgb()/rgba()``
    (legacy comma or modern space form; 0-255 or %), and ``hsl()/hsla()``.
    Raises :class:`Unresolvable` for ``var()``, ``color-mix()``, ``light-dark()``,
    any alpha < 1, or unknown syntax — never guesses.
    """
    v = value.strip().lower()
    if not v:
        raise Unresolvable("empty")
    if "var(" in v or "color-mix(" in v or "light-dark(" in v or v == "currentcolor":
        raise Unresolvable(v)

    m = _HEX_RE.match(v)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) == 8:
            if int(h[6:8], 16) != 255:
                raise Unresolvable(v)  # translucent
            h = h[:6]
        if len(h) != 6:
            raise Unresolvable(v)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    m = re.fullmatch(r"rgba?\(([^)]+)\)", v)
    if m:
        parts = re.split(r"[,\s/]+", m.group(1).strip())
        if len(parts) < 3:
            raise Unresolvable(v)
        if len(parts) > 3 and not _alpha_ok(parts[3]):
            raise Unresolvable(v)
        return (_chan(parts[0]), _chan(parts[1]), _chan(parts[2]))

    m = re.fullmatch(r"hsla?\(([^)]+)\)", v)
    if m:
        parts = re.split(r"[,\s/]+", m.group(1).strip())
        if len(parts) < 3:
            raise Unresolvable(v)
        if len(parts) > 3 and not _alpha_ok(parts[3]):
            raise Unresolvable(v)
        h = float(re.sub(r"(deg|grad|rad|turn)$", "", parts[0])) / 360.0
        s = float(parts[1].rstrip("%")) / 100.0
        light = float(parts[2].rstrip("%")) / 100.0
        r, g, b = colorsys.hls_to_rgb(h % 1.0, light, s)  # NB: colorsys is HLS
        return (round(r * 255), round(g * 255), round(b * 255))

    raise Unresolvable(v)


def _chan(tok: str) -> int:
    tok = tok.strip()
    val = float(tok[:-1]) * 255 / 100 if tok.endswith("%") else float(tok)
    return max(0, min(255, round(val)))


def _alpha_ok(tok: str | None) -> bool:
    if tok is None:
        return True
    tok = tok.strip()
    a = float(tok[:-1]) / 100 if tok.endswith("%") else float(tok)
    return a >= 1.0


def _to_rgb(color: str | RGB) -> RGB:
    return color if isinstance(color, tuple) else parse_color(color)


def relative_luminance(color: str | RGB) -> float:
    """WCAG relative luminance of an opaque sRGB color."""
    r, g, b = (_lin(c / 255) for c in _to_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def contrast_ratio(a: str | RGB, b: str | RGB) -> float:
    """WCAG contrast ratio (1.0 .. 21.0) between two opaque colors."""
    la, lb = relative_luminance(a) + 0.05, relative_luminance(b) + 0.05
    hi, lo = max(la, lb), min(la, lb)
    return hi / lo


def passes_aa(a: str | RGB, b: str | RGB, *, large: bool = False) -> bool:
    """Whether the pair meets WCAG AA (compares the unrounded ratio)."""
    return contrast_ratio(a, b) >= (AA_LARGE if large else AA_NORMAL)


def best_text_on(bg: str | RGB) -> str:
    """Return ``#ffffff`` or ``#111111`` — whichever has more contrast on ``bg``."""
    return "#ffffff" if contrast_ratio("#ffffff", bg) >= contrast_ratio("#111111", bg) else "#111111"


# --------------------------------------------------------------------------
# Palette model + curated genre table
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Palette:
    """A small, structured palette: primary surface, supporting secondary, and
    a CTA accent, each with its on-color, plus a light bg/fg/border."""

    primary: str
    on_primary: str
    secondary: str
    accent: str
    on_accent: str
    bg: str
    fg: str
    border: str

    def as_css_vars(self) -> dict[str, str]:
        """The subset surfaced as CSS custom properties on the scaffold."""
        return {
            "--brand": self.primary,
            "--brand-contrast": self.on_primary,
            "--secondary": self.secondary,
            "--accent": self.accent,
            "--on-accent": self.on_accent,
        }


# Machine-readable mirror of design_reference/palettes.md. Keep in sync.
GENRE_PALETTES: dict[str, Palette] = {
    "auto_repair": Palette("#1E293B", "#FFFFFF", "#334155", "#DC2626", "#FFFFFF", "#F8FAFC", "#0F172A", "#E2E8F0"),
    "garage_door": Palette("#1E40AF", "#FFFFFF", "#3B82F6", "#EA580C", "#FFFFFF", "#EFF6FF", "#1E3A8A", "#BFDBFE"),
    "plumber": Palette("#1E40AF", "#FFFFFF", "#3B82F6", "#EA580C", "#FFFFFF", "#EFF6FF", "#1E3A8A", "#BFDBFE"),
    "electrician": Palette("#1E40AF", "#FFFFFF", "#3B82F6", "#F59E0B", "#0F172A", "#EFF6FF", "#1E3A8A", "#BFDBFE"),
    "roofer": Palette("#64748B", "#FFFFFF", "#94A3B8", "#EA580C", "#FFFFFF", "#F8FAFC", "#334155", "#E2E8F0"),
    "landscaper": Palette("#15803D", "#FFFFFF", "#22C55E", "#D97706", "#FFFFFF", "#F0FDF4", "#14532D", "#BBF7D0"),
    "house_cleaning": Palette("#059669", "#FFFFFF", "#10B981", "#EA580C", "#FFFFFF", "#ECFDF5", "#064E3B", "#A7F3D0"),
    "barber_shop": Palette("#1E293B", "#FFFFFF", "#334155", "#DC2626", "#FFFFFF", "#F8FAFC", "#0F172A", "#E2E8F0"),
    "beauty_salon": Palette("#EC4899", "#FFFFFF", "#F9A8D4", "#8B5CF6", "#FFFFFF", "#FDF2F8", "#831843", "#FBCFE8"),
    "nail_salon": Palette("#EC4899", "#FFFFFF", "#F9A8D4", "#8B5CF6", "#FFFFFF", "#FDF2F8", "#831843", "#FBCFE8"),
    "massage_therapy": Palette("#7C3AED", "#FFFFFF", "#8B5CF6", "#059669", "#FFFFFF", "#FAF5FF", "#0F172A", "#EFE7FC"),
    "dog_groomer": Palette("#0D9488", "#FFFFFF", "#14B8A6", "#EA580C", "#FFFFFF", "#F0FDFA", "#134E4A", "#99F6E4"),
    "bakery": Palette("#92400E", "#FFFFFF", "#B45309", "#E8557A", "#FFFFFF", "#FEF3C7", "#78350F", "#FDE68A"),
    "coffee_shop": Palette("#92400E", "#FFFFFF", "#B45309", "#C9472F", "#FFFFFF", "#FEF3C7", "#78350F", "#FDE68A"),
    "restaurant": Palette("#DC2626", "#FFFFFF", "#F87171", "#A16207", "#FFFFFF", "#FEF2F2", "#450A0A", "#FECACA"),
    "yoga_studio": Palette("#6B7280", "#FFFFFF", "#78716C", "#0891B2", "#FFFFFF", "#F5F5F0", "#0F172A", "#EDEEEF"),
    "tutoring": Palette("#0D9488", "#FFFFFF", "#2DD4BF", "#EA580C", "#FFFFFF", "#F0FDFA", "#134E4A", "#5EEAD4"),
    "music_lessons": Palette("#DC2626", "#FFFFFF", "#9A3412", "#D97706", "#FFFFFF", "#FFFBEB", "#0F172A", "#FAE4E4"),
    "accountant": Palette("#0F172A", "#FFFFFF", "#1E3A8A", "#A16207", "#FFFFFF", "#F8FAFC", "#020617", "#E2E8F0"),
    "notary": Palette("#1E3A8A", "#FFFFFF", "#1E40AF", "#B45309", "#FFFFFF", "#F8FAFC", "#0F172A", "#CBD5E1"),
}


def palette_for_genre(genre: str) -> Palette | None:
    """The curated :class:`Palette` for ``genre``, or ``None`` if unmapped."""
    return GENRE_PALETTES.get(genre)


# --------------------------------------------------------------------------
# Deterministic palette synthesizer (fallback for unmapped genres / brand color)
# --------------------------------------------------------------------------

# mood -> (secondary hue offset, accent hue offset, saturation scale)
_HARMONY = {
    "calm": (30, -30, 0.85),
    "friendly": (150, 210, 0.95),
    "bold": (25, 180, 1.00),
    "auto": (150, 210, 0.95),  # split-complement: the forgiving default
}


def _hex(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, round(r))), max(0, min(255, round(g))), max(0, min(255, round(b)))
    )


def _hsl_to_hex(h: float, s: float, light: float) -> str:
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, light, s)
    return _hex(r * 255, g * 255, b * 255)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def derive_palette(brand_hex: str, *, mood: str = "auto") -> Palette:
    """Synthesize a :class:`Palette` from a single brand color.

    Derives in HSL (split-complement by default), then clamps the accent into a
    WCAG-AA-legible band so CTA text stays readable. ``mood`` ∈
    {``calm``, ``friendly``, ``bold``, ``auto``}.
    """
    r, g, b = parse_color(brand_hex)
    bh, bl, bs = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    bh *= 360.0
    sec_off, acc_off, sat_scale = _HARMONY.get(mood, _HARMONY["auto"])

    secondary = _hsl_to_hex(
        bh + sec_off,
        _clamp(bs * sat_scale, 0.30, 0.65),
        _clamp(bl + (0.06 if bl < 0.5 else -0.06), 0.28, 0.58),
    )

    acc_h = bh + acc_off
    # Accent must differ enough from brand to read as "clickable".
    dh = min(abs(acc_h - bh) % 360, 360 - (abs(acc_h - bh) % 360))
    if dh < 40:
        acc_h = bh + 180
    acc_s = _clamp(max(bs, 0.62), 0.55, 0.85)
    acc_l = 0.50
    # Loop accent lightness until on-color text hits AA 4.5:1.
    accent = _hsl_to_hex(acc_h, acc_s, acc_l)
    for _ in range(14):
        on = best_text_on(accent)
        if contrast_ratio(on, accent) >= AA_NORMAL:
            break
        acc_l = _clamp(acc_l + (-0.04 if on == "#ffffff" else 0.04), 0.30, 0.66)
        accent = _hsl_to_hex(acc_h, acc_s, acc_l)

    return Palette(
        primary=brand_hex if brand_hex.startswith("#") else _hex(r, g, b),
        on_primary=best_text_on(brand_hex),
        secondary=secondary,
        accent=accent,
        on_accent=best_text_on(accent),
        bg="#ffffff",
        fg="#15172b",
        border="#e6e8ef",
    )
