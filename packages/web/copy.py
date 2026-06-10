"""Conversion copy — design engine v3, Phase 4.

The v2 composer shipped placeholder copy ("Detail 1", "Replace with real proof")
and treated real copy as "the build agent's job" — so the judge's
`conversion_strength` / `copy_specificity` dimensions had nothing real to score.
This module derives **grounded conversion copy** from the packet's business
evidence, deterministically, honoring the packet's copy constraints (no fabricated
claims — every line traces to evidence or to neutral, defensible framing).

It is the pure, testable core. A later agent build-leg can override any field with
sharper human/LLM copy; this guarantees the loop always has real copy to judge.
"""

from __future__ import annotations

from packages.web.design_studio import DesignStudioPacket

# goal-keyword -> a concrete primary call to action. The CTA names the next action
# in the business's own terms instead of a generic "Get in touch".
_CTA_BY_INTENT: list[tuple[tuple[str, ...], str]] = [
    (("book", "appointment", "appt", "schedule", "reservation", "reserve"), "Book your visit"),
    (("quote", "estimate", "consultation", "consult"), "Get a free quote"),
    (("call", "phone", "emergency", "same-day", "same day"), "Call now"),
    (("order", "buy", "shop", "purchase"), "Start your order"),
    (("tour", "visit", "stop by", "come in"), "Plan your visit"),
    (("apply", "membership", "join", "sign up", "signup", "enroll"), "Become a member"),
]


def primary_cta(packet: DesignStudioPacket) -> str:
    """The action verb that fits the business goal — not a generic 'Get in touch'."""

    hay = f"{packet.goal} {packet.business_category}".lower()
    for needles, cta in _CTA_BY_INTENT:
        if any(n in hay for n in needles):
            return cta
    return "Get in touch"


# Section labels by business genre — keeps agency/portfolio language ("the work",
# "see the work") off a restaurant or salon, where it reads as a template tell.
_GENRE_LABELS: list[tuple[tuple[str, ...], dict[str, str]]] = [
    (
        ("restaurant", "taco", "taqueria", "cafe", "café", "coffee", "bakery", "bar", "grill",
         "kitchen", "eatery", "bistro", "deli", "pizz", "diner", "food", "brunch"),
        {"gallery": "On the menu", "secondary_cta": "See the menu"},
    ),
    (
        ("salon", "spa", "nail", "barber", "beauty", "hair", "wellness", "massage", "aesthetic",
         "lash", "brow", "skin", "studio"),
        {"gallery": "Inside the space", "secondary_cta": "Take a look"},
    ),
]
_DEFAULT_LABELS = {"gallery": "The work, up close", "secondary_cta": "See the work"}


def section_labels(packet: DesignStudioPacket) -> dict[str, str]:
    """Genre-appropriate section labels (gallery heading + secondary CTA)."""

    hay = packet.business_category.lower()
    for needles, labels in _GENRE_LABELS:
        if any(n in hay for n in needles):
            return labels
    return _DEFAULT_LABELS


# Genre-appropriate StickyProcess steps (a consult/visit flow). Wellness/clinical get a
# calm consultation arc; trades/services get the default scope-and-do.
_PROCESS_BY_GENRE: list[tuple[tuple[str, ...], tuple[str, list[tuple[str, str]]]]] = [
    (
        ("spa", "wellness", "aesthetic", "massage", "skin", "clinic", "salon", "beauty",
         "yoga", "facial", "lash", "brow", "therapy"),
        ("What to expect", [
            ("Consultation", "A private, unhurried consult to understand your goals."),
            ("Your treatment", "Expert, comfortable care in a calm, considered space."),
            ("Results & aftercare", "Natural results, with clear guidance for what comes next."),
        ]),
    ),
]
_DEFAULT_PROCESS = ("How it goes", [
    ("Reach out", "Tell us what you need."),
    ("We scope it", "A clear plan and a clear price."),
    ("It gets done", "Careful work, done right."),
])


def process_steps(packet: DesignStudioPacket) -> tuple[str, list[tuple[str, str]]]:
    """Genre-appropriate (heading, [(title, body), …]) for the StickyProcess section."""

    hay = packet.business_category.lower()
    for needles, block in _PROCESS_BY_GENRE:
        if any(n in hay for n in needles):
            return block
    return _DEFAULT_PROCESS


def _proof_points(packet: DesignStudioPacket, limit: int = 4) -> list[str]:
    """Evidence lines, lightly framed — never fabricated. Falls back to a neutral,
    honest prompt to add real proof (so the loop fails copy honestly rather than
    inventing claims)."""

    points = [e.strip() for e in packet.evidence if e.strip()][:limit]
    return points or ["Add proof points from real business evidence."]


def generate_conversion_copy(packet: DesignStudioPacket) -> dict[str, object]:
    """Derive a grounded conversion-copy set for the composer.

    Returns the fields the blocks consume (headline, subhead, CTAs, proof framing),
    all sourced from the packet's concept + evidence + goal — defensible, specific,
    and free of invented stats/testimonials (the copy_constraints bar).
    """

    name = packet.site_name
    clauses = [c.strip().rstrip(".") for c in packet.concept_statement.split(";") if c.strip()]
    concept = clauses[0] if clauses else ""
    headline = (concept[:1].upper() + concept[1:]) if concept else name
    proof = _proof_points(packet)
    cta = primary_cta(packet)
    labels = section_labels(packet)

    # A DISTINCT mid-page band headline so the full-bleed media block never repeats the
    # hero. Prefer the concept's second clause (concepts are written "A; B"); else a
    # concrete proof point; else an invitation — always different from `headline`.
    if len(clauses) > 1:
        band = clauses[1]
    elif proof and not proof[0].lower().startswith("add proof"):
        band = proof[0]
    else:
        band = f"{cta.lower()} today"
    band_headline = band[:1].upper() + band[1:]
    if band_headline.strip().lower() == headline.strip().lower():
        band_headline = f"{cta} today"  # last-resort guard against any echo

    # A subhead that states who it's for, grounded by the first proof signal — never the
    # raw operator GOAL ("drive walk-in visits and online pickup orders"), which is
    # internal objective-speak, not customer-facing copy.
    lead_proof = proof[0]
    subhead = f"{name} for {packet.audience}."
    if not lead_proof.lower().startswith("add proof"):
        subhead = f"{subhead} {lead_proof[:1].upper() + lead_proof[1:].rstrip('.')}."

    # The split section's lead line — a grounded promise distinct from headline/band, and
    # again never the raw goal: an unused concept clause, else a proof, else a soft fallback.
    used = {headline.strip().lower(), band_headline.strip().lower()}
    extra = [c for c in clauses if c.strip().lower() not in used]
    if extra:
        split_body = extra[0]
    elif not lead_proof.lower().startswith("add proof"):
        split_body = lead_proof
    else:
        split_body = f"what keeps {packet.audience.split(',')[0].strip()} coming back"
    split_body = split_body[:1].upper() + split_body[1:].rstrip(".") + "."

    return {
        "headline": headline,
        "subhead": subhead,
        "primary_cta": cta,
        "secondary_cta": labels["secondary_cta"],
        "proof_points": proof,
        "split_heading": f"Why {packet.audience.split(',')[0].strip()} choose {name}",
        "split_body": split_body,
        "gallery_heading": labels["gallery"],
        "band_headline": band_headline,
        "cta_headline": f"Ready when you are — {cta.lower()}",
        "cta_subhead": f"{name} for {packet.audience}. {cta} today.",
        "cta_href": "#get-started",
    }
