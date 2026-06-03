"""JSON persistence for prospect records."""

from __future__ import annotations

from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.db.json_store import JsonStore
from packages.schemas.prospect import ProspectRecord


def default_records_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).state_root / "prospects" / "records"


def dry_run_records_root(repo_root: Path | None = None) -> Path:
    """Isolated warehouse for ``--dry-run`` smoke tests, kept out of production."""
    return load_runtime_paths(repo_root).state_root / "prospects" / "dry_run" / "records"


def is_fixture_record(record: ProspectRecord) -> bool:
    """Synthetic fixtures from ``FixturePlacesConnector`` (dry-run smoke tests).

    These must never inflate the production warehouse. Identified by the
    ``"fixture"`` type tag the connector sets, with a display-name fallback.
    """
    return "fixture" in record.types or record.display_name.startswith("Fixture Local")


class FixtureWriteError(RuntimeError):
    """Raised when a fixture record is sent to the production warehouse."""


class ProspectRepository:
    def __init__(self, root: Path | None = None) -> None:
        self._store = JsonStore(root or default_records_root())

    @property
    def root(self) -> Path:
        return self._store.root

    def _is_production_root(self) -> bool:
        try:
            return self._store.root.resolve() == default_records_root().resolve()
        except OSError:
            return False

    def save(self, record: ProspectRecord) -> ProspectRecord:
        # Guard: synthetic fixtures must never land in the production records
        # warehouse. Test/dry-run repos use a different root and are unaffected.
        if is_fixture_record(record) and self._is_production_root():
            raise FixtureWriteError(
                f"refusing to write fixture record {record.place_id!r} "
                f"({record.display_name!r}) to the production warehouse at "
                f"{self._store.root}; use a dry-run/test records root instead"
            )
        self._store.save(_record_id(record.place_id), record.to_dict())
        return record

    def get(self, place_id: str) -> ProspectRecord:
        return ProspectRecord.from_dict(self._store.load(_record_id(place_id)))

    def exists(self, place_id: str) -> bool:
        return self._store.path_for(_record_id(place_id)).exists()

    def list(self) -> list[ProspectRecord]:
        return [
            ProspectRecord.from_dict(self._store.load(path.stem))
            for path in sorted(self._store.root.glob("*.json"))
        ]


def _record_id(place_id: str) -> str:
    return place_id.rsplit("/", 1)[-1].replace(":", "_")

