from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from packages.prospecting.config import CityConfig, GenreConfig, WeeklyCaps
from packages.prospecting.run import run_prospecting
from packages.prospecting.storage import ProspectRepository
from packages.schemas.prospect import (
    HttpCheck,
    HttpCheckClass,
    MapsWebsiteClass,
    ProspectRecord,
)
from scripts.prospect_scan import _selected_cells_for_start

FIXED = datetime(2026, 6, 1, tzinfo=timezone.utc)


class StubPlacesConnector:
    def search_cell(self, city: CityConfig, genre: GenreConfig, *, limit: int) -> list[str]:
        return ["places/abc123", "places/missing"]

    def fetch_details(self, place_id: str) -> ProspectRecord:
        if place_id.endswith("missing"):
            return ProspectRecord(
                place_id=place_id,
                display_name="Missing Website Shop",
                formatted_address="Seattle, WA",
                phone="+1 206-555-0101",
                types=["beauty_salon"],
                city_id="",
                genre_id="",
                grid_cell_id="",
                maps_website_class=MapsWebsiteClass.ABSENT,
                rating=4.5,
                user_ratings_total=31,
            )
        return ProspectRecord(
            place_id=place_id,
            display_name="Tonic Salon",
            formatted_address="Seattle, WA",
            phone="+1 206-555-0100",
            types=["beauty_salon"],
            city_id="",
            genre_id="",
            grid_cell_id="",
            maps_website_uri="https://facebook.com/tonic",
            maps_website_host="facebook.com",
            maps_website_class=MapsWebsiteClass.SOCIAL_ONLY,
            rating=4.7,
            user_ratings_total=26,
        )


class StubHTTPChecker:
    def check(self, url: str) -> HttpCheck:
        return HttpCheck(
            http_check_class=HttpCheckClass.REDIRECT_SOCIAL,
            final_url=url,
            status=200,
            checked_at=FIXED.isoformat(),
        )


def test_run_prospecting_persists_deduped_records_and_assigns_cohorts(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    city = CityConfig(id="seattle", name="Seattle", lat=47.6062, lng=-122.3321)
    genre = GenreConfig(id="beauty_salon", label="beauty salon", text_query_template="{label} in {city_name}")

    report = run_prospecting(
        cities=[city],
        genres=[genre],
        cells_limit=1,
        records=repo,
        places=StubPlacesConnector(),
        http_checker=StubHTTPChecker(),
        weekly_caps=WeeklyCaps(text_search_requests=10, place_details_essentials=10, http_checks=10),
        now=lambda: FIXED,
        selected_cells=["seattle:beauty_salon"],
    )
    second = run_prospecting(
        cities=[city],
        genres=[genre],
        cells_limit=1,
        records=repo,
        places=StubPlacesConnector(),
        http_checker=StubHTTPChecker(),
        weekly_caps=WeeklyCaps(text_search_requests=10, place_details_essentials=10, http_checks=10),
        now=lambda: FIXED,
        selected_cells=["seattle:beauty_salon"],
    )

    records = repo.list()
    assert report.status == "completed"
    assert second.records_created == 0
    assert len(records) == 2
    assert records[0].grid_cell_id == "seattle:beauty_salon"
    assert records[0].composite_cohort == "A_gold"
    assert records[0].http_check_class is HttpCheckClass.REDIRECT_SOCIAL

    skipped = [record for record in records if record.http_check_class is HttpCheckClass.SKIPPED]
    assert skipped
    assert all(record.http_skip_reason for record in skipped)


def test_required_seattle_smoke_command_is_pinned_to_named_cells() -> None:
    assert _selected_cells_for_start(approved_by="codex-phase1-smoke", cells=2, requested=[]) == [
        "seattle:beauty_salon",
        "seattle:auto_repair",
    ]
