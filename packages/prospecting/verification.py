"""Operator verification export/import helpers for cohort-A prospects (per city)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode

from packages.config.settings import load_runtime_paths
from packages.prospecting.cohorts import derive_composite_cohort, priority_score
from packages.prospecting.storage import ProspectRepository
from packages.schemas.prospect import HumanVerified, ProspectRecord, replace_record

EXPORT_COLUMNS = [
    "place_id",
    "display_name",
    "city_id",
    "genre_id",
    "composite_cohort",
    "formatted_address",
    "phone",
    "maps_website_class",
    "maps_website_uri",
    "http_check_class",
    "user_ratings_total",
    "priority_score",
    "maps_url",
    "human_verified",
    "human_verify_note",
]

# Default per-cohort export labels used in the output filename
# (``<city>-<label>-<date>.csv``).
COHORT_EXPORT_LABELS = {
    "A_gold": "cohortA",
    "A2_marketplace_review": "cohortA2",
    "B_stale_maps": "cohortB",
    "C_potential_signal": "cohortC",
    "D_low_signal": "cohortD",
    "E_has_site": "cohortE",
    "Z_needs_review": "cohortZ",
}


@dataclass(frozen=True)
class VerificationImportResult:
    updated: int = 0
    skipped: int = 0
    missing: list[str] | None = None


@dataclass(frozen=True)
class RecomputeResult:
    updated: int = 0


def default_exports_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).state_root / "prospects" / "exports"


def dry_run_exports_root(repo_root: Path | None = None) -> Path:
    """Isolated exports folder for ``--dry-run`` so fixtures never mix with prod."""
    return load_runtime_paths(repo_root).state_root / "prospects" / "dry_run" / "exports"


def export_cohort_verification_csv(
    records: list[ProspectRecord],
    *,
    cohort: str,
    label: str | None = None,
    output_dir: Path | None = None,
    today: Callable[[], datetime] | None = None,
) -> list[Path]:
    """Write one ``<city>-<label>-<date>.csv`` per city for the given cohort.

    Prospects are grouped by ``city_id`` so every crawled city lands as its own
    operator file. ``label`` defaults to the cohort's entry in
    ``COHORT_EXPORT_LABELS`` (falling back to the raw cohort name). Returns the
    written paths sorted by city.
    """
    clock = today or (lambda: datetime.now(timezone.utc))
    target_dir = output_dir or default_exports_root()
    target_dir.mkdir(parents=True, exist_ok=True)
    file_label = label or COHORT_EXPORT_LABELS.get(cohort, cohort)

    by_city: dict[str, list[ProspectRecord]] = {}
    for record in records:
        if record.composite_cohort != cohort or not _is_operator_exportable(record):
            continue
        by_city.setdefault(record.city_id or "unknown", []).append(record)

    written: list[Path] = []
    for city_id in sorted(by_city):
        rows = sorted(
            by_city[city_id],
            key=lambda record: (-record.priority_score, record.display_name.lower()),
        )
        target = target_dir / f"{city_id}-{file_label}-{clock().date().isoformat()}.csv"
        with target.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=EXPORT_COLUMNS)
            writer.writeheader()
            for record in rows:
                writer.writerow(_export_row(record))
        written.append(target)
    return written


def export_cohort_a_verification_csv(
    records: list[ProspectRecord],
    *,
    output_dir: Path | None = None,
    today: Callable[[], datetime] | None = None,
) -> list[Path]:
    """Backward-compatible wrapper: export the ``A_gold`` cohort per city."""
    return export_cohort_verification_csv(
        records, cohort="A_gold", output_dir=output_dir, today=today
    )


def import_verifications_csv(
    records: ProspectRepository,
    csv_path: Path,
    *,
    now: Callable[[], datetime] | None = None,
) -> VerificationImportResult:
    clock = now or (lambda: datetime.now(timezone.utc))
    updated = 0
    skipped = 0
    missing: list[str] = []
    with csv_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            place_id = str(row.get("place_id", "")).strip()
            verified = str(row.get("human_verified", "")).strip().lower()
            if not place_id or not verified:
                skipped += 1
                continue
            if verified not in {item.value for item in HumanVerified}:
                raise ValueError(f"Invalid human_verified value for {place_id}: {verified}")
            if not records.exists(place_id):
                missing.append(place_id)
                continue
            timestamp = "" if verified == HumanVerified.UNSET.value else clock().isoformat()
            records.save(
                replace_record(
                    records.get(place_id),
                    human_verified=verified,
                    human_verified_at=timestamp,
                    human_verify_note=str(row.get("human_verify_note", "")).strip(),
                    updated_at=clock().isoformat(),
                )
            )
            updated += 1
    return VerificationImportResult(updated=updated, skipped=skipped, missing=missing)


def recompute_cohorts_and_priority_scores(
    records: ProspectRepository,
    *,
    now: Callable[[], datetime] | None = None,
) -> RecomputeResult:
    clock = now or (lambda: datetime.now(timezone.utc))
    updated = 0
    for record in records.list():
        cohort = derive_composite_cohort(record)
        score = priority_score(record, cohort)
        if record.composite_cohort == cohort and record.priority_score == score:
            continue
        records.save(
            replace_record(
                record,
                composite_cohort=cohort,
                priority_score=score,
                updated_at=clock().isoformat(),
            )
        )
        updated += 1
    return RecomputeResult(updated=updated)


def maps_url(record: ProspectRecord) -> str:
    # Google Maps requires a non-empty `query` alongside `query_place_id`; a URL
    # with only `query_place_id` does not resolve (the Phase 2 export bug). We use
    # the business name (falling back to address, then place_id) as the query so
    # the link always opens the correct place. `query_place_id` stays last.
    query = record.display_name or record.formatted_address or record.place_id
    return "https://www.google.com/maps/search/?" + urlencode(
        {"api": "1", "query": query, "query_place_id": record.place_id}
    )


def _export_row(record: ProspectRecord) -> dict[str, object]:
    return {
        "place_id": record.place_id,
        "display_name": record.display_name,
        "city_id": record.city_id,
        "genre_id": record.genre_id,
        "composite_cohort": record.composite_cohort,
        "formatted_address": record.formatted_address,
        "phone": record.phone,
        "maps_website_class": record.maps_website_class.value,
        "maps_website_uri": record.maps_website_uri,
        "http_check_class": record.http_check_class.value,
        "user_ratings_total": record.user_ratings_total,
        "priority_score": f"{record.priority_score:.2f}",
        "maps_url": maps_url(record),
        "human_verified": "",
        "human_verify_note": "",
    }


def _is_operator_exportable(record: ProspectRecord) -> bool:
    # Dry-run fixture rows may persist in local state, but they are not emailable prospects.
    if record.display_name.startswith("Fixture Local"):
        return False
    if record.place_id.startswith("places/seattle-"):
        return False
    return True
