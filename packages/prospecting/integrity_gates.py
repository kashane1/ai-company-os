"""Integrity gates that keep BBW from building/sending for high-risk prospects.

The first gate covers the **notario-fraud zone**: non-attorney businesses that
advertise *immigration paperwork* (immigration consultant, servicios de
inmigración, "notario público" sold to Spanish speakers, USCIS/green-card/asylum
help) to a vulnerable, largely Spanish-speaking community. Building a polished
promotional site for one can funnel vulnerable people toward a possibly
unlicensed or fraudulent service, so policy is to treat the whole category as
do-not-contact by default and let a founder override a specific legitimate one
by deliberately un-suppressing it.

**Coverage and its limit (read this).** Detection keys on the business *name*
and Google *types* only — the signals stored on a ``ProspectRecord``. It does
*not* read review text (Phase-1 ingest skips it). So it reliably catches
name-evident cases ("Rodelas Immigration Consultant") but **cannot** catch a
business whose immigration work shows up only in its reviews under an opaque
name (e.g. "Grupo Francie INC"). Those still depend on the human integrity pass
during the build loop. This gate narrows the manual surface; it does not replace
the reviewer.

A genuine law firm / attorney (regulated, licensed to practice immigration law)
is explicitly *excluded* from the gate — the rule targets *non-attorney*
paperwork shops, per the founder decision (2026-06-15).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

# A name in the immigration-paperwork zone is only *auto-excluded* when its
# rating is also below this threshold. The founder rule (2026-06-15, refined
# 2026-06-16) pairs the category signal with a low-rating requirement so a
# high-rated, complaint-free business that merely has "immigration" in its name
# (e.g. a 4.7/527 passport-photo shop) is left alone. A prospect with no rating
# yet (unverified source candidates, 0 reviews) carries no rating signal and is
# likewise not auto-excluded — it gets re-evaluated once enriched.
MAX_RATING_FOR_EXCLUSION = 4.0

# Positive signals (matched on an accent-stripped, lowercased string built from
# the display name + Google types + genre_id). Kept high-precision on purpose:
# bare "notary"/"visa"/"residency" are intentionally absent because they sweep
# in legitimate English-language notaries and travel/medical/real-estate
# businesses. The Spanish "notario/notaría" *is* included — advertising oneself
# as a "notario" to Spanish speakers in the US is itself the notario-fraud
# vector many states prohibit.
_IMMIGRATION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bimmigration\b", "immigration"),
    (r"\binmigra", "inmigración"),
    (r"\bmigratori[oa]\b", "migratorio/a"),
    (r"\bnotari[oa]\b", "notario/notaría"),
    (r"\buscis\b", "uscis"),
    # "asylum"/"asilo" are deliberately omitted: "asylum" is a common place name
    # (Hawthorne Asylum food pod) and "asilo" is Spanish for a nursing home.
    # Bare "deport" would match Spanish "deportes" (sports); match the full word.
    (r"\bdeportation\b", "deportation"),
    (r"\bdeportaci", "deportación"),
    (r"\bgreen ?card\b", "green card"),
    (r"\bciudadania\b", "ciudadanía"),
)

# If any of these is present, the business is a regulated attorney/law practice
# and the gate does NOT fire — the rule targets non-attorney paperwork shops.
_ATTORNEY_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\blaw\b", "law"),
    (r"\blaw (firm|office|offices|group)\b", "law firm/office"),
    (r"\blawyer", "lawyer"),
    (r"\battorney", "attorney"),
    (r"\babogad", "abogado/a"),
    (r"\besq\b", "esq"),
    (r"\blegal\b", "legal"),
)


def _normalize(text: str) -> str:
    """Lowercase and strip accents so "inmigración" == "inmigracion"."""
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return ascii_text.lower()


@dataclass(frozen=True)
class GateResult:
    """Outcome of evaluating the immigration-paperwork gate against a record."""

    matched: bool
    terms: list[str] = field(default_factory=list)
    is_attorney: bool = False
    attorney_terms: list[str] = field(default_factory=list)
    rating: float | None = None

    def reason(self) -> str:
        """A short, registry-ready reason string for a positive match."""
        joined = ", ".join(self.terms) if self.terms else "immigration-paperwork signal"
        rating_note = f", rating {self.rating}" if self.rating is not None else ""
        return (
            "integrity: non-attorney immigration-paperwork prospect "
            f"(notario-fraud zone; matched: {joined}{rating_note}) — category "
            "gate + sub-4.0 rating (BBW 2026-06-16)"
        )


def _haystack(display_name: str, types: Iterable[str], genre_id: str) -> str:
    parts = [display_name or "", " ".join(str(t) for t in (types or [])), genre_id or ""]
    return _normalize(" ".join(p for p in parts if p))


def evaluate_immigration_paperwork(
    display_name: str,
    *,
    types: Iterable[str] | None = None,
    genre_id: str = "",
) -> GateResult:
    """Evaluate the immigration-paperwork gate against name/types/genre.

    Fires (``matched=True``) when an immigration-paperwork term is present AND no
    attorney/law-practice term is present. Attorney practices are regulated and
    explicitly out of scope.
    """
    hay = _haystack(display_name, types or [], genre_id)
    attorney_hits = [label for pat, label in _ATTORNEY_PATTERNS if re.search(pat, hay)]
    imm_hits = [label for pat, label in _IMMIGRATION_PATTERNS if re.search(pat, hay)]
    if attorney_hits:
        return GateResult(matched=False, terms=imm_hits, is_attorney=True, attorney_terms=attorney_hits)
    return GateResult(matched=bool(imm_hits), terms=imm_hits)


def evaluate_record(record: dict[str, object]) -> GateResult:
    """Pure name/type gate (no rating filter) for a prospect record dict."""
    return evaluate_immigration_paperwork(
        str(record.get("display_name", "")),
        types=record.get("types") if isinstance(record.get("types"), list) else [],
        genre_id=str(record.get("genre_id", "")),
    )


def _rating_of(record: dict[str, object]) -> float | None:
    raw = record.get("rating")
    if raw is None:
        return None
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def evaluate_record_for_exclusion(record: dict[str, object]) -> GateResult:
    """Full founder policy: auto-exclude only when the name is in the
    immigration-paperwork zone AND the rating is present and below
    ``MAX_RATING_FOR_EXCLUSION``.

    Returns a non-matching ``GateResult`` (carrying the detected terms for
    transparency) when the name matches but the rating spares it.
    """
    base = evaluate_record(record)
    rating = _rating_of(record)
    if not base.matched:
        return GateResult(matched=False, terms=base.terms, rating=rating)
    if rating is None or rating >= MAX_RATING_FOR_EXCLUSION:
        return GateResult(matched=False, terms=base.terms, rating=rating)
    return GateResult(matched=True, terms=base.terms, rating=rating)


__all__ = [
    "GateResult",
    "MAX_RATING_FOR_EXCLUSION",
    "evaluate_immigration_paperwork",
    "evaluate_record",
    "evaluate_record_for_exclusion",
]
