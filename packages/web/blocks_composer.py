"""Block composer — Phase 3 of the design engine.

Selects and orders art-directed blocks per archetype and assembles the premium
stack's `index.astro` from them. The blocks themselves
(`scaffold/astro-premium/src/blocks/*.astro`) are the craft artifacts; this module
is the deterministic, testable brain that decides *which* blocks, *in what order*,
filled with *what content* — so a build escapes the hero→features→CTA template by
construction.

Each block component takes a single `data` prop (a JSON object), so composition is
just choosing components and serializing their content. Real copy is supplied via
``content``; absent that, a serviceable placeholder is derived from the packet and
clearly meant to be replaced before ship.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from packages.web.design_studio import DesignStudioPacket

# Component name -> import path (relative to src/pages/index.astro).
_IMPORTS = {
    "CinematicHero": "../blocks/CinematicHero.astro",
    "EditorialSplit": "../blocks/EditorialSplit.astro",
    "BentoGallery": "../blocks/BentoGallery.astro",
    "StickyProcess": "../blocks/StickyProcess.astro",
    "FullBleedMedia": "../blocks/FullBleedMedia.astro",
    "ClosingCta": "../blocks/ClosingCta.astro",
}

# Archetype -> ordered block plan (the baseline). Every plan opens on a hero and
# closes on a CTA; the middle varies so no two archetypes read like the same stack.
_PLANS: dict[str, list[str]] = {
    "service-area-cinematic": [
        "CinematicHero", "EditorialSplit", "StickyProcess", "BentoGallery", "ClosingCta",
    ],
    "product-led": ["CinematicHero", "EditorialSplit", "StickyProcess", "ClosingCta"],
    "gallery-led": ["CinematicHero", "BentoGallery", "EditorialSplit", "ClosingCta"],
    "editorial-visit": ["CinematicHero", "EditorialSplit", "BentoGallery", "ClosingCta"],
    "classic-custom": ["CinematicHero", "EditorialSplit", "ClosingCta"],
}

# Per-archetype STRUCTURAL VARIANTS. The composer picks one by a stable hash of the
# concept (not the seed hue), so two same-archetype builds with different concepts
# get a different skeleton — the v3 fix for "template-sameness" (the audit found the
# v2 composer emitted the same section order every time). Each variant still opens on
# a hero and closes on a CTA; the difference is the middle + where the full-bleed
# media moment lands.
_VARIANTS: dict[str, list[list[str]]] = {
    "service-area-cinematic": [
        ["CinematicHero", "EditorialSplit", "StickyProcess", "BentoGallery", "ClosingCta"],
        ["CinematicHero", "FullBleedMedia", "EditorialSplit", "BentoGallery",
         "StickyProcess", "ClosingCta"],
        ["CinematicHero", "BentoGallery", "FullBleedMedia", "EditorialSplit", "ClosingCta"],
    ],
    "product-led": [
        ["CinematicHero", "EditorialSplit", "StickyProcess", "ClosingCta"],
        ["CinematicHero", "FullBleedMedia", "EditorialSplit", "StickyProcess", "ClosingCta"],
    ],
    "gallery-led": [
        ["CinematicHero", "BentoGallery", "EditorialSplit", "ClosingCta"],
        ["CinematicHero", "FullBleedMedia", "BentoGallery", "EditorialSplit", "ClosingCta"],
        ["CinematicHero", "EditorialSplit", "BentoGallery", "FullBleedMedia", "ClosingCta"],
    ],
    "editorial-visit": [
        ["CinematicHero", "EditorialSplit", "BentoGallery", "ClosingCta"],
        ["CinematicHero", "FullBleedMedia", "EditorialSplit", "BentoGallery", "ClosingCta"],
    ],
    "classic-custom": [
        ["CinematicHero", "EditorialSplit", "ClosingCta"],
        ["CinematicHero", "FullBleedMedia", "EditorialSplit", "ClosingCta"],
    ],
}

# Google Fonts for the premium type pairings (split to keep lines short).
_FONTS_LINK = (
    "https://fonts.googleapis.com/css2?"
    "family=Fraunces:opsz,wght@9..144,400..600"
    "&family=Cormorant+Garamond:wght@500;600"
    "&family=Inter:wght@400;500;600&family=Inter+Tight:wght@500;600"
    "&family=Newsreader:opsz@6..72&family=Spline+Sans+Mono:wght@400;500&display=swap"
)


@dataclass(frozen=True)
class BlockSpec:
    """One placed block: a component name and its content payload."""

    component: str
    data: dict


@dataclass(frozen=True)
class Composition:
    """An ordered, content-filled block plan for one premium build."""

    site_name: str
    archetype: str
    blocks: list[BlockSpec] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "site_name": self.site_name,
            "archetype": self.archetype,
            "blocks": [{"component": b.component, "data": b.data} for b in self.blocks],
        }


def plan_composition(
    packet: DesignStudioPacket,
    content: dict | None = None,
    *,
    images: dict | None = None,
    variant: int | None = None,
) -> Composition:
    """Choose + order + fill blocks for this packet's archetype.

    The block order is one of the archetype's structural variants, selected by a
    stable hash of the concept (override with ``variant``) so two same-archetype
    builds differ. ``images`` ({"hero": src, "supporting": [src, ...]}) places real
    imagery into the hero / gallery / full-bleed slots.
    """

    archetype = packet.archetype if packet.archetype in _PLANS else "classic-custom"
    variants = _VARIANTS.get(archetype, [_PLANS[archetype]])
    idx = variant if variant is not None else _variant_index(packet, len(variants))
    plan = variants[idx % len(variants)]
    content = content or derive_content(packet, images=images)
    blocks = [
        BlockSpec(component=name, data=content.get(_slot(name), {})) for name in plan
    ]
    return Composition(site_name=packet.site_name, archetype=archetype, blocks=blocks)


def _variant_index(packet: DesignStudioPacket, n: int) -> int:
    """A deterministic variant choice from the concept (not the seed hue)."""

    if n <= 1:
        return 0
    digest = hashlib.md5(packet.concept_statement.encode("utf-8")).hexdigest()
    return int(digest, 16) % n


def _slot(component: str) -> str:
    return {
        "CinematicHero": "hero",
        "EditorialSplit": "split",
        "BentoGallery": "bento",
        "StickyProcess": "process",
        "FullBleedMedia": "fullbleed",
        "ClosingCta": "cta",
    }[component]


def derive_content(packet: DesignStudioPacket, images: dict | None = None) -> dict:
    """Serviceable placeholder content from the packet — replace with real copy.

    ``images`` ({"hero": src, "supporting": [src, ...]}) supplies real, art-directed
    imagery; absent it, blocks fall back to the WebGL hero / text cards.
    """

    name = packet.site_name
    concept = packet.concept_statement.split(";")[0].strip().rstrip(".")
    headline = concept[:1].upper() + concept[1:] if concept else f"{name}"
    proof = [e for e in packet.evidence if e.strip()][:6]
    images = images or {}
    hero_img = images.get("hero")
    supporting = list(images.get("supporting", []))

    def support(i: int) -> str | None:
        return supporting[i % len(supporting)] if supporting else None

    return {
        "hero": {
            "eyebrow": packet.business_category.title(),
            "headline": headline,
            "subhead": f"{name} for {packet.audience} — {packet.goal}.",
            "primaryCta": "Get in touch",
            "secondaryCta": "See the work",
            "image": hero_img,
            "imageAlt": f"{name} — {concept}" if concept else name,
        },
        "split": {
            "index": "01",
            "heading": "Built around what actually matters here",
            "body": packet.goal.capitalize() + ".",
            "points": proof or ["Add proof points from real business evidence."],
        },
        "bento": {
            "heading": "The work, up close",
            "items": [
                {
                    "title": f"Detail {i + 1}",
                    "body": p,
                    "span": "wide" if i == 0 else ("tall" if i == 1 else None),
                    "image": support(i),
                }
                for i, p in enumerate(proof or ["Replace with real proof of work."])
            ],
        },
        "process": {
            "heading": "How it goes",
            "steps": [
                {"title": "Reach out", "body": "Tell us what you need."},
                {"title": "We scope it", "body": "A clear plan and a clear price."},
                {"title": "It gets done", "body": "Careful work, done right."},
            ],
        },
        "fullbleed": {
            "image": hero_img or support(0),
            "alt": f"{name} — {concept}" if concept else name,
            "kicker": packet.business_category.title(),
            "headline": headline,
            "cta": "Get in touch",
        },
        "cta": {
            "headline": "Ready when you are",
            "subhead": f"Get in touch with {name} today.",
            "cta": "Get in touch",
        },
    }


def render_index_astro(
    composition: Composition,
    *,
    tagline: str = "",
    meta_description: str = "",
    year: str = "2026",
) -> str:
    """Generate the premium `index.astro` that composes the chosen blocks."""

    used = [b.component for b in composition.blocks]
    seen: set[str] = set()
    imports = []
    for comp in used:
        if comp not in seen:
            imports.append(f'import {comp} from "{_IMPORTS[comp]}";')
            seen.add(comp)

    body_blocks = "\n    ".join(
        f"<{b.component} data={{{json.dumps(b.data)}}} />" for b in composition.blocks
    )
    name = composition.site_name
    return f"""---
// Generated by packages/web/blocks_composer.py — an archetype-driven composition
// of art-directed blocks. Edit content via the composer, not by hand.
import "../styles/global.css";
{chr(10).join(imports)}
---
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{name} — {tagline}</title>
  <meta name="description" content="{meta_description}" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="{_FONTS_LINK}" />
</head>
<body class="grain">
  <a class="btn btn-ghost" href="#main"
     style="position:absolute;left:-9999px;top:auto"
     onfocus="this.style.left='1rem';this.style.top='1rem';this.style.position='fixed'"
     >Skip to content</a>
  <header class="section" style="padding-block:1.5rem">
    <div class="container"
         style="display:flex;align-items:center;justify-content:space-between">
      <a href="/"
         style="font-family:var(--display-font);font-weight:600;text-decoration:none"
         >{name}</a>
      <a class="btn btn-primary" href="#get-started">Get in touch</a>
    </div>
  </header>
  <main id="main">
    {body_blocks}
  </main>
  <footer class="section" style="padding-block:2rem;border-top:1px solid var(--border)">
    <div class="container muted" style="font-size:var(--step-n1)">© {year} {name}.</div>
  </footer>
  <script>
    import "../scripts/motion.ts";
  </script>
</body>
</html>
"""
