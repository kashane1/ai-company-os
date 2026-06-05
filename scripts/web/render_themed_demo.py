#!/usr/bin/env python3
"""Render a landing page themed by the design-intelligence palette + font reference.

A small bridge that proves out ``packages/web/palette.py`` end to end: it takes a
genre + business copy, renders the Astro scaffold offline, applies the genre's
structured :class:`Palette` (navy/slate/red for auto repair, etc.) and a
vibe-matched font pairing (from ``design_reference/font_pairings.md``) as ``:root``
overrides, validates the result through the web gate (incl. the new contrast
check), and writes a ``dist/index.html``.

Usage:
    python scripts/web/render_themed_demo.py            # Ironside auto-repair demo
    python scripts/web/render_themed_demo.py --out DIR  # custom output dir

Then screenshot it:
    node scripts/web/shoot.mjs <out> docs/products/better-business-web/screenshots /:auto-repair-v2
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from packages.web.palette import Palette, palette_for_genre  # noqa: E402
from packages.web.scaffold import render_landing_html, unfilled_tokens  # noqa: E402
from packages.web.validation import validate_web_dist  # noqa: E402

# Vibe-matched pairings lifted from design_reference/font_pairings.md (weights verified).
FONT_PAIRINGS: dict[str, dict[str, str]] = {
    "auto_repair": {
        "heading": '"Oswald", system-ui, sans-serif',
        "body": '"Inter", system-ui, sans-serif',
        "import": "https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700"
        "&family=Inter:wght@400;500;600&display=swap",
    },
}


def theme_block(pal: Palette, fonts: dict[str, str]) -> str:
    """The ``<link>`` + ``<style>`` that re-skins the scaffold with a Palette.

    Injected after global.css so its ``:root`` wins. The accent becomes the CTA
    (classic auto-shop red on the navy/white system); headings take the display
    font. Only light-mode is overridden — the screenshot renders light.
    """
    return f"""<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{fonts['import']}">
<style>
:root {{
  --brand: {pal.primary}; --brand-strong: #0f172a; --brand-contrast: {pal.on_primary};
  --secondary: {pal.secondary}; --accent: {pal.accent}; --on-accent: {pal.on_accent};
  --bg: {pal.bg}; --surface: #ffffff; --bg-subtle: #eef2f7; --border: {pal.border};
  --text: {pal.fg}; --text-muted: #475569;
  --font-heading: {fonts['heading']}; --font-body: {fonts['body']};
}}
body {{ font-family: var(--font-body); }}
h1, h2, h3, .eyebrow {{ font-family: var(--font-heading); }}
h1, h2 {{ text-transform: uppercase; letter-spacing: 0.005em; }}
/* Accent as the primary CTA — red pops on the navy/white system. */
.btn-primary {{ background: var(--accent); color: var(--on-accent); }}
.btn-primary:hover {{ background: #b91c1c; }}
.eyebrow {{ color: var(--accent); }}
.icon {{ background: color-mix(in srgb, var(--brand) 8%, transparent); }}
</style>"""


def photo_hero_block() -> str:
    """Full-bleed photo hero: the shop photo under a dark navy gradient, white
    text, red CTA — closes the visual gap with the hand-built bespoke demo.
    Text contrast holds (white on a ~85% navy overlay); the photo is a CSS
    background (no ``<img>``, so no alt needed)."""
    return """<style>
.hero {
  position: relative;
  background:
    linear-gradient(180deg, rgba(15,23,42,0.72) 0%, rgba(15,23,42,0.88) 100%),
    url('assets/hero.jpg');
  background-size: cover;
  background-position: center 35%;
  color: #fff;
  padding-block: var(--space-xl);
}
.hero .hero-grid { grid-template-columns: 1fr; max-width: 760px; }
.hero-visual { display: none; }
.hero h1, .hero .hero-sub { color: #fff; }
.hero .hero-note { color: #e2e8f0; }
.hero .btn-ghost { color: #fff; border-color: rgba(255,255,255,0.45); }
.hero .btn-ghost:hover { background: rgba(255,255,255,0.12); }
</style>"""


# Real Ironside Auto Works copy (anonymized portfolio business; services verbatim
# from the existing demo so the rebuild is the same business, not invented).
IRONSIDE_CONTEXT: dict[str, str] = {
    "SITE_NAME": "Ironside Auto Works",
    "PACKAGE_NAME": "ironside-auto-works",
    "SITE_URL": "https://example.com",
    "TAGLINE": "Tires, brakes & alignment — done right, priced fair",
    "META_DESCRIPTION": "Honest tire & auto repair on Maplewood's Birch Ave. Tires, "
    "brakes, alignment, A/C, tune-ups. No upsell — just what your car needs.",
    "EYEBROW": "Auto Repair · Maplewood",
    "HERO_HEADLINE": "Tires, brakes & alignment — done right, priced fair.",
    "HERO_SUBHEAD": "Honest auto repair on Maplewood's Birch Ave. We put it on the lift, "
    "show you the problem, and give you a straight answer — never an upsell.",
    "PRIMARY_CTA": "Call (503) 555-0142",
    "SECONDARY_CTA": "See our services",
    "HERO_NOTE": "4.5★ · 500+ Google reviews · Hunter alignment on-site",
    "TRUST_LABEL": "Trusted by Maplewood drivers",
    "TRUST_1": "ASE Certified", "TRUST_2": "Hunter Alignment",
    "TRUST_3": "NAPA Parts", "TRUST_4": "12-Mo Warranty",
    "FEATURES_HEADLINE": "What we fix",
    "FEATURES_SUBHEAD": "Six bays, a mechanic-owner on site, and no run-around.",
    "FEATURE_1_TITLE": "Tires",
    "FEATURE_1_BODY": "New and used, flat repair, patches, and full replacements. We show "
    "you the damage so you decide — patch or replace.",
    "FEATURE_2_TITLE": "Wheel Alignment",
    "FEATURE_2_BODY": "Computerized Hunter alignment on-site to protect your tires and keep "
    "your steering straight.",
    "FEATURE_3_TITLE": "Brakes",
    "FEATURE_3_BODY": "Inspection, pad replacement, and rotor service. Don't wait for the "
    "grind — we'll check them and give you a straight answer.",
    "HOW_HEADLINE": "How a visit works",
    "STEP_1_TITLE": "Drop by", "STEP_1_BODY": "Walk in or call — no appointment needed for most jobs.",
    "STEP_2_TITLE": "We show you", "STEP_2_BODY": "It goes on the lift and we show you what's actually wrong.",
    "STEP_3_TITLE": "Straight quote", "STEP_3_BODY": "Clear price, no upsell. We fix what needs fixing.",
    "TESTIMONIAL": "Showed me the worn pad, quoted me fair, and had me out in an hour. Found my new shop.",
    "TESTIMONIAL_AUTHOR": "— Google review · 5 stars",
    "CTA_HEADLINE": "Need tires or a brake check in Maplewood?",
    "CTA_SUBHEAD": "Call (503) 555-0142 or stop by 1200 Birch Ave. Fast, honest, fair.",
    "FAQ_HEADLINE": "Frequently asked questions",
    "FAQ_1_Q": "Do I need an appointment?",
    "FAQ_1_A": "Walk-ins are welcome for tires, flats, and quick checks. Call ahead for bigger jobs.",
    "FAQ_2_Q": "Do you offer a warranty?",
    "FAQ_2_A": "Yes — a 12-month warranty on most parts and labor.",
    "FAQ_3_Q": "What areas do you serve?",
    "FAQ_3_A": "Ironside Auto Works serves Maplewood and the surrounding area.",
    "YEAR": "2026",
    "FOOTER_NOTE": "1200 Birch Ave, Maplewood, OR · (503) 555-0142",
    "STRIPE_PRICE_ID": "price_demo",
}


def polish_block() -> str:
    """Stats bar + CTA-card recolor styles (the bespoke-parity polish)."""
    return """<style>
.stats-bar { background: var(--brand); }
.stats-bar .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-md); text-align: center; }
.stat-num { display: block; font-family: var(--font-heading); font-weight: 700; font-size: var(--step-3); line-height: 1; color: #fff; }
.stat-num.accent { color: var(--accent); }
.stat-label { display: block; margin-top: 0.4em; font-size: var(--step--1); letter-spacing: 0.08em; text-transform: uppercase; color: #cbd5e1; }
@media (max-width: 640px) { .stats-bar .stats { grid-template-columns: repeat(2, 1fr); } }
/* Stats replace the default badge bar. */
.section:has(> .container > .trust) { display: none; }
/* CTA card → navy/red palette (was an off-palette plum gradient). */
.cta-card { background: linear-gradient(135deg, var(--brand) 0%, #0f172a 100%); }
.cta-card .btn-ghost { background: var(--accent); color: #fff; border-color: var(--accent); }
.cta-card .btn-ghost:hover { background: #b91c1c; }
</style>"""


# Stats for the navy trust bar: (number, label, accent?). Numbers trace to the
# real business (4.5★ / 500+ reviews) + verified services (Hunter alignment).
IRONSIDE_STATS = [
    ("4.5★", "Google rating", True),
    ("500+", "Reviews", False),
    ("7", "Days a week", False),
    ("Hunter", "Alignment on-site", False),
]


def _stats_section(stats: list[tuple[str, str, bool]]) -> str:
    cells = "".join(
        f'<div class="stat"><span class="stat-num{" accent" if accent else ""}">{num}</span>'
        f'<span class="stat-label">{label}</span></div>'
        for num, label, accent in stats
    )
    return (
        '<section class="section stats-bar" style="padding-block:var(--space-md)">'
        f'<div class="container stats">{cells}</div></section>'
    )


def enrich_html(html: str, stats: list[tuple[str, str, bool]]) -> str:
    """Inject the stats bar after the hero and swap the email form for call CTAs."""
    i = html.find('class="hero"')
    close = html.find("</section>", i)
    if close != -1:
        close += len("</section>")
        html = html[:close] + "\n" + _stats_section(stats) + html[close:]
    call = (
        '<div class="cta-form" style="display:flex;gap:var(--space-sm);'
        'justify-content:center;flex-wrap:wrap">'
        '<a class="btn btn-ghost btn-lg" href="tel:+15035550142">Call (503) 555-0142</a>'
        '<a class="btn btn-ghost btn-lg" '
        'href="https://maps.google.com/?q=1200+Birch+Ave+Maplewood+OR" '
        'style="background:transparent;border-color:rgba(255,255,255,0.45);color:#fff">'
        "Get directions</a></div>"
    )
    html = re.sub(r'<form class="cta-form".*?</form>', call, html, count=1, flags=re.DOTALL)
    return html


def build(genre: str, context: dict[str, str], out: Path, hero_photo: Path | None = None) -> None:
    pal = palette_for_genre(genre)
    if pal is None:
        raise SystemExit(f"no curated palette for genre {genre!r}")
    fonts = FONT_PAIRINGS[genre]

    html = render_landing_html(context)
    leftover = unfilled_tokens(html)
    if leftover:
        raise SystemExit(f"unfilled tokens: {leftover}")
    html = enrich_html(html, IRONSIDE_STATS)
    head_inject = theme_block(pal, fonts) + "\n  " + polish_block()
    if hero_photo:
        head_inject += "\n  " + photo_hero_block()
    html = html.replace("</head>", f"  {head_inject}\n</head>", 1)

    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    if hero_photo:
        (out / "assets").mkdir(exist_ok=True)
        shutil.copyfile(hero_photo, out / "assets" / "hero.jpg")

    report = validate_web_dist(out)
    print(f"built {out/'index.html'}")
    print(f"palette: brand={pal.primary} secondary={pal.secondary} accent={pal.accent}")
    for c in report.checks:
        print(f"  {'PASS' if c.passed else 'FAIL'} {c.name}: {c.details[:90]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--genre", default="auto_repair")
    ap.add_argument("--out", default=str(ROOT / "build" / "themed-demos" / "auto-repair-v2"))
    ap.add_argument(
        "--hero-photo",
        default=str(
            ROOT / "products/better-business-web/portfolio/auto_repair/dist/assets/tech-working.jpg"
        ),
        help="brand-neutral hero photo; pass '' to use the abstract visual instead",
    )
    args = ap.parse_args()
    hero = Path(args.hero_photo) if args.hero_photo else None
    build(args.genre, IRONSIDE_CONTEXT, Path(args.out), hero_photo=hero)


if __name__ == "__main__":
    main()
