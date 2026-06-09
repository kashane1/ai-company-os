"""Deterministic composition / geometry gate (no model, no Gemini).

The vision judge scores rendered *screenshots* on taste — it has no model of element
geometry, so it tolerates real composition defects: two full-bleed photo sections
stacked back-to-back, sections that vertically overlap, text sitting on top of a
*different* section's image, or a page that scrolls sideways. Those are deterministic
and cheap to detect from a DOM geometry snapshot — they should never depend on a
stochastic vision pass (which also can't run when the imagery/judge API is down).

`shoot.mjs --geometry <path>` captures the snapshot (absolute element rects at a
settled, reduced-motion layout). This module classifies it into defects in the SAME
shape as the adversarial defect inspector (`{severity, type, where, detail}`), so they
merge straight into the existing `defects.json` + score-capping flow.
"""

from __future__ import annotations

# Sub-pixel rounding slack; below this an "overlap" is just rounding noise.
OVERLAP_TOL = 4


def _intersects(a: dict, b: dict) -> bool:
    """True if two absolute rects overlap by more than the rounding tolerance."""
    return not (
        a["right"] - b["left"] <= OVERLAP_TOL
        or b["right"] - a["left"] <= OVERLAP_TOL
        or a["bottom"] - b["top"] <= OVERLAP_TOL
        or b["bottom"] - a["top"] <= OVERLAP_TOL
    )


def composition_defects(geometry: dict) -> list[dict]:
    """Classify a DOM geometry snapshot into deterministic composition defects.

    Detects: (1) two consecutive full-bleed media sections (the hero is already
    full-bleed, so a full-bleed band right after it reads as a cluttered patchwork);
    (2) sections that vertically overlap; (3) text rendered over an image that belongs
    to a different section; (4) horizontal overflow (the page scrolls sideways).
    """
    sections = geometry.get("sections", [])
    defects: list[dict] = []

    # (1) consecutive full-bleed photo sections.
    for i in range(len(sections) - 1):
        if sections[i].get("fullBleed") and sections[i + 1].get("fullBleed"):
            defects.append(
                {
                    "severity": "high",
                    "type": "stacked_fullbleed",
                    "where": f"sections {i} & {i + 1}",
                    "detail": (
                        "two full-bleed photo sections are stacked back-to-back; "
                        "a contained section should separate them"
                    ),
                }
            )

    # (2) sections overlapping vertically (a real layout collision).
    for i in range(len(sections) - 1):
        a, b = sections[i], sections[i + 1]
        gap = b["top"] - a["bottom"]
        if gap < -OVERLAP_TOL:
            defects.append(
                {
                    "severity": "high",
                    "type": "section_overlap",
                    "where": f"sections {i} & {i + 1}",
                    "detail": (
                        f"section {i} (bottom {a['bottom']}) overlaps section {i + 1} "
                        f"(top {b['top']}) by {-gap}px"
                    ),
                }
            )

    # (3) text over a DIFFERENT section's image (e.g. a card's text bleeding onto the
    # neighbouring photo). Same-section text-over-image is intentional, so skip i == j.
    for i, sec in enumerate(sections):
        flagged = False
        for t in sec.get("texts", []):
            for j, other in enumerate(sections):
                if i == j:
                    continue
                if any(_intersects(t, im) for im in other.get("imgs", [])):
                    defects.append(
                        {
                            "severity": "high",
                            "type": "text_foreign_image_overlap",
                            "where": f"{t.get('tag', 'text')} in section {i} over image in section {j}",
                            "detail": (
                                "text overlaps an image that belongs to a different "
                                "section (cross-section collision)"
                            ),
                        }
                    )
                    flagged = True
                    break
            if flagged:
                break  # one report per section is enough to fail the gate

    # (4) horizontal overflow — the page scrolls sideways on some viewport.
    if geometry.get("hasHorizontalScroll"):
        defects.append(
            {
                "severity": "medium",
                "type": "horizontal_overflow",
                "where": "document",
                "detail": (
                    "the page scrolls horizontally — an element exceeds the viewport "
                    f"width (scrollWidth {geometry.get('scrollWidth')} > "
                    f"clientWidth {geometry.get('clientWidth')})"
                ),
            }
        )

    return defects


def high_severity(defects: list[dict]) -> list[dict]:
    """The subset that should hard-fail a build."""
    return [d for d in defects if d.get("severity") == "high"]
