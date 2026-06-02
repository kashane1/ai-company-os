"""JSON persistence for prospect records."""

from __future__ import annotations

from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.db.json_store import JsonStore
from packages.schemas.prospect import ProspectRecord


def default_records_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).state_root / "prospects" / "records"


class ProspectRepository:
    def __init__(self, root: Path | None = None) -> None:
        self._store = JsonStore(root or default_records_root())

    @property
    def root(self) -> Path:
        return self._store.root

    def save(self, record: ProspectRecord) -> ProspectRecord:
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

