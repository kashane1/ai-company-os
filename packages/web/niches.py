"""Premium niche → starter spec — design engine v3, Phase 5 (scale).

Turns a niche name ("med spa", "boutique fitness", ...) into a starter build spec
the design loop can run, so a flagship build is one command:

    python scripts/agency/design_loop.py run --target <dir> \
        --spec <(python -c "import json,sys;\
                 from packages.web.niches import niche_to_spec;\
                 print(json.dumps(niche_to_spec('med spa')))")

or via `make premium NICHE="med spa"`. The catalog covers the high-premium-upside
niches the v3 plan recommends; an unknown niche falls back to a sensible generic
spec keyed off the niche string. The evidence here is illustrative placeholder —
a real client build replaces it with the business's own proof (the copy layer
fails honestly on placeholder, per copy.py).
"""

from __future__ import annotations

# niche key (substring-matched, lowercased) -> starter spec fields.
_CATALOG: list[tuple[tuple[str, ...], dict[str, object]]] = [
    (
        ("med spa", "medspa", "aesthetic", "botox"),
        {
            "site_name": "Lumina Aesthetics",
            "business_category": "med spa",
            "audience": "professionals seeking subtle, expert aesthetic treatments",
            "goal": "book consultations for premium aesthetic treatments",
            "concept_statement": "clinical precision, spa calm; results you can trust",
            "evidence": [
                "board-certified injectors",
                "1,000+ treatments a year",
                "private, unhurried consultations",
            ],
            "imagery_mode": "concept-led",
        },
    ),
    (
        ("pilates", "boutique fitness", "yoga studio", "reformer"),
        {
            "site_name": "Meridian Pilates",
            "business_category": "boutique fitness",
            "audience": "members who want focused, expert-led training",
            "goal": "book a first class and convert to membership",
            "concept_statement": "strength as a daily ritual; precise, unhurried movement",
            "evidence": [
                "small-group reformer classes",
                "certified instructors",
                "studio capped at 8 per class",
            ],
            "imagery_mode": "concept-led",
        },
    ),
    (
        ("restaurant", "fine dining", "bistro", "tasting menu"),
        {
            "site_name": "Atelier Nord",
            "business_category": "high-end restaurant",
            "audience": "diners booking a special occasion",
            "goal": "drive reservations for the tasting menu",
            "concept_statement": "seasonal craft, quiet luxury; a room worth dressing for",
            "evidence": [
                "seasonal tasting menu",
                "chef trained in Copenhagen",
                "reservations open 30 days out",
            ],
            "imagery_mode": "concept-led",
        },
    ),
    (
        ("law", "attorney", "legal"),
        {
            "site_name": "Hale & Crowe",
            "business_category": "law firm",
            "audience": "clients facing a high-stakes legal matter",
            "goal": "book a confidential case consultation",
            "concept_statement": "calm authority under pressure; precision that protects you",
            "evidence": [
                "20 years of trial experience",
                "free initial consultation",
                "confidential, responsive counsel",
            ],
            "imagery_mode": "evidence-led",
        },
    ),
    (
        ("remodel", "renovation", "home builder", "landscap"),
        {
            "site_name": "Cedar & Stone",
            "business_category": "luxury home remodeling",
            "audience": "homeowners planning a high-end renovation",
            "goal": "book a design-build consultation",
            "concept_statement": "craft you can see; a calm, managed build, start to finish",
            "evidence": [
                "design-build under one roof",
                "fixed-price proposals",
                "portfolio of full-home remodels",
            ],
            "imagery_mode": "concept-led",
        },
    ),
]


def _base_spec(niche: str) -> dict[str, object]:
    """The catalog match or the generic fallback — business framing, no art direction."""

    key = niche.strip().lower()
    for needles, spec in _CATALOG:
        if any(n in key for n in needles):
            return dict(spec)
    title = niche.strip().title() or "Premium Studio"
    return {
        "site_name": title,
        "business_category": niche.strip() or "premium local service",
        "audience": f"clients seeking a premium {niche.strip() or 'local'} experience",
        "goal": f"book more {niche.strip() or 'premium'} work",
        "concept_statement": f"premium {niche.strip()} done with quiet craft and precision",
        "evidence": ["Add real proof from the business (reviews, credentials, work)."],
        "imagery_mode": "concept-led",
    }


def niche_to_spec(niche: str) -> dict[str, object]:
    """Return a starter build spec for ``niche``.

    A genre **art-direction kit** is the durable, image-backed successor to this
    function's hardcoded catalog: if a kit matches the niche, its recipe (palette,
    accent, imagery direction, references, evidence) is overlaid onto the base spec —
    the "instant high-quality first draft." With no kit, the catalog/generic spec is
    returned unchanged, so the legacy ``make premium`` path is unaffected.
    """

    spec = _base_spec(niche)
    # Lazy import: keep this module a leaf, and avoid pulling yaml/PIL into callers
    # that only want the catalog.
    from packages.web.art_direction import apply_kit_to_spec, find_kit_for_niche

    kit = find_kit_for_niche(niche)
    return apply_kit_to_spec(spec, kit) if kit else spec


def catalog_niches() -> list[str]:
    """The first keyword of each catalog entry (for help text / discovery)."""

    return [needles[0] for needles, _ in _CATALOG]
