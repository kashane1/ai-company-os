from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from packages.prospecting.storage import ProspectRepository
from packages.prospecting.verification import (
    recompute_cohorts_and_priority_scores,
    export_cohort_a_verification_csv,
    import_verifications_csv,
)
from packages.schemas.prospect import (
    HumanVerified,
    HttpCheckClass,
    MapsWebsiteClass,
    ProspectRecord,
)

FIXED = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)


def _record(place_id: str, cohort: str, priority_score: float) -> ProspectRecord:
    return ProspectRecord(
        place_id=place_id,
        display_name=f"Business {place_id}",
        formatted_address="Seattle, WA",
        phone="+1 206-555-0100",
        types=["beauty_salon"],
        city_id="seattle",
        genre_id="beauty_salon",
        grid_cell_id="seattle:beauty_salon",
        maps_website_class=MapsWebsiteClass.ABSENT,
        user_ratings_total=50,
        http_check_class=HttpCheckClass.SKIPPED,
        composite_cohort=cohort,
        priority_score=priority_score,
    )


def test_export_cohort_a_verification_csv_is_sorted_and_operator_blank(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    repo.save(_record("places/low", "A_gold", 20))
    repo.save(_record("places/high", "A_gold", 90))
    repo.save(_record("places/z", "Z_needs_review", 100))
    repo.save(
        ProspectRecord.from_dict(
            {
                **_record("places/seattle-beauty_salon-1", "A_gold", 95).to_dict(),
                "display_name": "Fixture Local 1",
            }
        )
    )

    paths = export_cohort_a_verification_csv(
        repo.list(),
        output_dir=tmp_path / "exports",
        today=lambda: FIXED,
    )

    assert [p.name for p in paths] == ["seattle-cohortA-2026-06-01.csv"]
    path = paths[0]
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["place_id"] for row in rows] == ["places/high", "places/low"]
    assert [row["human_verified"] for row in rows] == ["", ""]
    assert [row["human_verify_note"] for row in rows] == ["", ""]
    assert rows[0]["maps_url"].endswith("query_place_id=places%2Fhigh")
    # Maps URL must include the required `query` param so the link actually
    # resolves (regression: query_place_id alone does not open the place).
    assert "query=" in rows[0]["maps_url"]


def _record_in_city(place_id: str, city_id: str, priority_score: float) -> ProspectRecord:
    return ProspectRecord.from_dict(
        {
            **_record(place_id, "A_gold", priority_score).to_dict(),
            "city_id": city_id,
        }
    )


def test_export_writes_one_file_per_city(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    repo.save(_record_in_city("places/sea1", "seattle", 90))
    repo.save(_record_in_city("places/pdx1", "portland", 80))
    repo.save(_record_in_city("places/pdx2", "portland", 95))
    repo.save(_record_in_city("places/den1", "denver", 70))

    paths = export_cohort_a_verification_csv(
        repo.list(),
        output_dir=tmp_path / "exports",
        today=lambda: FIXED,
    )

    assert [p.name for p in paths] == [
        "denver-cohortA-2026-06-01.csv",
        "portland-cohortA-2026-06-01.csv",
        "seattle-cohortA-2026-06-01.csv",
    ]
    # Each file holds only its own city's prospects, sorted by priority desc.
    portland = next(p for p in paths if p.name.startswith("portland"))
    with portland.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["place_id"] for row in rows] == ["places/pdx2", "places/pdx1"]


def test_import_verifications_csv_sets_only_operator_filled_fields(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    repo.save(_record("places/yes", "A_gold", 90))
    repo.save(_record("places/no", "A_gold", 80))

    csv_path = tmp_path / "filled.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["place_id", "human_verified", "human_verify_note"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "place_id": "places/yes",
                "human_verified": "true",
                "human_verify_note": "GBP spot-check passed",
            }
        )
        writer.writerow(
            {
                "place_id": "places/no",
                "human_verified": "false",
                "human_verify_note": "Found working owned website",
            }
        )

    result = import_verifications_csv(repo, csv_path, now=lambda: FIXED)

    assert result.updated == 2
    assert repo.get("places/yes").human_verified is HumanVerified.TRUE
    assert repo.get("places/yes").human_verified_at == FIXED.isoformat()
    assert repo.get("places/yes").human_verify_note == "GBP spot-check passed"
    assert repo.get("places/no").human_verified is HumanVerified.FALSE


def test_recompute_cohorts_and_priority_scores_backfills_existing_records(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    repo.save(
        ProspectRecord(
            place_id="places/backfill",
            display_name="Backfill Business",
            formatted_address="Seattle, WA",
            phone="",
            types=[],
            city_id="seattle",
            genre_id="beauty_salon",
            grid_cell_id="seattle:beauty_salon",
            maps_website_class=MapsWebsiteClass.ABSENT,
            user_ratings_total=75,
            http_check_class=HttpCheckClass.SKIPPED,
            composite_cohort="",
            priority_score=0.0,
        )
    )

    result = recompute_cohorts_and_priority_scores(repo, now=lambda: FIXED)

    record = repo.get("places/backfill")
    assert result.updated == 1
    assert record.composite_cohort == "A_gold"
    assert record.priority_score == 75.0
    assert record.updated_at == FIXED.isoformat()
