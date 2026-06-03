from __future__ import annotations

from pathlib import Path

import pytest

from packages.prospecting import storage
from packages.prospecting.run import FixturePlacesConnector
from packages.prospecting.storage import (
    FixtureWriteError,
    ProspectRepository,
    is_fixture_record,
)
from packages.schemas.prospect import MapsWebsiteClass, ProspectRecord


def _fixture_record() -> ProspectRecord:
    return FixturePlacesConnector().fetch_details("places/seattle-beauty_salon-1")


def _real_record() -> ProspectRecord:
    return ProspectRecord(
        place_id="places/ChIJreal123",
        display_name="Tonic Salon",
        formatted_address="Seattle, WA",
        phone="+1 206-555-0100",
        types=["beauty_salon"],
        city_id="seattle",
        genre_id="beauty_salon",
        grid_cell_id="seattle:beauty_salon",
        maps_website_class=MapsWebsiteClass.ABSENT,
        user_ratings_total=42,
    )


def test_is_fixture_record_flags_fixture_connector_output() -> None:
    assert is_fixture_record(_fixture_record()) is True
    assert is_fixture_record(_real_record()) is False


def test_production_warehouse_rejects_fixture_records(tmp_path: Path, monkeypatch) -> None:
    prod_root = tmp_path / "records"
    monkeypatch.setattr(storage, "default_records_root", lambda repo_root=None: prod_root)

    repo = ProspectRepository()  # resolves to the (patched) production root

    with pytest.raises(FixtureWriteError):
        repo.save(_fixture_record())
    # The fixture must not have been written.
    assert list(prod_root.glob("*.json")) == []

    # Real records still persist to the production warehouse.
    repo.save(_real_record())
    assert repo.exists("places/ChIJreal123")


def test_non_production_root_allows_fixtures_for_dry_run(tmp_path: Path, monkeypatch) -> None:
    # A different root (dry-run / test) is unaffected by the production guard.
    monkeypatch.setattr(
        storage, "default_records_root", lambda repo_root=None: tmp_path / "prod"
    )
    repo = ProspectRepository(tmp_path / "dry_run" / "records")

    repo.save(_fixture_record())
    assert repo.exists("places/seattle-beauty_salon-1")
