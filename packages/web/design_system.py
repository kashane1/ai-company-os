"""Design System Synthesizer — Phase 1 of the design engine.

Turns a :class:`~packages.web.design_studio.DesignStudioPacket` into a complete,
role-based token set: a dominant canvas + memorable accent (WCAG-AA gated), a
premium type pairing that escapes the genre default, a zoom-safe modular type
scale, spacing/radius/elevation, and archetype-selected signature treatments.

This is the deterministic, testable craft layer. It does **not** judge taste (the
visual rubric does that) — it guarantees the *contract* a five-figure build needs:
same packet → identical tokens, AA-valid roles, a monotonic zoom-safe scale, and a
valid W3C DTCG token document the premium stack (and downstream tooling like Style
Dictionary) consumes.

Color math is delegated to :mod:`packages.web.palette` (the color engine); this
module owns the non-color tiers and assembles the role set.
"""

from __future__ import annotations

import colorsys
from dataclasses import dataclass, field

from packages.web.design_studio import DesignStudioPacket
from packages.web.palette import (
    AA_NORMAL,
    GENRE_PALETTES,
    Palette,
    best_text_on,
    contrast_ratio,
    derive_palette,
    parse_color,
)

# Archetypes that read as premium on a dark canvas + warm-metal accent.
_DARK_ARCHETYPES = {"service-area-cinematic", "product-led"}

# Archetype -> (type ratio, display family, body family, mono family).
# Display faces are chosen to escape the genre cliché (an editorial serif over a
# trades site reads premium; a precise grotesk over SaaS reads engineered).
_TYPE: dict[str, tuple[float, str, str, str]] = {
    "service-area-cinematic": (1.333, "Fraunces", "Inter", "Spline Sans Mono"),
    "product-led": (1.2, "Inter Tight", "Inter", "Spline Sans Mono"),
    "gallery-led": (1.25, "Cormorant Garamond", "Inter", "Spline Sans Mono"),
    "editorial-visit": (1.25, "Fraunces", "Newsreader", "Spline Sans Mono"),
    "classic-custom": (1.25, "Fraunces", "Inter", "Spline Sans Mono"),
}

# Archetype -> opt-in signature surface treatments.
_TREATMENTS: dict[str, list[str]] = {
    "service-area-cinematic": ["grain", "glow", "hairline"],
    "product-led": ["gradient-mesh", "glow", "hairline"],
    "gallery-led": ["grain", "hairline"],
    "editorial-visit": ["grain", "hairline"],
    "classic-custom": ["hairline"],
}

# business_category substring -> GENRE_PALETTES key (archetype↔genre bridge).
_GENRE_BRIDGE: list[tuple[tuple[str, ...], str]] = [
    (("plumb",), "plumber"),
    (("roof",), "roofer"),
    (("electric",), "electrician"),
    (("hvac", "garage"), "garage_door"),
    (("landscap", "lawn"), "landscaper"),
    (("clean",), "house_cleaning"),
    (("nail",), "nail_salon"),
    (("salon", "beauty", "hair"), "beauty_salon"),
    (("barber",), "barber_shop"),
    (("groom", "pet"), "dog_groomer"),
    (("bakery", "bake"), "bakery"),
    (("coffee", "cafe"), "coffee_shop"),
    (("restaurant", "bistro", "eatery"), "restaurant"),
    (("massage", "spa"), "massage_therapy"),
    (("yoga",), "yoga_studio"),
    (("account", "bookkeep", "tax"), "accountant"),
    (("auto", "mechanic", "repair"), "auto_repair"),
]

_FONT_FALLBACK = {
    "Fraunces": "Georgia, 'Times New Roman', serif",
    "Cormorant Garamond": "Georgia, serif",
    "Newsreader": "Georgia, serif",
    "Inter": "system-ui, -apple-system, sans-serif",
    "Inter Tight": "system-ui, -apple-system, sans-serif",
    "Spline Sans Mono": "ui-monospace, 'SF Mono', monospace",
}


@dataclass(frozen=True)
class TypeStep:
    """One step of the modular type scale, with a zoom-safe fluid clamp."""

    step: int
    min_rem: float
    max_rem: float

    @property
    def name(self) -> str:
        return f"--step-{self.step}" if self.step >= 0 else f"--step-n{abs(self.step)}"

    def to_css_clamp(self) -> str:
        # Small steps (caption/body) stay fixed so body never drops below 1rem and
        # captions don't shrink under zoom. Larger steps go fluid — and the
        # preferred term keeps a rem base (WCAG 1.4.4: a vw-only term freezes zoom).
        if self.step <= 0 or self.max_rem <= self.min_rem:
            return f"{self.max_rem}rem"
        slope_vw = round((self.max_rem - self.min_rem) * 16 / 9.2, 3)
        return f"clamp({self.min_rem}rem, {self.min_rem}rem + {slope_vw}vw, {self.max_rem}rem)"


@dataclass(frozen=True)
class DesignSystem:
    """The synthesized, role-based token set for one premium build."""

    archetype: str
    roles: dict[str, str]  # semantic color roles
    fonts: dict[str, str]  # display / body / mono families
    type_ratio: float
    type_scale: list[TypeStep]
    space_unit_rem: float
    radius_rem: float
    treatments: list[str] = field(default_factory=list)

    # ---- W3C DTCG token document (interop artifact) -----------------------
    def to_dtcg(self) -> dict:
        primitive = {
            key: {"$type": "color", "$value": value} for key, value in self.roles.items()
        }
        semantic = {
            key: {"$type": "color", "$value": f"{{color.primitive.{key}}}"}
            for key in self.roles
        }
        sizes = {
            step.name.removeprefix("--"): {"$type": "dimension", "$value": f"{step.max_rem}rem"}
            for step in self.type_scale
        }
        return {
            "$description": f"Design system for a {self.archetype} premium build.",
            "color": {"primitive": primitive, **semantic},
            "font": {
                "display": {"$type": "fontFamily", "$value": self.fonts["display"]},
                "body": {"$type": "fontFamily", "$value": self.fonts["body"]},
                "mono": {"$type": "fontFamily", "$value": self.fonts["mono"]},
            },
            "size": sizes,
            "space": {"unit": {"$type": "dimension", "$value": f"{self.space_unit_rem}rem"}},
            "radius": {"md": {"$type": "dimension", "$value": f"{self.radius_rem}rem"}},
            "ratio": {"type-scale": {"$type": "number", "$value": self.type_ratio}},
        }

    # ---- Resolved CSS the premium stack consumes --------------------------
    def to_css(self) -> str:
        lines = [":root {"]
        for role, value in self.roles.items():
            lines.append(f"  --{role}: {value};")
        lines.append(f"  --display-font: {_stack(self.fonts['display'])};")
        lines.append(f"  --body-font: {_stack(self.fonts['body'])};")
        lines.append(f"  --mono-font: {_stack(self.fonts['mono'])};")
        lines.append(f"  --type-ratio: {self.type_ratio};")
        lines.append(f"  --space-unit: {self.space_unit_rem}rem;")
        lines.append(f"  --radius: {self.radius_rem}rem;")
        for step in self.type_scale:
            lines.append(f"  {step.name}: {step.to_css_clamp()};")
        for treatment in self.treatments:
            lines.append(f"  --treatment-{treatment}: 1;")
        lines.append("}")
        return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Synthesis
# --------------------------------------------------------------------------- #
def synthesize_design_system(packet: DesignStudioPacket) -> DesignSystem:
    """Build the full role-based token set from a packet (deterministic)."""

    archetype = packet.archetype if packet.archetype in _TYPE else "classic-custom"
    ratio, display, body, mono = _TYPE[archetype]
    is_dark = archetype in _DARK_ARCHETYPES

    roles = _color_roles(packet, archetype, is_dark=is_dark)
    return DesignSystem(
        archetype=archetype,
        roles=roles,
        fonts={"display": display, "body": body, "mono": mono},
        type_ratio=ratio,
        type_scale=_type_scale(ratio),
        space_unit_rem=0.5,
        radius_rem=0.75 if archetype != "product-led" else 0.5,
        treatments=list(_TREATMENTS.get(archetype, ["hairline"])),
    )


def _color_roles(packet: DesignStudioPacket, archetype: str, *, is_dark: bool) -> dict[str, str]:
    seed = _seed_hex(packet)
    base = derive_palette(seed)
    base_h = _hue(seed)

    if is_dark:
        canvas = _hsl(base_h, 0.30, 0.08)
        ink = _hsl(base_h, 0.10, 0.93)
        muted = _hsl(base_h, 0.08, 0.66)
        border = _hsl(base_h, 0.22, 0.20)
        # Cinematic default to a warm-metal accent (copper), unless a concept
        # palette was supplied — then honor the seed's derived accent.
        accent_h = base_h if packet.concept_palette.strip() else 32.0
        accent = _aa_accent(accent_h, 0.62)
    else:
        canvas = _hsl(base_h, 0.28, 0.985)
        ink = _hsl(base_h, 0.30, 0.11)
        muted = _hsl(base_h, 0.12, 0.40)
        border = _hsl(base_h, 0.20, 0.88)
        accent = base.accent

    accent_strong = _shift_l(accent, -0.10)
    return {
        "canvas": canvas,
        "ink": ink,
        "muted": muted,
        "border": border,
        "accent": accent,
        "accent-strong": accent_strong,
        "on-accent": best_text_on(accent),
    }


def _type_scale(ratio: float) -> list[TypeStep]:
    steps: list[TypeStep] = []
    for step in range(-1, 7):
        max_rem = round(ratio**step, 4) if step != 0 else 1.0
        min_rem = max_rem if step <= 0 else round(max_rem * 0.78, 4)
        steps.append(TypeStep(step=step, min_rem=min_rem, max_rem=max_rem))
    return steps


# --------------------------------------------------------------------------- #
# Color helpers (thin layer over palette.py / colorsys)
# --------------------------------------------------------------------------- #
def _seed_hex(packet: DesignStudioPacket) -> str:
    cue = packet.concept_palette.strip()
    if cue.startswith("#"):
        try:
            parse_color(cue)
            return cue
        except ValueError:
            pass
    genre = _genre_key(packet.business_category)
    if genre and genre in GENRE_PALETTES:
        return _palette_primary(GENRE_PALETTES[genre])
    return "#1e3a5f"  # a calm, premium-leaning default seed


def _palette_primary(pal: Palette) -> str:
    return pal.primary


def _genre_key(category: str) -> str | None:
    c = category.lower()
    for needles, key in _GENRE_BRIDGE:
        if any(n in c for n in needles):
            return key
    return None


def _hue(hex_color: str) -> float:
    r, g, b = parse_color(hex_color)
    h, _, _ = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return h * 360.0


def _hsl(h: float, s: float, light: float) -> str:
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, light, s)
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def _shift_l(hex_color: str, delta: float) -> str:
    r, g, b = parse_color(hex_color)
    h, light, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return _hsl(h * 360, s, max(0.0, min(1.0, light + delta)))


def _aa_accent(h: float, s: float) -> str:
    """An accent at hue ``h`` whose best on-color text clears AA 4.5:1."""
    light = 0.50
    accent = _hsl(h, s, light)
    for _ in range(16):
        on = best_text_on(accent)
        if contrast_ratio(on, accent) >= AA_NORMAL:
            break
        light += -0.04 if on == "#ffffff" else 0.04
        light = max(0.30, min(0.70, light))
        accent = _hsl(h, s, light)
    return accent


def _stack(family: str) -> str:
    fallback = _FONT_FALLBACK.get(family, "sans-serif")
    return f"'{family}', {fallback}"
