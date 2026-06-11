"""Run controller for Phase 1 prospecting."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

import httpx

from packages.config.settings import load_runtime_paths
from packages.db.json_store import JsonStore
from packages.policies.discovery_gates import assert_bulk_crawl_allowed
from packages.prospecting.cohorts import derive_composite_cohort, priority_score
from packages.prospecting.config import CityConfig, GenreConfig, WeeklyCaps
from packages.prospecting.grid import GridCursorStore, build_grid, select_cells
from packages.prospecting.http_check import HTTPChecker, should_check_http
from packages.prospecting.storage import ProspectRepository
from packages.schemas.prospect import (
    HttpCheck,
    HttpCheckClass,
    ProspectRecord,
    ProspectStatus,
    replace_record,
)

STOP_FILE_NAME = "STOP"
CURRENT_RUN_ID = "current"


@runtime_checkable
class PlacesClient(Protocol):
    def search_cell(self, city: CityConfig, genre: GenreConfig, *, limit: int) -> list[str]:
        ...

    def fetch_details(self, place_id: str) -> ProspectRecord:
        ...


@runtime_checkable
class HTTPCheckClient(Protocol):
    def check(self, url: str) -> HttpCheck:
        ...


@dataclass(frozen=True)
class ProspectRunReport:
    run_id: str
    status: str
    cells_done: int = 0
    places_seen: int = 0
    records_created: int = 0
    records_updated: int = 0
    api_errors: list[str] = field(default_factory=list)
    http_counts: dict[str, int] = field(default_factory=dict)
    cap_headroom: dict[str, int] = field(default_factory=dict)
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ProspectRunReport":
        return cls(
            run_id=str(payload["run_id"]),
            status=str(payload["status"]),
            cells_done=int(payload.get("cells_done", 0)),
            places_seen=int(payload.get("places_seen", 0)),
            records_created=int(payload.get("records_created", 0)),
            records_updated=int(payload.get("records_updated", 0)),
            api_errors=[str(item) for item in list(payload.get("api_errors", []))],
            http_counts={str(k): int(v) for k, v in dict(payload.get("http_counts", {})).items()},
            cap_headroom={str(k): int(v) for k, v in dict(payload.get("cap_headroom", {})).items()},
            started_at=str(payload.get("started_at", "")),
            finished_at=str(payload.get("finished_at", "")),
        )


def run_prospecting(
    *,
    cities: list[CityConfig],
    genres: list[GenreConfig],
    cells_limit: int,
    records: ProspectRepository,
    places: PlacesClient,
    http_checker: HTTPCheckClient,
    weekly_caps: WeeklyCaps,
    cursor_store: GridCursorStore | None = None,
    should_stop: Callable[[], bool] | None = None,
    now: Callable[[], datetime] | None = None,
    run_id: str | None = None,
    selected_cells: list[str] | None = None,
    approved_by: str | None = None,
    bulk: bool = False,
    dry_run: bool = False,
    places_per_cell: int = 20,
) -> ProspectRunReport:
    if bulk:
        assert_bulk_crawl_allowed(
            approved_by=approved_by, robots_checked=True, rate_limited=True
        )

    clock = now or (lambda: datetime.now(timezone.utc))
    stop = should_stop or (lambda: False)
    started = clock().isoformat()
    rid = run_id or f"run_{uuid.uuid4().hex[:12]}"
    cursor = None if selected_cells else (cursor_store or GridCursorStore()).load()
    cells = select_cells(
        build_grid(cities, genres),
        cursor=cursor,
        limit=cells_limit,
        selected_cells=selected_cells,
    )

    text_search_used = 0
    details_used = 0
    http_used = 0
    cells_done = 0
    places_seen = 0
    records_created = 0
    records_updated = 0
    api_errors: list[str] = []
    http_counts: dict[str, int] = {}
    status = "completed"

    for cell in cells:
        if stop():
            status = "stopped"
            break
        if text_search_used >= weekly_caps.text_search_requests:
            status = "cap_hit"
            break
        try:
            place_ids = places.search_cell(cell.city, cell.genre, limit=places_per_cell)
            text_search_used += 1
        except Exception as exc:  # noqa: BLE001 - cell errors should not kill the run
            api_errors.append(f"{cell.id}: search: {exc}")
            continue

        for place_id in place_ids:
            if details_used >= weekly_caps.place_details_essentials:
                status = "cap_hit"
                break
            places_seen += 1
            exists = records.exists(place_id)
            try:
                record = places.fetch_details(place_id)
                details_used += 1
                record = _prepare_record(record, cell.city.id, cell.genre.id, cell.id, clock)
                if should_check_http(record):
                    if http_used >= weekly_caps.http_checks:
                        status = "cap_hit"
                    elif record.maps_website_uri:
                        check = http_checker.check(record.maps_website_uri)
                        http_used += 1
                        http_counts[check.http_check_class.value] = (
                            http_counts.get(check.http_check_class.value, 0) + 1
                        )
                        record = _apply_http(record, check, clock)
                    else:
                        http_counts[HttpCheckClass.SKIPPED.value] = (
                            http_counts.get(HttpCheckClass.SKIPPED.value, 0) + 1
                        )
                        record = replace_record(
                            record,
                            http_skip_reason="maps_website_uri_absent",
                            updated_at=clock().isoformat(),
                        )
                else:
                    record = replace_record(
                        record,
                        http_skip_reason="present_site_not_in_deterministic_sample",
                        updated_at=clock().isoformat(),
                    )
                record = _derive(record, clock)
                records.save(record)
                if exists:
                    records_updated += 1
                else:
                    records_created += 1
            except Exception as exc:  # noqa: BLE001
                api_errors.append(f"{cell.id}: details {place_id}: {exc}")
        cells_done += 1
        if cursor_store is not None and not selected_cells and status == "completed":
            cursor_store.mark_completed(cell.id)
        if status == "cap_hit":
            break

    return ProspectRunReport(
        run_id=rid,
        status=("error" if status == "completed" and api_errors and cells_done == 0 else status),
        cells_done=cells_done,
        places_seen=places_seen,
        records_created=records_created,
        records_updated=records_updated,
        api_errors=api_errors,
        http_counts=http_counts,
        cap_headroom={
            "text_search_requests": weekly_caps.text_search_requests - text_search_used,
            "place_details_essentials": weekly_caps.place_details_essentials - details_used,
            "http_checks": weekly_caps.http_checks - http_used,
            "place_details_pro_reviews": weekly_caps.place_details_pro_reviews,
            "google_search_verifications": weekly_caps.google_search_verifications,
        },
        started_at=started,
        finished_at=clock().isoformat(),
    )


def _prepare_record(
    record: ProspectRecord,
    city_id: str,
    genre_id: str,
    grid_cell_id: str,
    clock: Callable[[], datetime],
) -> ProspectRecord:
    timestamp = clock().isoformat()
    created = record.created_at or timestamp
    return replace_record(
        record,
        city_id=city_id,
        genre_id=genre_id,
        grid_cell_id=grid_cell_id,
        status=ProspectStatus.MAPS_ENRICHED.value,
        created_at=created,
        updated_at=timestamp,
    )


def _apply_http(
    record: ProspectRecord, check: HttpCheck, clock: Callable[[], datetime]
) -> ProspectRecord:
    return replace_record(
        record,
        http_check_class=check.http_check_class.value,
        http_final_url=check.final_url,
        http_status=check.status,
        http_checked_at=check.checked_at,
        status=ProspectStatus.HTTP_ENRICHED.value,
        updated_at=clock().isoformat(),
        last_error=check.error,
    )


def _derive(record: ProspectRecord, clock: Callable[[], datetime]) -> ProspectRecord:
    cohort = derive_composite_cohort(record)
    return replace_record(
        record,
        composite_cohort=cohort,
        priority_score=priority_score(record, cohort),
        updated_at=clock().isoformat(),
    )


def default_runs_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).state_root / "prospects" / "runs"


class ProspectRunStore:
    def __init__(self, root: Path | None = None) -> None:
        self._store = JsonStore(root or default_runs_root())

    def save(self, report: ProspectRunReport) -> ProspectRunReport:
        self._store.save(report.run_id, report.to_dict())
        self._store.save(CURRENT_RUN_ID, report.to_dict())
        return report

    def latest(self) -> ProspectRunReport | None:
        path = self._store.path_for(CURRENT_RUN_ID)
        if not path.exists():
            return None
        return ProspectRunReport.from_dict(self._store.load(CURRENT_RUN_ID))


class FileStopSignal:
    def __init__(self, root: Path | None = None) -> None:
        self._path = (root or default_runs_root()) / STOP_FILE_NAME

    def request(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text("stop\n")

    def clear(self) -> None:
        self._path.unlink(missing_ok=True)

    def requested(self) -> bool:
        return self._path.exists()

    def __call__(self) -> bool:
        return self.requested()


class FixturePlacesConnector:
    def search_cell(self, city: CityConfig, genre: GenreConfig, *, limit: int) -> list[str]:
        return [f"places/{city.id}-{genre.id}-{i}" for i in range(1, min(limit, 3) + 1)]

    def fetch_details(self, place_id: str) -> ProspectRecord:
        suffix = place_id.rsplit("-", 1)[-1]
        if suffix == "1":
            website = ""
            maps_class = "absent"
            host = ""
            reviews = 37
        elif suffix == "2":
            website = "https://facebook.com/localfixture"
            maps_class = "social_only"
            host = "facebook.com"
            reviews = 42
        else:
            website = "https://example.com/localfixture"
            maps_class = "present"
            host = "example.com"
            reviews = 12
        return ProspectRecord.from_dict(
            {
                "place_id": place_id,
                "display_name": f"Fixture Local {suffix}",
                "formatted_address": "Seattle, WA",
                "phone": "+1 206-555-0100",
                "types": ["fixture"],
                "city_id": "",
                "genre_id": "",
                "grid_cell_id": "",
                "maps_website_uri": website,
                "maps_website_host": host,
                "maps_website_class": maps_class,
                "rating": 4.6,
                "user_ratings_total": reviews,
            }
        )


def fixture_http_checker() -> HTTPChecker:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "facebook.com":
            return httpx.Response(200, request=request)
        return httpx.Response(200, text="owned site", request=request)

    return HTTPChecker(client=httpx.Client(transport=httpx.MockTransport(handler)))
