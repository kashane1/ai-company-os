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
    concept = packet.concept_statement.split(";")[0].strip().rstrip(".")
    headline = (concept[:1].upper() + concept[1:]) if concept else name
    proof = _proof_points(packet)
    cta = primary_cta(packet)

    # A subhead that states who it's for + the goal, grounded by the first proof
    # signal when there is one (no superlatives, no fabricated numbers).
    lead_proof = proof[0]
    subhead = f"{name} for {packet.audience} — {packet.goal.rstrip('.')}."
    if not lead_proof.lower().startswith("add proof"):
        subhead = f"{subhead} {lead_proof[:1].upper() + lead_proof[1:].rstrip('.')}."

    return {
        "headline": headline,
        "subhead": subhead,
        "primary_cta": cta,
        "secondary_cta": "See the work",
        "proof_points": proof,
        "split_heading": f"Why {packet.audience.split(',')[0].strip()} choose {name}",
        "cta_headline": f"Ready when you are — {cta.lower()}",
        "cta_subhead": f"{name} for {packet.audience}. {cta} today.",
    }
