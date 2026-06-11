"""Source-run ledger for idempotent prospect collection."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from packages.config.settings import load_runtime_paths


@dataclass(frozen=True)
class SourceRunRecord:
    source: str
    city_id: str
    genre_id: str
    query: str
    connector_version: str
    status: str
    candidates_seen: int = 0
    records_created: int = 0
    records_updated: int = 0
    duplicates_skipped: int = 0
    absent_website_candidates: int = 0
    social_only_candidates: int = 0
    marketplace_candidates: int = 0
    present_site_skipped: int = 0
    started_at: str = ""
    finished_at: str = ""
    last_error: str = ""

    @property
    def query_hash(self) -> str:
        digest = hashlib.sha1(normalize_query(self.query).encode("utf-8")).hexdigest()
        return digest[:12]

    @property
    def run_key(self) -> str:
        return "__".join(
            [
                slug(self.source),
                slug(self.city_id),
                slug(self.genre_id),
                slug(self.connector_version),
                self.query_hash,
            ]
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["query_hash"] = self.query_hash
        payload["run_key"] = self.run_key
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "SourceRunRecord":
        return cls(
            source=str(payload["source"]),
            city_id=str(payload["city_id"]),
            genre_id=str(payload["genre_id"]),
            query=str(payload["query"]),
            connector_version=str(payload["connector_version"]),
            status=str(payload["status"]),
            candidates_seen=int(payload.get("candidates_seen", 0) or 0),
            records_created=int(payload.get("records_created", 0) or 0),
            records_updated=int(payload.get("records_updated", 0) or 0),
            duplicates_skipped=int(payload.get("duplicates_skipped", 0) or 0),
            absent_website_candidates=int(
                payload.get("absent_website_candidates", 0) or 0
            ),
            social_only_candidates=int(payload.get("social_only_candidates", 0) or 0),
            marketplace_candidates=int(payload.get("marketplace_candidates", 0) or 0),
            present_site_skipped=int(payload.get("present_site_skipped", 0) or 0),
            started_at=str(payload.get("started_at", "")),
            finished_at=str(payload.get("finished_at", "")),
            last_error=str(payload.get("last_error", "")),
        )


def default_source_runs_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).state_root / "prospects" / "source-runs"


class SourceRunStore:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or default_source_runs_root()

    def save(self, record: SourceRunRecord) -> SourceRunRecord:
        path = self.path_for(record)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True))
        return record

    def has_completed(
        self,
        *,
        source: str,
        city_id: str,
        genre_id: str,
        query: str,
        connector_version: str,
    ) -> bool:
        record = SourceRunRecord(
            source=source,
            city_id=city_id,
            genre_id=genre_id,
            query=query,
            connector_version=connector_version,
            status="completed",
        )
        path = self.path_for(record)
        if not path.exists():
            return False
        return SourceRunRecord.from_dict(json.loads(path.read_text())).status == "completed"

    def latest_for_cell(
        self, source: str, city_id: str, genre_id: str
    ) -> SourceRunRecord | None:
        root = self._root / slug(source)
        matches = [
            SourceRunRecord.from_dict(json.loads(path.read_text()))
            for path in root.glob("*.json")
        ]
        matches = [
            record
            for record in matches
            if record.city_id == city_id and record.genre_id == genre_id
        ]
        if not matches:
            return None
        return sorted(matches, key=lambda record: record.finished_at or record.started_at)[-1]

    def path_for(self, record: SourceRunRecord) -> Path:
        return self._root / slug(record.source) / f"{record.run_key}.json"


def normalize_query(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower())
    return cleaned.strip("-") or "unknown"
