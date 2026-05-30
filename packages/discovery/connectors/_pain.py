"""Shared helpers: spotting and classifying "payable pain" in free text.

Tune ``PAIN_MARKERS`` per domain. These are intentionally simple lexical
heuristics — a connector's job is to surface candidates with provenance, not to
judge them. The market analyst scores; this just filters obvious noise.
"""

from __future__ import annotations

from packages.schemas.opportunity import EvidenceKind

PAIN_MARKERS: tuple[str, ...] = (
    "is there a tool",
    "is there an app",
    "how do i automate",
    "i hate doing",
    "manually",
    "alternative to",
    "wish there was",
    "anyone know an app",
    "anyone know a tool",
    "tired of",
    "frustrated with",
    "no good tool",
    "still doing this by hand",
)


def looks_like_pain(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in PAIN_MARKERS)


def classify(text: str) -> EvidenceKind:
    lowered = text.lower()
    if "alternative to" in lowered:
        return EvidenceKind.COMPETITOR
    requests = ("is there a tool", "anyone know an app", "anyone know a tool")
    if any(marker in lowered for marker in requests):
        return EvidenceKind.REQUEST
    if "manually" in lowered or "automate" in lowered or "by hand" in lowered:
        return EvidenceKind.WORKAROUND
    if "hate" in lowered or "tired of" in lowered or "frustrated" in lowered:
        return EvidenceKind.COMPLAINT
    return EvidenceKind.OTHER
