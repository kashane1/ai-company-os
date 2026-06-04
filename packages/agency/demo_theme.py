"""Deterministic, offline theming (legacy token-fill + portfolio tooling).

**Not** used for customer-facing prospect mockups — those follow
``docs/demo-site-build-playbook.md`` (palette from real photos, ``dist-v2/``).
This module remains for:

* ``--legacy-build`` token-fill previews (deprecated bulk path)
* portfolio anonymization (``scripts/agency/build_portfolio_demos.py``)
* unit tests

Historically, every preview was the *same* template with only copy + a single
brand color swapped. This module gives each *generated* demo a distinct,
genre-appropriate identity — **palette**, **font pairing**, and **layout variant**
— derived only from warehouse data (``genre_id`` + ``place_id``).

By design (operator decision, see ``docs/agency/smarter-demos-plan.md``):

* **No network, no Google Places Photo API, no image analysis.** The look is
  *generated*, not read from the business's real signage/photos. This avoids
  per-fetch billing and photo ToS.
* **Fonts** come from a genre *style class* → a curated Google Font pairing
  (no exact-typeface guessing).
* **Layouts** are several genuinely different arrangements, assigned per
  business.

Determinism: every choice is seeded by a stable hash of ``place_id`` (NOT the
salted builtin ``hash()``), so re-runs are stable and two same-genre businesses
still differ (hue rotation + layout/pairing pick).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

# --- Layout variants ------------------------------------------------------
# CSS-driven arrangements over the existing scaffold markup (see
# ``theme_style_block``). Adding a name here requires matching CSS below.
LAYOUTS: tuple[str, ...] = ("split", "centered", "banner", "editorial")


# --- Font pairings --------------------------------------------------------
# ``kind`` selects the fallback stack so the page still reads well before the
# Google Font loads (and in the offline preview, which has no network).
@dataclass(frozen=True)
class FontPairing:
    heading: str
    body: str
    heading_kind: str  # serif | sans | display | slab
    body_kind: str


# Google Fonts axis weights to request per family (only weights that exist).
_FONT_WEIGHTS: dict[str, str] = {
    "Bebas Neue": "400",
    "Oswald": "500;700",
    "Archivo": "500;700",
    "Saira Condensed": "500;700",
    "Playfair Display": "500;700",
    "Cormorant Garamond": "500;600",
    "Fraunces": "400;600;700",
    "Lora": "500;700",
    "Spectral": "500;700",
    "Poppins": "500;700",
    "Manrope": "600;800",
    "Baloo 2": "500;700",
    "Inter": "400;600",
    "Nunito": "400;700",
    "Nunito Sans": "400;700",
    "Mulish": "400;700",
}

_FALLBACK_STACKS: dict[str, str] = {
    "serif": 'Georgia, "Times New Roman", serif',
    "sans": 'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    "display": "system-ui, -apple-system, sans-serif",
    "slab": 'Rockwell, "Roboto Slab", Georgia, serif',
}


# --- Per-genre style profile ---------------------------------------------
@dataclass(frozen=True)
class StyleProfile:
    style_class: str
    base_hue: int  # 0-360
    hue_jitter: int  # +/- degrees varied per business
    saturation: int  # %
    lightness: int  # % for --brand
    fonts: tuple[FontPairing, ...]
    layouts: tuple[str, ...]


# Curated pairings reused across profiles.
_F_INDUSTRIAL = (
    FontPairing("Oswald", "Inter", "display", "sans"),
    FontPairing("Archivo", "Inter", "sans", "sans"),
)
_F_TRADES = (
    FontPairing("Archivo", "Inter", "sans", "sans"),
    FontPairing("Saira Condensed", "Inter", "display", "sans"),
)
_F_VINTAGE = (FontPairing("Bebas Neue", "Inter", "display", "sans"),)
_F_ELEGANT = (
    FontPairing("Playfair Display", "Nunito Sans", "serif", "sans"),
    FontPairing("Cormorant Garamond", "Mulish", "serif", "sans"),
)
_F_WARM = (
    FontPairing("Fraunces", "Nunito", "serif", "sans"),
    FontPairing("Lora", "Nunito", "serif", "sans"),
)
_F_PLAYFUL = (FontPairing("Baloo 2", "Nunito", "display", "sans"),)
_F_CALM = (FontPairing("Cormorant Garamond", "Mulish", "serif", "sans"),)
_F_FRIENDLY = (FontPairing("Poppins", "Inter", "sans", "sans"),)
_F_PROFESSIONAL = (FontPairing("Spectral", "Inter", "serif", "sans"),)
_F_DEFAULT = (FontPairing("Manrope", "Inter", "sans", "sans"),)


STYLE_PROFILES: dict[str, StyleProfile] = {
    "auto_repair": StyleProfile("industrial", 14, 16, 68, 48, _F_INDUSTRIAL, ("split", "banner", "editorial")),
    "garage_door": StyleProfile("industrial", 210, 18, 60, 44, _F_INDUSTRIAL, ("split", "banner")),
    "plumber": StyleProfile("trades", 208, 26, 66, 45, _F_TRADES, ("split", "banner")),
    "electrician": StyleProfile("trades", 38, 14, 78, 50, _F_TRADES, ("split", "banner")),
    "roofer": StyleProfile("trades", 16, 18, 60, 44, _F_TRADES, ("split", "editorial")),
    "landscaper": StyleProfile("trades", 130, 24, 48, 40, _F_TRADES, ("split", "banner")),
    "house_cleaning": StyleProfile("trades", 188, 26, 58, 46, _F_TRADES, ("centered", "split")),
    "barber_shop": StyleProfile("vintage", 28, 12, 52, 36, _F_VINTAGE, ("banner", "editorial", "centered")),
    "beauty_salon": StyleProfile("elegant", 330, 24, 46, 55, _F_ELEGANT, ("centered", "editorial")),
    "nail_salon": StyleProfile("elegant", 318, 28, 50, 58, _F_ELEGANT, ("centered", "editorial")),
    "massage_therapy": StyleProfile("calm", 168, 22, 32, 44, _F_CALM, ("centered", "editorial")),
    "dog_groomer": StyleProfile("playful", 178, 40, 58, 45, _F_PLAYFUL, ("centered", "banner", "split")),
    "bakery": StyleProfile("warm", 24, 18, 60, 47, _F_WARM, ("centered", "split", "editorial")),
    "coffee_shop": StyleProfile("warm", 30, 14, 46, 38, _F_WARM, ("editorial", "centered", "split")),
    "restaurant": StyleProfile("warm", 8, 20, 62, 46, _F_WARM, ("banner", "centered", "editorial")),
    "yoga_studio": StyleProfile("calm", 140, 26, 30, 42, _F_CALM, ("centered", "editorial")),
    "tutoring": StyleProfile("friendly", 250, 40, 64, 56, _F_FRIENDLY, ("split", "centered", "banner")),
    "music_lessons": StyleProfile("friendly", 280, 40, 56, 54, _F_FRIENDLY, ("split", "centered", "banner")),
    "accountant": StyleProfile("professional", 218, 16, 46, 38, _F_PROFESSIONAL, ("split", "editorial")),
    "notary": StyleProfile("professional", 222, 14, 40, 36, _F_PROFESSIONAL, ("split", "editorial")),
}

_DEFAULT_PROFILE = StyleProfile("default", 245, 30, 60, 55, _F_DEFAULT, ("split", "centered"))


# --- Color helpers (pure) -------------------------------------------------
def _hsl_to_rgb(h: float, s: float, lightness: float) -> tuple[int, int, int]:
    """h in [0,360), s/lightness in [0,1] -> (r,g,b) 0-255."""
    h = h % 360.0
    c = (1 - abs(2 * lightness - 1)) * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = lightness - c / 2
    if h < 60:
        r, g, b = c, x, 0.0
    elif h < 120:
        r, g, b = x, c, 0.0
    elif h < 180:
        r, g, b = 0.0, c, x
    elif h < 240:
        r, g, b = 0.0, x, c
    elif h < 300:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x
    return (round((r + m) * 255), round((g + m) * 255), round((b + m) * 255))


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG relative luminance, 0 (black) .. 1 (white)."""

    def chan(c: int) -> float:
        cs = c / 255.0
        return cs / 12.92 if cs <= 0.03928 else ((cs + 0.055) / 1.055) ** 2.4

    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


_NEAR_BLACK = "#15172b"


def _contrast_for(rgb: tuple[int, int, int]) -> str:
    """White text on a dark/saturated brand, near-black on a light one."""
    return "#ffffff" if _relative_luminance(rgb) < 0.5 else _NEAR_BLACK


# --- Seeding --------------------------------------------------------------
def _seed(place_id: str) -> int:
    """Stable, process-independent seed (builtin hash() is salted)."""
    digest = hashlib.sha256((place_id or "seed").encode("utf-8")).hexdigest()
    return int(digest, 16)


def _pick(seq, seed: int):
    return seq[seed % len(seq)]


# --- The theme ------------------------------------------------------------
@dataclass(frozen=True)
class DemoTheme:
    style_class: str
    layout: str
    brand: str
    brand_strong: str
    brand_contrast: str
    heading_font: str
    body_font: str
    heading_stack: str
    body_stack: str
    font_import_url: str

    def to_dict(self) -> dict[str, str]:
        return {
            "style_class": self.style_class,
            "layout": self.layout,
            "brand": self.brand,
            "brand_strong": self.brand_strong,
            "heading_font": self.heading_font,
            "body_font": self.body_font,
        }


def _font_import_url(pairing: FontPairing) -> str:
    families = []
    for fam in (pairing.heading, pairing.body):
        weights = _FONT_WEIGHTS.get(fam, "400;700")
        name = fam.replace(" ", "+")
        families.append(f"family={name}:wght@{weights}")
    return "https://fonts.googleapis.com/css2?" + "&".join(families) + "&display=swap"


def theme_for_record(record: dict) -> DemoTheme:
    """Deterministically derive a :class:`DemoTheme` from a warehouse record."""
    genre = str(record.get("genre_id", ""))
    profile = STYLE_PROFILES.get(genre, _DEFAULT_PROFILE)
    seed = _seed(str(record.get("place_id", "")))

    # Independent draws from different slices of the seed so they don't correlate.
    layout = _pick(profile.layouts, seed)
    pairing = _pick(profile.fonts, seed >> 8)
    # Hue jitter in [-jitter, +jitter].
    span = profile.hue_jitter * 2 + 1
    hue = (profile.base_hue + ((seed >> 16) % span) - profile.hue_jitter) % 360

    sat = profile.saturation / 100.0
    light = profile.lightness / 100.0
    brand_rgb = _hsl_to_rgb(hue, sat, light)
    strong_rgb = _hsl_to_rgb(hue, min(1.0, sat + 0.05), max(0.20, light - 0.12))

    return DemoTheme(
        style_class=profile.style_class,
        layout=layout,
        brand=_hex(brand_rgb),
        brand_strong=_hex(strong_rgb),
        brand_contrast=_contrast_for(brand_rgb),
        heading_font=pairing.heading,
        body_font=pairing.body,
        heading_stack=f'"{pairing.heading}", {_FALLBACK_STACKS[pairing.heading_kind]}',
        body_stack=f'"{pairing.body}", {_FALLBACK_STACKS[pairing.body_kind]}',
        font_import_url=_font_import_url(pairing),
    )


# --- Render integration ---------------------------------------------------
_LAYOUT_CSS = """
/* split — text + visual side by side (explicit base) */
body[data-layout="split"] .hero-grid{align-items:center;}

/* centered — single column, no side visual, larger headline */
body[data-layout="centered"] .hero-grid{grid-template-columns:1fr;text-align:center;justify-items:center;max-width:820px;margin-inline:auto;}
body[data-layout="centered"] .hero-visual{display:none;}
body[data-layout="centered"] .hero h1{font-size:var(--step-4);}
body[data-layout="centered"] .hero-actions{justify-content:center;}

/* banner — full-bleed brand-colored hero band */
body[data-layout="banner"] .hero{background:linear-gradient(135deg,var(--brand),var(--brand-strong));}
body[data-layout="banner"] .hero .eyebrow,body[data-layout="banner"] .hero h1,body[data-layout="banner"] .hero .hero-sub,body[data-layout="banner"] .hero .hero-note{color:var(--brand-contrast);}
body[data-layout="banner"] .hero-grid{grid-template-columns:1fr;text-align:center;justify-items:center;max-width:880px;margin-inline:auto;}
body[data-layout="banner"] .hero-visual{display:none;}
body[data-layout="banner"] .hero .btn-primary{background:var(--brand-contrast);color:var(--brand);}
body[data-layout="banner"] .hero .btn-ghost{color:var(--brand-contrast);border-color:color-mix(in srgb,var(--brand-contrast) 55%,transparent);}

/* editorial — asymmetric, oversized left-aligned headline */
body[data-layout="editorial"] .hero-grid{grid-template-columns:1.5fr 0.9fr;align-items:center;gap:var(--space-lg);}
body[data-layout="editorial"] .hero h1{font-size:var(--step-4);line-height:1.03;letter-spacing:-0.02em;}
body[data-layout="editorial"] .hero .eyebrow{letter-spacing:0.18em;text-transform:uppercase;}
body[data-layout="editorial"] .section .center{text-align:left;margin-inline:0;}
"""


def theme_style_block(theme: DemoTheme) -> str:
    """The ``<link>`` + ``<style>`` that applies a theme to the scaffold markup.

    Overrides only the brand trio + font vars (neutrals are left to the template
    so its dark-mode handling keeps working), then carries the per-layout CSS.
    """
    return (
        f'<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link rel="stylesheet" href="{theme.font_import_url}">\n'
        "<style>\n"
        ":root{\n"
        f"  --brand:{theme.brand};\n"
        f"  --brand-strong:{theme.brand_strong};\n"
        f"  --brand-contrast:{theme.brand_contrast};\n"
        f"  --font-heading:{theme.heading_stack};\n"
        f"  --font-body:{theme.body_stack};\n"
        "}\n"
        "body{font-family:var(--font-body);}\n"
        "h1,h2,h3,.brand,.eyebrow{font-family:var(--font-heading);}\n"
        f"{_LAYOUT_CSS}"
        "</style>"
    )


def apply_theme(html: str, theme: DemoTheme) -> str:
    """Inject the theme into rendered scaffold HTML.

    Appends the style block just before ``</head>`` (so its ``:root`` overrides
    win over the inlined ``global.css``) and stamps ``data-layout`` on ``<body>``.
    """
    block = theme_style_block(theme)
    if "</head>" in html:
        html = html.replace("</head>", f"  {block}\n</head>", 1)
    else:  # pragma: no cover - scaffold always has a head
        html = block + html
    # Stamp the layout on <body>. The scaffold's body tag is a bare "<body>".
    html = html.replace("<body>", f'<body data-layout="{theme.layout}" data-theme="{theme.style_class}">', 1)
    return html
