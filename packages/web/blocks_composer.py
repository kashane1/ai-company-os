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

import json
from dataclasses import dataclass, field

from packages.web.design_studio import DesignStudioPacket

# Component name -> import path (relative to src/pages/index.astro).
_IMPORTS = {
    "CinematicHero": "../blocks/CinematicHero.astro",
    "EditorialSplit": "../blocks/EditorialSplit.astro",
    "BentoGallery": "../blocks/BentoGallery.astro",
    "StickyProcess": "../blocks/StickyProcess.astro",
    "ClosingCta": "../blocks/ClosingCta.astro",
}

# Archetype -> ordered block plan. Every plan opens on a hero and closes on a CTA;
# the middle varies so no two archetypes read like the same stacked template.
_PLANS: dict[str, list[str]] = {
    "service-area-cinematic": [
        "CinematicHero", "EditorialSplit", "StickyProcess", "BentoGallery", "ClosingCta",
    ],
    "product-led": ["CinematicHero", "EditorialSplit", "StickyProcess", "ClosingCta"],
    "gallery-led": ["CinematicHero", "BentoGallery", "EditorialSplit", "ClosingCta"],
    "editorial-visit": ["CinematicHero", "EditorialSplit", "BentoGallery", "ClosingCta"],
    "classic-custom": ["CinematicHero", "EditorialSplit", "ClosingCta"],
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


def plan_composition(packet: DesignStudioPacket, content: dict | None = None) -> Composition:
    """Choose + order + fill blocks for this packet's archetype."""

    archetype = packet.archetype if packet.archetype in _PLANS else "classic-custom"
    content = content or derive_content(packet)
    blocks = [
        BlockSpec(component=name, data=content.get(_slot(name), {}))
        for name in _PLANS[archetype]
    ]
    return Composition(site_name=packet.site_name, archetype=archetype, blocks=blocks)


def _slot(component: str) -> str:
    return {
        "CinematicHero": "hero",
        "EditorialSplit": "split",
        "BentoGallery": "bento",
        "StickyProcess": "process",
        "ClosingCta": "cta",
    }[component]


def derive_content(packet: DesignStudioPacket) -> dict:
    """Serviceable placeholder content from the packet — replace with real copy."""

    name = packet.site_name
    concept = packet.concept_statement.split(";")[0].strip().rstrip(".")
    headline = concept[:1].upper() + concept[1:] if concept else f"{name}"
    proof = [e for e in packet.evidence if e.strip()][:6]
    return {
        "hero": {
            "eyebrow": packet.business_category.title(),
            "headline": headline,
            "subhead": f"{name} for {packet.audience} — {packet.goal}.",
            "primaryCta": "Get in touch",
            "secondaryCta": "See the work",
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
                {"title": f"Detail {i + 1}", "body": p, "span": "wide" if i == 0 else None}
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
