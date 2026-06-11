"""Plan the next safe prospect qualification step."""

from __future__ import annotations

from dataclasses import dataclass

from packages.schemas.prospect import ProspectRecord, WebVerifyVerdict

QUALIFICATION_COHORT_PRIORITY = [
    "A2_marketplace_review",
    "B_stale_maps",
    "A_gold",
    "C_potential_signal",
    "S_source_candidate",
]


@dataclass(frozen=True)
class QualificationPlan:
    action: str
    reason: str
    provider: str
    cohort: str = ""
    command: str = ""
    candidate_count: int = 0
    candidate_place_ids: list[str] | None = None


def next_qualification_plan(
    records: list[ProspectRecord],
    *,
    provider: str,
    limit: int,
) -> QualificationPlan:
    for cohort in QUALIFICATION_COHORT_PRIORITY:
        candidates = _unverified_records(records, cohort=cohort)
        if not candidates:
            continue
        selected = candidates[: max(limit, 0)]
        selected_limit = len(selected)
        return QualificationPlan(
            action="verify_current_warehouse",
            reason=(
                f"{cohort} has {len(candidates)} unverified candidate(s); "
                "verify these before collecting new source data"
            ),
            provider=provider,
            cohort=cohort,
            command=(
                "python scripts/prospect_scan.py verify-web "
                f"--provider {provider} --cohort {cohort} --limit {selected_limit}"
            ),
            candidate_count=len(candidates),
            candidate_place_ids=[record.place_id for record in selected],
        )

    return QualificationPlan(
        action="collect_new_source_data",
        reason=(
            "current high-priority warehouse cohorts are web-verified; use the "
            "source-run ledger and identity index before importing any Overture, "
            "Foursquare, OSM, or open-data candidates"
        ),
        provider=provider,
        candidate_place_ids=[],
    )


def _unverified_records(records: list[ProspectRecord], *, cohort: str) -> list[ProspectRecord]:
    candidates = [
        record
        for record in records
        if record.composite_cohort == cohort
        and record.web_verify_verdict is WebVerifyVerdict.UNVERIFIED
    ]
    return sorted(
        candidates,
        key=lambda record: (-record.priority_score, record.display_name.lower()),
    )
