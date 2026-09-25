"""Etsy-specific opportunity evidence, sectioning, and gated scoring."""

from __future__ import annotations

import csv
import math
import re
from dataclasses import asdict, dataclass
from typing import IO, Mapping, Sequence


SECTION_LABELS = {
    "workday_absurdity": "Workday Absurdity",
    "tiny_morale_boosts": "Tiny Morale Boosts",
    "useful_useless_facts": "Useful Useless Facts",
    "seasonal_work_breaks": "Seasonal Work Breaks",
    "exception": "Exception",
}

MARKETPLACE_COLUMNS = (
    "query",
    "observed_at",
    "searches_30d",
    "competing_listings",
    "related_queries",
    "trend",
    "dominant_visual_pattern",
    "price_band_usd",
    "buyer_occasion",
    "notes",
)

FACTOR_WEIGHTS = {
    "buyer_demand": 25,
    "competitive_room": 20,
    "buyer_clarity": 20,
    "brand_fit": 15,
    "visual_differentiation": 10,
    "product_fit": 10,
}

_SPECIFIC_QUERY_HINTS = {
    "breathing manually shirt": ("breathing manually",),
    "funny raccoon shirt": ("raccoon",),
    "snack lover shirt": ("snack",),
    "funny cat shirt": ("cat", "kitten"),
    "cat pun shirt": ("cat", "kitten"),
    "wombat poop shirt": ("wombat",),
    "funny astronomy shirt": ("astronomy", "venus", "planet", "solar"),
    "halloween work shirt": ("halloween", "ghost", "witch", "boo"),
}

_SECTION_QUERY_FALLBACKS = {
    "workday_absurdity": (
        "funny work from home shirt",
        "funny coworker shirt",
        "coworker gift shirt",
    ),
    "tiny_morale_boosts": ("motivational animal shirt", "encouragement shirt"),
    "useful_useless_facts": ("animal fact shirt", "science humor shirt"),
    "seasonal_work_breaks": ("halloween work shirt",),
    "exception": (),
}


@dataclass(frozen=True)
class MarketplaceInsight:
    query: str
    observed_at: str
    searches_30d: int | None
    competing_listings: int | None
    related_queries: str
    trend: str
    dominant_visual_pattern: str
    price_band_usd: str
    buyer_occasion: str
    notes: str


@dataclass(frozen=True)
class SectionAssignment:
    primary: str
    secondary: str | None
    rationale: str
    confidence: str


@dataclass(frozen=True)
class HardGates:
    ip: bool | None
    production: bool | None
    economics: bool | None
    policy: bool | None


@dataclass(frozen=True)
class CandidateScore:
    candidate_id: str
    eligible: bool
    status: str
    weighted_score: float | None
    available_points: float
    evidence_coverage: float
    failed_gates: tuple[str, ...]
    unknown_gates: tuple[str, ...]
    factor_scores: Mapping[str, float | None]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _optional_int(value: str, field: str, row_number: int) -> int | None:
    value = value.strip().replace(",", "")
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"row {row_number}: {field} must be an integer or blank") from exc
    if parsed < 0:
        raise ValueError(f"row {row_number}: {field} cannot be negative")
    return parsed


def parse_marketplace_insights(stream: IO[str]) -> list[MarketplaceInsight]:
    """Parse the founder-completed Marketplace Insights worksheet.

    Etsy Insights is intentionally gathered manually. Blank numeric values remain
    unknown rather than becoming zero-demand evidence.
    """

    reader = csv.DictReader(stream)
    columns = set(reader.fieldnames or [])
    missing = sorted(set(MARKETPLACE_COLUMNS) - columns)
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")
    rows: list[MarketplaceInsight] = []
    for row_number, row in enumerate(reader, start=2):
        query = (row.get("query") or "").strip()
        if not query:
            raise ValueError(f"row {row_number}: query is required")
        searches_30d = _optional_int(
            row.get("searches_30d") or "", "searches_30d", row_number
        )
        competing_listings = _optional_int(
            row.get("competing_listings") or "", "competing_listings", row_number
        )
        observed_at = (row.get("observed_at") or "").strip()
        if (searches_30d is not None or competing_listings is not None) and not observed_at:
            raise ValueError(f"row {row_number}: observed_at is required for observed metrics")
        rows.append(
            MarketplaceInsight(
                query=query,
                observed_at=observed_at,
                searches_30d=searches_30d,
                competing_listings=competing_listings,
                related_queries=(row.get("related_queries") or "").strip(),
                trend=(row.get("trend") or "").strip(),
                dominant_visual_pattern=(
                    row.get("dominant_visual_pattern") or ""
                ).strip(),
                price_band_usd=(row.get("price_band_usd") or "").strip(),
                buyer_occasion=(row.get("buyer_occasion") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            )
        )
    return rows


def _related_query_count(value: str) -> int:
    return len([part for part in re.split(r"[;,|]", value) if part.strip()])


def _mean(values: Sequence[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _matches_hint(text: str, hint: str) -> bool:
    """Match a query hint as a complete word or phrase, never a substring."""

    return re.search(rf"(?<!\w){re.escape(hint)}(?!\w)", text) is not None


def marketplace_factor_scores(
    insights: Sequence[MarketplaceInsight],
    *,
    candidate_text: str,
    section: str,
) -> dict[str, object]:
    """Map manual first-party observations to two reproducible score factors.

    Specific concept queries take precedence over broad section queries. Demand
    uses a log scale (25 points per order of magnitude) plus up to ten points
    for related-query depth. Competitive room centers a 1:1 search/listing ratio
    at 50 and changes 25 points per order of magnitude. These are ranking
    heuristics, not sales forecasts.
    """

    available = {row.query.casefold(): row for row in insights}
    text = candidate_text.casefold()
    specific = [
        query
        for query, hints in _SPECIFIC_QUERY_HINTS.items()
        if query in available and any(_matches_hint(text, hint) for hint in hints)
    ]
    query_names = specific or [
        query
        for query in _SECTION_QUERY_FALLBACKS.get(section, ())
        if query in available
    ]
    matched = [available[query] for query in query_names]
    missing_metric_queries = [
        row.query
        for row in matched
        if row.searches_30d is None or row.competing_listings is None
    ]
    errored_queries = [
        row.query for row in matched if "error" in row.notes.casefold()
    ]

    demand_scores: list[float] = []
    competition_scores: list[float] = []
    for row in matched:
        if row.searches_30d is not None:
            related_bonus = min(10.0, _related_query_count(row.related_queries) * 5.0)
            demand_scores.append(
                min(
                    100.0,
                    (25.0 * math.log10(row.searches_30d) if row.searches_30d > 0 else 0.0)
                    + related_bonus,
                )
            )
        if row.searches_30d is not None and row.competing_listings is not None:
            if row.competing_listings == 0:
                room = 100.0 if row.searches_30d > 0 else 50.0
            elif row.searches_30d == 0:
                room = 0.0
            else:
                ratio = row.searches_30d / row.competing_listings
                room = max(0.0, min(100.0, 50.0 + 25.0 * math.log10(ratio)))
            competition_scores.append(room)

    buyer_demand = _mean(demand_scores)
    competitive_room = _mean(competition_scores)
    return {
        "matched_queries": query_names,
        "missing_metric_queries": missing_metric_queries,
        "errored_queries": errored_queries,
        "buyer_demand": buyer_demand,
        "competitive_room": competitive_room,
        "evidence_complete": (
            buyer_demand is not None
            and competitive_room is not None
            and not missing_metric_queries
        ),
        "method": (
            "manual Etsy Marketplace Insights; concept-specific query precedence; "
            "log-scaled searches and search-to-listing ratio"
        ),
    }


def classify_listing(*, title: str, key: str) -> SectionAssignment:
    # Batch folders can contain unrelated ideas (for example
    # ``witch-venus-steak``); only the leaf key is evidence about this listing.
    leaf_key = key.rsplit("/", 1)[-1]
    text = f"{title} {leaf_key}".casefold()
    if any(word in text for word in ("halloween", "ghost", "witch", "boo sheet", "here for the boos")):
        secondary = "workday_absurdity" if "witch" in text else None
        return SectionAssignment(
            "seasonal_work_breaks",
            secondary,
            "The concept depends on a time-bound Halloween or spooky-season buying occasion.",
            "high",
        )
    if any(
        phrase in text
        for phrase in (
            "wombat poop",
            "venus",
            "lightning and sun",
            "bananas are berries",
            "body hole",
            "astronomy",
            "science fact",
            "anatomy",
            "being third",
        )
    ):
        return SectionAssignment(
            "useful_useless_facts",
            None,
            "The buyer hook is a surprising fact, science joke, or nerdy conversation starter.",
            "high",
        )
    if any(
        phrase in text
        for phrase in (
            "hold on tight",
            "reach for the stars",
            "slow and steady",
            "weather the storm",
            "hang in there",
            "brighter days ahead",
            "dream big",
            "follow your heart",
            "take the leap",
            "new leaf",
            "go with the flow",
        )
    ):
        return SectionAssignment(
            "tiny_morale_boosts",
            None,
            "The product offers a small encouragement suitable for self-purchase or a supportive gift.",
            "high",
        )
    if any(
        phrase in text
        for phrase in (
            "breathing manually",
            "there would be snacks",
            "just kitten around",
            "rise and shine",
            "mouth is a body hole",
        )
    ):
        return SectionAssignment(
            "workday_absurdity",
            None,
            "The joke can be framed as desk-life relief, a coworker gift, or workday self-purchase.",
            "medium",
        )
    return SectionAssignment(
        "exception",
        None,
        "No strong connection to a named HomeFromWorking section is established by current evidence.",
        "high",
    )


def score_candidate(
    candidate_id: str,
    gates: HardGates,
    factor_scores: Mapping[str, float | int | None],
) -> CandidateScore:
    missing_factors = sorted(set(FACTOR_WEIGHTS) - set(factor_scores))
    extra_factors = sorted(set(factor_scores) - set(FACTOR_WEIGHTS))
    if missing_factors or extra_factors:
        raise ValueError(
            f"factor mismatch; missing={missing_factors or 'none'} extra={extra_factors or 'none'}"
        )
    normalized: dict[str, float | None] = {}
    for name, value in factor_scores.items():
        if value is None:
            normalized[name] = None
            continue
        numeric = float(value)
        if not 0 <= numeric <= 100:
            raise ValueError(f"{name} must be between 0 and 100")
        normalized[name] = numeric

    gate_values = asdict(gates)
    failed = tuple(sorted(name for name, value in gate_values.items() if value is False))
    unknown = tuple(sorted(name for name, value in gate_values.items() if value is None))
    known_factor_weight = sum(
        weight for name, weight in FACTOR_WEIGHTS.items() if normalized[name] is not None
    )
    available_points = sum(
        FACTOR_WEIGHTS[name] * value / 100
        for name, value in normalized.items()
        if value is not None
    )
    coverage = known_factor_weight / 100

    if failed:
        return CandidateScore(
            candidate_id,
            False,
            "failed_hard_gate",
            None,
            round(available_points, 4),
            coverage,
            failed,
            unknown,
            normalized,
        )
    if unknown:
        return CandidateScore(
            candidate_id,
            False,
            "blocked_unknown_hard_gate",
            None,
            round(available_points, 4),
            coverage,
            failed,
            unknown,
            normalized,
        )
    if known_factor_weight < 100:
        return CandidateScore(
            candidate_id,
            True,
            "provisional_missing_evidence",
            None,
            round(available_points, 4),
            coverage,
            failed,
            unknown,
            normalized,
        )
    return CandidateScore(
        candidate_id,
        True,
        "scored",
        round(available_points, 4),
        round(available_points, 4),
        coverage,
        failed,
        unknown,
        normalized,
    )
