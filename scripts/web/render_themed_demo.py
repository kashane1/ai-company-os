#!/usr/bin/env python3
"""Render Better Business Web portfolio demos through the design-intelligence stack.

Proves out ``packages/web/palette.py`` end to end across every portfolio genre:
each demo renders the Astro scaffold, applies the genre's structured
:class:`Palette` + a vibe-matched font pairing (from
``design_reference/font_pairings.md``) as ``:root`` overrides, adds a brand-tinted
photo hero, a stats bar, and a local-business call CTA, then validates through the
web gate (incl. the new contrast check).

Usage:
    python scripts/web/render_themed_demo.py                 # build all genres
    python scripts/web/render_themed_demo.py --genre bakery  # one genre
    python scripts/web/render_themed_demo.py --out DIR       # output base dir

Each demo writes ``<out>/<slug>/index.html`` (+ assets/hero.jpg). Screenshot with:
    node scripts/web/shoot.mjs <out>/<slug> docs/.../screenshots "/:<slug>-v2"
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from packages.web.palette import Palette, palette_for_genre  # noqa: E402
from packages.web.scaffold import local_business_context, render_landing_html, unfilled_tokens  # noqa: E402
from packages.web.validation import validate_web_dist  # noqa: E402

PORTFOLIO = ROOT / "products/better-business-web/portfolio"


# --- font vibes (from design_reference/font_pairings.md; weights verified) ----

@dataclass(frozen=True)
class Vibe:
    heading: str
    body: str
    fimport: str
    upper: bool


VIBES: dict[str, Vibe] = {
    "industrial": Vibe('"Oswald", system-ui, sans-serif', '"Inter", system-ui, sans-serif',
        "Oswald:wght@500;600;700&family=Inter:wght@400;500;600", True),
    "vintage": Vibe('"Oswald", system-ui, sans-serif', '"Inter", system-ui, sans-serif',
        "Oswald:wght@600;700&family=Inter:wght@400;500", True),
    "trades": Vibe('"Archivo", system-ui, sans-serif', '"Inter", system-ui, sans-serif',
        "Archivo:wght@600;700;800&family=Inter:wght@400;500;600", True),
    "warm": Vibe('"Fraunces", Georgia, serif', '"Nunito", system-ui, sans-serif',
        "Fraunces:wght@400;500;600;700&family=Nunito:wght@400;600;700", False),
    "warm_alt": Vibe('"Lora", Georgia, serif', '"Inter", system-ui, sans-serif',
        "Lora:wght@500;600;700&family=Inter:wght@400;500", False),
    "playful": Vibe('"Fredoka", system-ui, sans-serif', '"Nunito", system-ui, sans-serif',
        "Fredoka:wght@500;600;700&family=Nunito:wght@400;600;700", False),
    "elegant": Vibe('"Playfair Display", Georgia, serif', '"Inter", system-ui, sans-serif',
        "Playfair+Display:wght@500;600;700&family=Inter:wght@400;500", False),
}

# gun_store isn't one of the 20 canonical genres — give it a tactical palette here
# (charcoal / steel / burnt-orange CTA) rather than expanding the canonical table.
PALETTE_OVERRIDES: dict[str, Palette] = {
    "gun_store": Palette("#1F2937", "#FFFFFF", "#374151", "#C2410C", "#FFFFFF",
                         "#F8FAFC", "#111827", "#E5E7EB"),
}


@dataclass
class Demo:
    genre: str
    slug: str
    business: str
    area: str
    phone: str
    service_category: str
    vibe: str
    photo: str  # relative to PORTFOLIO/<genre>/dist/assets/
    eyebrow: str
    headline: str
    sub: str
    hero_note: str
    feat_headline: str
    feat_sub: str
    features: list[tuple[str, str]]  # 3 x (title, body)
    stats: list[tuple[str, str]]     # 4 x (number, label)
    testimonial: str
    cta_headline: str
    cta_sub: str
    trust: tuple[str, str, str, str]

    @property
    def tel(self) -> str:
        return "+1" + re.sub(r"\D", "", self.phone)

    def palette(self) -> Palette:
        return PALETTE_OVERRIDES.get(self.genre) or palette_for_genre(self.genre)

    def photo_path(self) -> Path:
        return PORTFOLIO / self.genre / "dist" / "assets" / self.photo


# Shared local-business "how it works" — same shape for every genre.
HOW = {
    "HOW_HEADLINE": "How it works",
    "STEP_1_TITLE": "Reach out", "STEP_1_BODY": "Call or stop by — quick and easy, no runaround.",
    "STEP_2_TITLE": "We take care of it", "STEP_2_BODY": "Skilled work, done right the first time.",
    "STEP_3_TITLE": "You're set", "STEP_3_BODY": "Fair price, no surprises — and we stand behind it.",
}


def make_context(d: Demo) -> dict[str, str]:
    ctx = local_business_context(
        d.business,
        service_category=d.service_category,
        city=d.area,
        services=[t for t, _ in d.features],
        phone=d.phone,
    )
    ctx.update(HOW)
    ctx.update({
        "EYEBROW": d.eyebrow,
        "HERO_HEADLINE": d.headline,
        "HERO_SUBHEAD": d.sub,
        "HERO_NOTE": d.hero_note,
        "PRIMARY_CTA": f"Call {d.phone}",
        "SECONDARY_CTA": "See our services",
        "TRUST_LABEL": f"Proudly serving {d.area}",
        "TRUST_1": d.trust[0], "TRUST_2": d.trust[1], "TRUST_3": d.trust[2], "TRUST_4": d.trust[3],
        "FEATURES_HEADLINE": d.feat_headline,
        "FEATURES_SUBHEAD": d.feat_sub,
        "FEATURE_1_TITLE": d.features[0][0], "FEATURE_1_BODY": d.features[0][1],
        "FEATURE_2_TITLE": d.features[1][0], "FEATURE_2_BODY": d.features[1][1],
        "FEATURE_3_TITLE": d.features[2][0], "FEATURE_3_BODY": d.features[2][1],
        "TESTIMONIAL": d.testimonial,
        "TESTIMONIAL_AUTHOR": "— Google review · 5 stars",
        "CTA_HEADLINE": d.cta_headline,
        "CTA_SUBHEAD": d.cta_sub,
        "FAQ_3_Q": "How do I book?",
        "FAQ_3_A": "Call us or stop by — we'll take care of the rest.",
        "FOOTER_NOTE": f"{d.area} · {d.phone}",
    })
    return ctx


def theme_block(pal: Palette, vibe: Vibe) -> str:
    upper = "h1, h2 { text-transform: uppercase; letter-spacing: 0.005em; }" if vibe.upper else ""
    return f"""<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={vibe.fimport}&display=swap">
<style>
:root {{
  --brand: {pal.primary}; --brand-strong: {pal.primary}; --brand-contrast: {pal.on_primary};
  --secondary: {pal.secondary}; --accent: {pal.accent}; --on-accent: {pal.on_accent};
  --bg: {pal.bg}; --surface: #ffffff; --bg-subtle: #eef2f7; --border: {pal.border};
  --text: {pal.fg}; --text-muted: #475569;
  --font-heading: {vibe.heading}; --font-body: {vibe.body};
}}
body {{ font-family: var(--font-body); }}
h1, h2, h3, .eyebrow {{ font-family: var(--font-heading); }}
{upper}
.eyebrow {{ color: var(--accent); }}
.btn-primary {{ background: var(--accent); color: var(--on-accent); }}
.btn-primary:hover {{ filter: brightness(0.92); }}
.icon {{ background: color-mix(in srgb, var(--brand) 8%, transparent); }}
/* Stats bar — always a dark surface (var(--text)) so labels stay legible across
   light-brand genres (e.g. the pink nail palette). */
.stats-bar {{ background: var(--text); }}
.stats-bar .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-md); text-align: center; }}
.stat-num {{ display: block; font-family: var(--font-heading); font-weight: 700; font-size: var(--step-3); line-height: 1; color: #fff; }}
.stat-label {{ display: block; margin-top: 0.4em; font-size: var(--step--1); letter-spacing: 0.06em; text-transform: uppercase; color: #cbd5e1; }}
@media (max-width: 640px) {{ .stats-bar .stats {{ grid-template-columns: repeat(2, 1fr); }} }}
.section:has(> .container > .trust) {{ display: none; }}
.cta-card {{ background: linear-gradient(135deg, var(--brand) 0%, var(--text) 100%); }}
.cta-card .btn-ghost {{ background: var(--accent); color: var(--on-accent); border-color: var(--accent); }}
.cta-card .btn-ghost:hover {{ filter: brightness(0.92); }}
</style>"""


def photo_hero_block() -> str:
    return """<style>
.hero {
  position: relative;
  background:
    linear-gradient(180deg,
      color-mix(in srgb, var(--brand) 42%, rgba(0,0,0,0.74)) 0%,
      color-mix(in srgb, var(--brand) 26%, rgba(0,0,0,0.9)) 100%),
    url('assets/hero.jpg');
  background-size: cover;
  background-position: center 38%;
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


def _stats_section(stats: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<div class="stat"><span class="stat-num">{num}</span>'
        f'<span class="stat-label">{label}</span></div>'
        for num, label in stats
    )
    return ('<section class="section stats-bar" style="padding-block:var(--space-md)">'
            f'<div class="container stats">{cells}</div></section>')


def enrich_html(html: str, d: Demo) -> str:
    i = html.find('class="hero"')
    close = html.find("</section>", i)
    if close != -1:
        close += len("</section>")
        html = html[:close] + "\n" + _stats_section(d.stats) + html[close:]
    maps = "https://maps.google.com/?q=" + re.sub(r"\s+", "+", f"{d.business} {d.area}")
    call = (
        '<div class="cta-form" style="display:flex;gap:var(--space-sm);'
        'justify-content:center;flex-wrap:wrap">'
        f'<a class="btn btn-ghost btn-lg" href="{d.tel and "tel:" + d.tel}">Call {d.phone}</a>'
        f'<a class="btn btn-ghost btn-lg" href="{maps}" '
        'style="background:transparent;border-color:rgba(255,255,255,0.45);color:#fff">'
        "Get directions</a></div>"
    )
    return re.sub(r'<form class="cta-form".*?</form>', call, html, count=1, flags=re.DOTALL)


def build(d: Demo, out: Path) -> bool:
    pal = d.palette()
    if pal is None:
        raise SystemExit(f"no palette for genre {d.genre!r}")
    vibe = VIBES[d.vibe]

    html = render_landing_html(make_context(d))
    leftover = unfilled_tokens(html)
    if leftover:
        raise SystemExit(f"{d.slug}: unfilled tokens {leftover}")
    html = enrich_html(html, d)
    head = theme_block(pal, vibe) + "\n  " + photo_hero_block()
    html = html.replace("</head>", f"  {head}\n</head>", 1)

    site = out / d.slug
    (site / "assets").mkdir(parents=True, exist_ok=True)
    (site / "index.html").write_text(html, encoding="utf-8")
    shutil.copyfile(d.photo_path(), site / "assets" / "hero.jpg")

    report = validate_web_dist(site)
    ok = report.passed
    flags = [c.name for c in report.checks if not c.passed]
    print(f"  {'PASS' if ok else 'FAIL'} {d.slug:14s} brand={pal.primary} accent={pal.accent}"
          + (f"  ! {flags}" if flags else ""))
    return ok


# --------------------------------------------------------------------------
# The eight portfolio demos (business data from curated.json; copy is concept
# copy for a shop of this type — same posture as the existing demos).
# --------------------------------------------------------------------------

DEMOS: dict[str, Demo] = {
    "auto_repair": Demo(
        "auto_repair", "auto-repair", "Ironside Auto Works", "Maplewood", "(503) 555-0142",
        "auto repair", "industrial", "tech-working.jpg",
        "Auto Repair · Maplewood",
        "Tires, brakes & alignment — done right, priced fair.",
        "Honest auto repair on Maplewood's Birch Ave. We put it on the lift, show you the "
        "problem, and give you a straight answer — never an upsell.",
        "4.5★ · 500+ Google reviews · Hunter alignment on-site",
        "What we fix", "Six bays, a mechanic-owner on site, and no run-around.",
        [("Tires", "New and used, flat repair, patches, and full replacements. We show you the "
          "damage so you decide — patch or replace."),
         ("Wheel Alignment", "Computerized Hunter alignment on-site to protect your tires and "
          "keep your steering straight."),
         ("Brakes", "Inspection, pad replacement, and rotor service. Don't wait for the grind — "
          "we'll check them and give you a straight answer.")],
        [("4.5★", "Google rating"), ("500+", "Reviews"), ("7", "Days a week"), ("Hunter", "Alignment")],
        "Showed me the worn pad, quoted me fair, and had me out in an hour. Found my new shop.",
        "Need tires or a brake check in Maplewood?",
        "Call (503) 555-0142 or stop by 1200 Birch Ave. Fast, honest, fair.",
        ("ASE Certified", "Hunter Alignment", "NAPA Parts", "12-Mo Warranty")),

    "plumber": Demo(
        "plumber", "plumbing", "TrueLine Plumbing", "Westbrook", "(207) 555-0151",
        "plumbing", "trades", "work-kitchen-faucet.jpg",
        "Plumbing · Westbrook",
        "Leaks, water heaters & drains — fixed fast, priced right.",
        "Licensed plumbing for Westbrook homes and businesses. Upfront quotes, clean work, and "
        "we treat your home like our own.",
        "Licensed & insured · Same-day service · 24/7 emergencies",
        "What we do", "Local, dependable plumbing you can count on.",
        [("Repairs & Leaks", "Dripping faucets, running toilets, and burst pipes — found fast and "
          "fixed for good."),
         ("Water Heaters", "Repair, replacement, and tankless installs. Hot water back the same day."),
         ("Drain Cleaning", "Slow or clogged drains cleared — no mess, no upsell, just a working drain.")],
        [("4.9★", "Google rating"), ("Licensed", "& Insured"), ("24/7", "Emergency"), ("Upfront", "Pricing")],
        "Came out same day, fixed the leak, and the price was exactly what he quoted. My go-to plumber now.",
        "Got a leak in Westbrook?",
        "Call (207) 555-0151 or request a free quote. Fast, clean, fair.",
        ("Licensed & Insured", "Same-Day Service", "Upfront Quotes", "Local & Trusted")),

    "barber_shop": Demo(
        "barber_shop", "barbering", "Kingsway Barber Co.", "Downtown Brighton", "(617) 555-0188",
        "barbering", "vintage", "work.jpg",
        "Barbershop · Downtown Brighton",
        "Sharp cuts, classic fades, clean lines.",
        "A proper barbershop in Downtown Brighton. Skilled barbers, hot-towel finishes, and no "
        "rush — just a great cut.",
        "Walk-ins welcome · Online booking · 7 days a week",
        "The chair", "Classic barbering, done right.",
        [("Haircuts", "Classic and modern cuts tailored to you — consultation included, every time."),
         ("Fades", "Skin, taper, and drop fades dialed in clean by barbers who do them all day."),
         ("Beard Trims", "Line-ups, shaping, and hot-towel straight-razor finishes.")],
        [("4.8★", "Google rating"), ("7", "Days a week"), ("Walk-ins", "Welcome"), ("Hot-Towel", "Finish")],
        "Best fade in Brighton, hands down. Friendly chair, no rush, and it's always on point.",
        "Need a fresh cut in Brighton?",
        "Book online or walk in at 88 Harbor St. Call (617) 555-0188.",
        ("Master Barbers", "Walk-ins Welcome", "Online Booking", "Hot-Towel Finish")),

    "bakery": Demo(
        "bakery", "baked-goods", "Goldenrod Bakehouse", "Sutton village", "(802) 555-0119",
        "baked goods", "warm", "pastry-case.jpg",
        "Bakery · Sutton Village",
        "Fresh bread, real butter, baked every morning.",
        "A small-batch bakehouse in Sutton village. Sourdough, pastries, and custom cakes — "
        "made by hand and sold the same day.",
        "Open Tue–Sun · Order cakes ahead · Locally milled flour",
        "From the oven", "Hand-made, same-day, never frozen.",
        [("Fresh Bread", "Sourdough, baguettes, and seeded loaves baked daily and sold while warm."),
         ("Custom Cakes", "Birthdays, weddings, and whatever you're celebrating — designed with you."),
         ("Pastries", "Croissants, scones, and morning buns — the reason regulars line up early.")],
        [("4.9★", "Google rating"), ("Daily", "Fresh-baked"), ("Local", "Milled flour"), ("Order", "Cakes ahead")],
        "The sourdough is unreal and the cakes are showstoppers. Worth the drive to Sutton every weekend.",
        "Hungry, or planning a celebration?",
        "Stop by 5 Mill Lane or order a cake ahead. Call (802) 555-0119.",
        ("Baked Daily", "Custom Cakes", "Locally Milled", "Small Batch")),

    "coffee_shop": Demo(
        "coffee_shop", "coffee", "Northside Coffee Co.", "Riverside", "(509) 555-0120",
        "coffee", "warm_alt", "interior-wide.jpg",
        "Coffee · Riverside",
        "Good coffee, slow mornings, your new regular.",
        "A neighborhood café on Main St. Carefully pulled espresso, fresh pastries, and a room "
        "you'll want to linger in.",
        "Open daily from 6am · Free wifi · Locally roasted",
        "The menu", "Small menu, done really well.",
        [("Espresso Drinks", "Lattes, cortados, and a proper flat white — pulled by baristas who care."),
         ("Cold Brew", "Slow-steeped 18 hours for a smooth, low-acid cup that actually tastes like coffee."),
         ("Fresh Pastries", "Croissants and bakes delivered each morning — the perfect side to your cup.")],
        [("4.8★", "Google rating"), ("6am", "Open daily"), ("Local", "Roast"), ("Free", "Wifi")],
        "My favorite spot in Riverside. The cortado is perfect and the staff remember your order.",
        "Coffee's on. Come say hi.",
        "Find us at 412 Main St, Riverside. Open daily from 6am.",
        ("Locally Roasted", "Open Daily", "Free Wifi", "Fresh Pastries")),

    "nail_salon": Demo(
        "nail_salon", "nails", "Lumière Nail Lounge", "Park Hill", "(720) 555-0166",
        "nail care", "elegant", "work-chrome.jpg",
        "Nail Lounge · Park Hill",
        "Polished, pampered, and out the door glowing.",
        "A calm, spotless nail lounge in Park Hill. Meticulous manicures, relaxing pedicures, "
        "and nail art that turns heads.",
        "By appointment or walk-in · Sanitized tools · Gel & dip",
        "The menu", "Meticulous work in a calm, clean space.",
        [("Manicures", "Classic, gel, and dip — shaped, buffed, and finished to last."),
         ("Pedicures", "A spotless, relaxing soak-and-scrub that leaves your feet sandal-ready."),
         ("Gel & Nail Art", "Chrome, ombré, French, and custom art by techs who love the detail.")],
        [("4.9★", "Google rating"), ("Sanitized", "Tools"), ("Walk-ins", "Welcome"), ("Custom", "Nail art")],
        "Spotless, relaxing, and my gel lasted three weeks. Just moved to the neighborhood and found my go-to.",
        "Treat yourself in Park Hill.",
        "Book an appointment or walk in at 1330 Aspen Way. Call (720) 555-0166.",
        ("Sanitized Tools", "Gel & Dip", "Custom Art", "By Appt or Walk-in")),

    "dog_groomer": Demo(
        "dog_groomer", "dog-grooming", "Wagtail Grooming Studio", "Cedar Falls", "(319) 555-0173",
        "dog grooming", "playful", "grooming-table.jpg",
        "Dog Grooming · Cedar Falls",
        "Happy dogs, fresh cuts, waggable tails.",
        "A gentle, low-stress grooming studio in Cedar Falls. Full grooms, baths, and tidy-ups "
        "by people who genuinely love dogs.",
        "By appointment · Gentle handling · All breeds & sizes",
        "The spa day", "Low-stress grooming, tail-wag guaranteed.",
        [("Full Grooms", "Breed-specific cuts, bath, blow-dry, nails, and ears — the whole spa day."),
         ("Baths & De-shed", "Deep-clean baths and de-shedding that keep your home (and pup) fresher."),
         ("Nail Trims", "Quick, calm nail trims and tidy-ups — walk-ins welcome between appointments.")],
        [("4.9★", "Google rating"), ("Gentle", "Handling"), ("All", "Breeds"), ("By", "Appointment")],
        "My anxious rescue actually loves it here. He comes home soft, happy, and smelling amazing.",
        "Ready for a fresh, happy pup?",
        "Book a grooming at 210 Cedar Rd, Cedar Falls. Call (319) 555-0173.",
        ("Gentle Handling", "All Breeds", "Low-Stress", "By Appointment")),

    "gun_store": Demo(
        "gun_store", "gun-store", "Blue Ridge Gun & Ammo", "Dahlonega", "(706) 555-0173",
        "firearms & ammo", "industrial", "gunsmith-bench.jpg",
        "Firearms & Ammo · Dahlonega",
        "Firearms, ammo & expert service — done right.",
        "A well-stocked shop in Dahlonega. Handguns, rifles, ammo, optics, and on-site "
        "gunsmithing — plus straight answers, whatever your experience.",
        "FFL transfers · On-site gunsmith · New & consignment",
        "The counter", "Well-stocked, no pressure, expert help.",
        [("Firearms", "Handguns, rifles, and shotguns — new and consignment, with no-pressure guidance."),
         ("Ammo & Optics", "Stocked ammunition, scopes, and accessories — sighting-in help included."),
         ("Transfers & Gunsmithing", "Fast, by-the-book FFL transfers and on-site repair, cleaning, and custom work.")],
        [("4.8★", "Google rating"), ("FFL", "Transfers"), ("On-site", "Gunsmith"), ("New &", "Consignment")],
        "Knowledgeable, patient, and never pushy. Walked me through my first purchase and earned a customer for life.",
        "Stop by the shop in Dahlonega.",
        "Visit 388 Morrison Moore Pkwy E. Call (706) 555-0173.",
        ("FFL Dealer", "On-site Gunsmith", "New & Used", "Straight Answers")),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--genre", default="all", help="a genre key, or 'all'")
    ap.add_argument("--out", default=str(ROOT / "build" / "themed-demos"))
    args = ap.parse_args()

    out = Path(args.out)
    demos = list(DEMOS.values()) if args.genre == "all" else [DEMOS[args.genre]]
    results = [build(d, out) for d in demos]
    print(f"\n{sum(results)}/{len(results)} demos pass the web gate")


if __name__ == "__main__":
    main()
