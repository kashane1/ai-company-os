from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from packages.prospecting.config import CityConfig, GenreConfig
from packages.prospecting.identity import ProspectCandidate
from packages.prospecting.source_import import (
    render_source_collection_report,
    run_source_collection,
)
from packages.prospecting.source_runs import SourceRunRecord, SourceRunStore
from packages.prospecting.storage import ProspectRepository
from packages.schemas.prospect import MapsWebsiteClass, ProspectRecord, WebVerifyVerdict


class FakeSourceConnector:
    source = "overture"
    connector_version = "test-v1"

    def __init__(self, candidates: list[ProspectCandidate]) -> None:
        self.candidates = candidates
        self.calls: list[tuple[str, str, int]] = []

    def query_for(self, city: CityConfig, genre: GenreConfig) -> str:
        return f"{genre.id} near {city.id}"

    def fetch_candidates(
        self, city: CityConfig, genre: GenreConfig, *, limit: int
    ) -> list[ProspectCandidate]:
        self.calls.append((city.id, genre.id, limit))
        return self.candidates[:limit]


def test_source_collection_creates_only_new_identity_safe_records(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    existing = _record("places/existing", phone="+1 206-555-0100")
    repo.save(existing)
    source_runs = SourceRunStore(tmp_path / "source-runs")
    connector = FakeSourceConnector(
        [
            ProspectCandidate(
                source="overture",
                source_id="duplicate",
                display_name="Existing Shop",
                formatted_address="10 Pine St, Seattle, WA",
                phone="206-555-0100",
                city_id="seattle",
                genre_id="nail_salon",
            ),
            ProspectCandidate(
                source="overture",
                source_id="fresh-1",
                display_name="Fresh Nails",
                formatted_address="20 Pine St, Seattle, WA",
                phone="206-555-0199",
                city_id="seattle",
                genre_id="nail_salon",
            ),
        ]
    )

    report = run_source_collection(
        cities=[_city()],
        genres=[_genre()],
        records=repo,
        source_runs=source_runs,
        connector=connector,
        candidates_per_cell=50,
        now=lambda: datetime(2026, 6, 10, tzinfo=timezone.utc),
    )

    assert report.status == "completed"
    assert report.cells_processed == 1
    assert report.candidates_seen == 2
    assert report.records_created == 1
    assert report.duplicates_skipped == 1
    assert report.present_site_skipped == 0
    assert report.absent_website_candidates == 2
    assert report.social_only_candidates == 0
    assert report.marketplace_candidates == 0

    created = repo.get("source/overture:fresh-1")
    assert created.display_name == "Fresh Nails"
    assert created.source_name == "overture"
    assert created.source_record_id == "fresh-1"
    assert created.source_run_key
    assert created.composite_cohort == "S_source_candidate"
    assert created.maps_website_class is MapsWebsiteClass.ABSENT
    assert created.web_verify_verdict is WebVerifyVerdict.UNVERIFIED

    ledger = source_runs.latest_for_cell("overture", "seattle", "nail_salon")
    assert ledger is not None
    assert ledger.status == "completed"
    assert ledger.candidates_seen == 2
    assert ledger.records_created == 1
    assert ledger.duplicates_skipped == 1


def test_source_collection_skips_completed_run_without_force(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    source_runs = SourceRunStore(tmp_path / "source-runs")
    connector = FakeSourceConnector(
        [
            ProspectCandidate(
                source="overture",
                source_id="fresh-1",
                display_name="Fresh Nails",
                formatted_address="20 Pine St, Seattle, WA",
                phone="206-555-0199",
                city_id="seattle",
                genre_id="nail_salon",
            )
        ]
    )
    source_runs.save(
        SourceRunRecord(
            source="overture",
            city_id="seattle",
            genre_id="nail_salon",
            query="nail_salon near seattle",
            connector_version="test-v1",
            status="completed",
        )
    )

    report = run_source_collection(
        cities=[_city()],
        genres=[_genre()],
        records=repo,
        source_runs=source_runs,
        connector=connector,
        candidates_per_cell=50,
    )

    assert report.status == "completed"
    assert report.runs_skipped == 1
    assert report.records_created == 0
    assert connector.calls == []


def test_source_collection_skips_candidates_that_already_have_owned_sites(
    tmp_path: Path,
) -> None:
    repo = ProspectRepository(tmp_path / "records")
    source_runs = SourceRunStore(tmp_path / "source-runs")
    connector = FakeSourceConnector(
        [
            ProspectCandidate(
                source="overture",
                source_id="has-site",
                display_name="Already Online Salon",
                formatted_address="30 Pine St, Seattle, WA",
                phone="206-555-0133",
                city_id="seattle",
                genre_id="nail_salon",
                website_uri="https://already-online.example",
            )
        ]
    )

    report = run_source_collection(
        cities=[_city()],
        genres=[_genre()],
        records=repo,
        source_runs=source_runs,
        connector=connector,
        candidates_per_cell=50,
    )

    assert report.candidates_seen == 1
    assert report.records_created == 0
    assert report.present_site_skipped == 1
    assert repo.list() == []


def test_source_collection_keeps_marketplace_website_candidates(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    source_runs = SourceRunStore(tmp_path / "source-runs")
    connector = FakeSourceConnector(
        [
            ProspectCandidate(
                source="overture",
                source_id="booking-only",
                display_name="Booking Only Nails",
                formatted_address="40 Pine St, Seattle, WA",
                phone="206-555-0144",
                city_id="seattle",
                genre_id="nail_salon",
                website_uri="https://www.mytime.com/express_checkout/123",
            )
        ]
    )

    report = run_source_collection(
        cities=[_city()],
        genres=[_genre()],
        records=repo,
        source_runs=source_runs,
        connector=connector,
        candidates_per_cell=50,
    )

    assert report.records_created == 1
    assert report.present_site_skipped == 0
    assert report.marketplace_candidates == 1
    created = repo.get("source/overture:booking-only")
    assert created.maps_website_class is MapsWebsiteClass.MARKETPLACE


def test_source_collection_report_summarizes_cells_and_counts() -> None:
    rendered = render_source_collection_report(
        source="overture",
        tranche="tranche1",
        status="completed",
        cells_total=60,
        cells_processed=60,
        runs_skipped=10,
        candidates_seen=200,
        records_created=40,
        duplicates_skipped=120,
        present_site_skipped=40,
        absent_website_candidates=25,
        social_only_candidates=125,
        marketplace_candidates=50,
        errors=[],
    )

    assert "# Prospect Source Collection Report" in rendered
    assert "| source | overture |" in rendered
    assert "| cells_total | 60 |" in rendered
    assert "| records_created | 40 |" in rendered
    assert "| absent_website_candidates | 25 |" in rendered
    assert "| social_only_candidates | 125 |" in rendered
    assert "| marketplace_candidates | 50 |" in rendered


def _city() -> CityConfig:
    return CityConfig(id="seattle", name="Seattle", lat=47.6062, lng=-122.3321)


def _genre() -> GenreConfig:
    return GenreConfig(id="nail_salon", label="nail salon", text_query_template="{label}")


def _record(place_id: str, *, phone: str) -> ProspectRecord:
    return ProspectRecord(
        place_id=place_id,
        display_name="Existing Shop",
        formatted_address="10 Pine Street, Seattle, WA",
        phone=phone,
        types=["nail_salon"],
        city_id="seattle",
        genre_id="nail_salon",
        grid_cell_id="seattle:nail_salon",
        maps_website_class=MapsWebsiteClass.ABSENT,
    )
