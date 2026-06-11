"""Import normalized open-source prospect candidates into the warehouse."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

from packages.config.settings import load_runtime_paths
from packages.prospecting.cohorts import derive_composite_cohort, priority_score
from packages.prospecting.config import CityConfig, GenreConfig
from packages.prospecting.connectors.google_places import (
    MARKETPLACE_HOSTS,
    SOCIAL_HOSTS,
    normalized_host,
)
from packages.prospecting.identity import IdentityIndex, ProspectCandidate
from packages.prospecting.source_runs import SourceRunRecord, SourceRunStore, slug
from packages.prospecting.storage import ProspectRepository
from packages.schemas.prospect import MapsWebsiteClass, ProspectRecord, ProspectStatus


@runtime_checkable
class SourceConnector(Protocol):
    source: str
    connector_version: str

    def query_for(self, city: CityConfig, genre: GenreConfig) -> str:
        ...

    def fetch_candidates(
        self, city: CityConfig, genre: GenreConfig, *, limit: int
    ) -> list[ProspectCandidate]:
        ...


@dataclass(frozen=True)
class SourceCollectionReport:
    source: str
    tranche: str = "custom"
    status: str = "completed"
    cells_total: int = 0
    cells_processed: int = 0
    runs_skipped: int = 0
    candidates_seen: int = 0
    records_created: int = 0
    records_updated: int = 0
    duplicates_skipped: int = 0
    absent_website_candidates: int = 0
    social_only_candidates: int = 0
    marketplace_candidates: int = 0
    present_site_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    report_path: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_source_collection(
    *,
    cities: list[CityConfig],
    genres: list[GenreConfig],
    records: ProspectRepository,
    source_runs: SourceRunStore,
    connector: SourceConnector,
    candidates_per_cell: int,
    selected_city_ids: list[str] | None = None,
    selected_genre_ids: list[str] | None = None,
    force: bool = False,
    include_present_sites: bool = False,
    tranche: str = "custom",
    now: Callable[[], datetime] | None = None,
) -> SourceCollectionReport:
    clock = now or (lambda: datetime.now(timezone.utc))
    started = clock().isoformat()
    target_cities = _select_cities(cities, selected_city_ids)
    target_genres = _select_genres(genres, selected_genre_ids)
    cells_total = len(target_cities) * len(target_genres)
    index = IdentityIndex.from_records(records.list())

    cells_processed = 0
    runs_skipped = 0
    candidates_seen = 0
    records_created = 0
    records_updated = 0
    duplicates_skipped = 0
    absent_website_candidates = 0
    social_only_candidates = 0
    marketplace_candidates = 0
    present_site_skipped = 0
    errors: list[str] = []

    for city in target_cities:
        for genre in target_genres:
            query = connector.query_for(city, genre)
            if (
                not force
                and source_runs.has_completed(
                    source=connector.source,
                    city_id=city.id,
                    genre_id=genre.id,
                    query=query,
                    connector_version=connector.connector_version,
                )
            ):
                runs_skipped += 1
                continue

            run_started = clock().isoformat()
            run_key = SourceRunRecord(
                source=connector.source,
                city_id=city.id,
                genre_id=genre.id,
                query=query,
                connector_version=connector.connector_version,
                status="running",
            ).run_key

            run_seen = 0
            run_created = 0
            run_updated = 0
            run_duplicates = 0
            run_absent_website = 0
            run_social_only = 0
            run_marketplace = 0
            run_present_site_skipped = 0

            try:
                candidates = connector.fetch_candidates(
                    city, genre, limit=max(candidates_per_cell, 0)
                )
            except Exception as exc:  # noqa: BLE001 - keep batch collection going
                errors.append(f"{city.id}:{genre.id}: {exc}")
                source_runs.save(
                    SourceRunRecord(
                        source=connector.source,
                        city_id=city.id,
                        genre_id=genre.id,
                        query=query,
                        connector_version=connector.connector_version,
                        status="error",
                        started_at=run_started,
                        finished_at=clock().isoformat(),
                        last_error=str(exc),
                    )
                )
                continue

            for candidate in candidates:
                run_seen += 1
                candidates_seen += 1

                website_class = website_class_for_candidate(candidate)
                if website_class is MapsWebsiteClass.ABSENT:
                    run_absent_website += 1
                    absent_website_candidates += 1
                elif website_class is MapsWebsiteClass.SOCIAL_ONLY:
                    run_social_only += 1
                    social_only_candidates += 1
                elif website_class is MapsWebsiteClass.MARKETPLACE:
                    run_marketplace += 1
                    marketplace_candidates += 1
                if website_class is MapsWebsiteClass.PRESENT and not include_present_sites:
                    run_present_site_skipped += 1
                    present_site_skipped += 1
                    continue

                match = index.match(candidate)
                if match is not None:
                    run_duplicates += 1
                    duplicates_skipped += 1
                    continue

                record = source_candidate_to_record(
                    candidate,
                    run_key=run_key,
                    query=query,
                    collected_at=clock().isoformat(),
                )
                records.save(record)
                index.add_record(record)
                run_created += 1
                records_created += 1

            cells_processed += 1
            source_runs.save(
                SourceRunRecord(
                    source=connector.source,
                    city_id=city.id,
                    genre_id=genre.id,
                    query=query,
                    connector_version=connector.connector_version,
                    status="completed",
                    candidates_seen=run_seen,
                    records_created=run_created,
                    records_updated=run_updated,
                    duplicates_skipped=run_duplicates,
                    absent_website_candidates=run_absent_website,
                    social_only_candidates=run_social_only,
                    marketplace_candidates=run_marketplace,
                    present_site_skipped=run_present_site_skipped,
                    started_at=run_started,
                    finished_at=clock().isoformat(),
                )
            )

    status = "completed" if not errors else "completed_with_errors"
    return SourceCollectionReport(
        source=connector.source,
        tranche=tranche,
        status=status,
        cells_total=cells_total,
        cells_processed=cells_processed,
        runs_skipped=runs_skipped,
        candidates_seen=candidates_seen,
        records_created=records_created,
        records_updated=records_updated,
        duplicates_skipped=duplicates_skipped,
        absent_website_candidates=absent_website_candidates,
        social_only_candidates=social_only_candidates,
        marketplace_candidates=marketplace_candidates,
        present_site_skipped=present_site_skipped,
        errors=errors,
        started_at=started,
        finished_at=clock().isoformat(),
    )


def source_candidate_to_record(
    candidate: ProspectCandidate,
    *,
    run_key: str,
    query: str,
    collected_at: str,
) -> ProspectRecord:
    website_class = website_class_for_candidate(candidate)
    website = candidate.website_uri
    if not website and candidate.social_urls:
        website = candidate.social_urls[0]
    if not website and candidate.marketplace_urls:
        website = candidate.marketplace_urls[0]
    host = normalized_host(website)
    record = ProspectRecord(
        place_id=source_place_id(candidate.source, candidate.source_id),
        display_name=candidate.display_name,
        formatted_address=candidate.formatted_address,
        phone=candidate.phone,
        types=[candidate.source, candidate.genre_id],
        city_id=candidate.city_id,
        genre_id=candidate.genre_id,
        grid_cell_id=f"{candidate.city_id}:{candidate.genre_id}",
        maps_website_uri=website,
        maps_website_host=host,
        maps_website_class=website_class,
        source_name=candidate.source,
        source_record_id=candidate.source_id,
        source_run_key=run_key,
        source_query=query,
        source_confidence=candidate.source_confidence,
        source_collected_at=collected_at,
        status=ProspectStatus.SOURCE_ENRICHED,
        created_at=collected_at,
        updated_at=collected_at,
    )
    cohort = derive_composite_cohort(record)
    return ProspectRecord.from_dict(
        {
            **record.to_dict(),
            "composite_cohort": cohort,
            "priority_score": priority_score(record, cohort),
        }
    )


def website_class_for_candidate(candidate: ProspectCandidate) -> MapsWebsiteClass:
    if candidate.website_uri:
        host = normalized_host(candidate.website_uri)
        if _host_in(host, SOCIAL_HOSTS):
            return MapsWebsiteClass.SOCIAL_ONLY
        if _host_in(host, MARKETPLACE_HOSTS):
            return MapsWebsiteClass.MARKETPLACE
        return MapsWebsiteClass.PRESENT
    if candidate.social_urls:
        return MapsWebsiteClass.SOCIAL_ONLY
    if candidate.marketplace_urls:
        return MapsWebsiteClass.MARKETPLACE
    return MapsWebsiteClass.ABSENT


def source_place_id(source: str, source_id: str) -> str:
    return f"source/{slug(source)}:{slug(source_id)}"


def default_source_collection_report_path(
    *, source: str, tranche: str, now: datetime | None = None
) -> Path:
    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return (
        load_runtime_paths().artifacts_root
        / "prospecting"
        / f"source-collection-{slug(source)}-{slug(tranche)}-{timestamp}.md"
    )


def write_source_collection_report(
    report: SourceCollectionReport, path: Path | None = None
) -> Path:
    target = path or default_source_collection_report_path(
        source=report.source, tranche=report.tranche
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_source_collection_report(**report.to_dict()))
    return target


def render_source_collection_report(
    *,
    source: str,
    tranche: str,
    status: str,
    cells_total: int,
    cells_processed: int,
    runs_skipped: int,
    candidates_seen: int,
    records_created: int,
    duplicates_skipped: int,
    absent_website_candidates: int,
    social_only_candidates: int,
    marketplace_candidates: int,
    present_site_skipped: int,
    errors: list[str],
    records_updated: int = 0,
    started_at: str = "",
    finished_at: str = "",
    report_path: str = "",
) -> str:
    lines = [
        "# Prospect Source Collection Report",
        "",
        "| field | value |",
        "|---|---:|",
        f"| source | {source} |",
        f"| tranche | {tranche} |",
        f"| status | {status} |",
        f"| cells_total | {cells_total} |",
        f"| cells_processed | {cells_processed} |",
        f"| runs_skipped | {runs_skipped} |",
        f"| candidates_seen | {candidates_seen} |",
        f"| records_created | {records_created} |",
        f"| records_updated | {records_updated} |",
        f"| duplicates_skipped | {duplicates_skipped} |",
        f"| absent_website_candidates | {absent_website_candidates} |",
        f"| social_only_candidates | {social_only_candidates} |",
        f"| marketplace_candidates | {marketplace_candidates} |",
        f"| present_site_skipped | {present_site_skipped} |",
    ]
    if started_at or finished_at:
        lines.extend(
            [
                f"| started_at | {started_at} |",
                f"| finished_at | {finished_at} |",
            ]
        )
    lines.extend(["", "## Errors", ""])
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("none")
    return "\n".join(lines) + "\n"


def _select_cities(cities: list[CityConfig], selected: list[str] | None) -> list[CityConfig]:
    if not selected:
        return cities
    wanted = set(selected)
    return [city for city in cities if city.id in wanted]


def _select_genres(genres: list[GenreConfig], selected: list[str] | None) -> list[GenreConfig]:
    enabled = [genre for genre in genres if genre.enabled]
    if not selected:
        return enabled
    wanted = set(selected)
    return [genre for genre in enabled if genre.id in wanted]


def _host_in(host: str, hosts: set[str]) -> bool:
    return any(host == candidate or host.endswith(f".{candidate}") for candidate in hosts)
