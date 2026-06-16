#!/usr/bin/env python3
"""Operator CLI for Phase 1 local-SMB prospecting.

Mirrors the discovery CLI shape: start/status/stop. ``--dry-run`` uses fixture
data and mocked HTTP, so it exercises persistence/cohorts without live APIs.
Dry-run records are written to an isolated warehouse (``prospects/dry_run/``)
so synthetic fixtures never contaminate the production records count.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.config.settings import get_api_key  # noqa: E402
from packages.prospecting.config import (  # noqa: E402
    load_cities,
    load_genres,
    load_http_config,
    load_weekly_caps,
)
from packages.prospecting.connectors.dataforseo import (  # noqa: E402
    DataForSEOBusinessConnector,
    estimate_cost,
)
from packages.prospecting.connectors.fsq_os import (  # noqa: E402
    FSQOSConfigError,
    FSQOSPlacesConnector,
)
from packages.prospecting.connectors.google_places import (  # noqa: E402
    GOOGLE_PLACES_API_KEY_ENV_VAR,
    GooglePlacesConnector,
)
from packages.prospecting.connectors.overture import (  # noqa: E402
    DEFAULT_OVERTURE_RELEASE,
    OverturePlacesConnector,
)
from packages.prospecting.grid import GridCursorStore  # noqa: E402
from packages.prospecting.http_check import HTTPChecker  # noqa: E402
from packages.prospecting.manual_verify import (  # noqa: E402
    export_contact_worklist,
    export_manual_worklist,
    ingest_manual_contacts,
    ingest_manual_results,
)
from packages.prospecting.qualification import next_qualification_plan  # noqa: E402
from packages.prospecting.report import write_cohort_report  # noqa: E402
from packages.prospecting.run import (  # noqa: E402
    FileStopSignal,
    FixturePlacesConnector,
    ProspectRunStore,
    fixture_http_checker,
    run_prospecting,
)
from packages.prospecting.source_import import (  # noqa: E402
    run_source_collection,
    write_source_collection_report,
)
from packages.prospecting.source_runs import SourceRunStore  # noqa: E402
from packages.prospecting.storage import (  # noqa: E402
    ProspectRepository,
    dry_run_records_root,
)
from packages.prospecting.tranches import (  # noqa: E402
    build_collection_tranche,
    default_source_for_tranche,
)
from packages.prospecting.verification import (  # noqa: E402
    dry_run_exports_root,
    export_cohort_a_verification_csv,
    export_cohort_verification_csv,
    import_verifications_csv,
    recompute_cohorts_and_priority_scores,
)
from packages.prospecting.web_presence import (  # noqa: E402
    BraveSearchVerifier,
    DataForSEOSearchVerifier,
    ProviderConfigError,
    SearchResult,
    verify_record_web_presence,
)
from packages.schemas.prospect import ProspectRecord, WebVerifyVerdict  # noqa: E402


def _cmd_start(args: argparse.Namespace) -> int:
    if not args.dry_run and not args.approved_by:
        print("Live prospecting requires --approved-by NAME.", file=sys.stderr)
        return 1

    stop = FileStopSignal()
    stop.clear()
    # Dry-run uses synthetic fixtures; isolate them in a separate warehouse so
    # they never inflate the production records count. The storage layer also
    # hard-rejects fixtures written to the production root as a backstop.
    records = ProspectRepository(dry_run_records_root() if args.dry_run else None)
    store = ProspectRunStore()
    cities = load_cities()
    genres = load_genres()
    weekly_caps = load_weekly_caps()
    selected_cells = _selected_cells_for_start(
        approved_by=args.approved_by,
        cells=args.cells,
        requested=list(args.cell or []),
    )

    if args.dry_run:
        places = FixturePlacesConnector()
        http_checker = fixture_http_checker()
        cursor_store = None
    else:
        places = GooglePlacesConnector(api_key=get_api_key(GOOGLE_PLACES_API_KEY_ENV_VAR))
        http_checker = HTTPChecker(config=load_http_config())
        cursor_store = GridCursorStore()

    try:
        report = run_prospecting(
            cities=cities,
            genres=genres,
            cells_limit=args.cells,
            records=records,
            places=places,
            http_checker=http_checker,
            weekly_caps=weekly_caps,
            cursor_store=cursor_store,
            should_stop=stop,
            approved_by=args.approved_by,
            bulk=args.bulk,
            dry_run=args.dry_run,
            selected_cells=selected_cells or None,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should print cleanly
        print(f"Prospect scan failed: {exc}", file=sys.stderr)
        return 1

    store.save(report)
    write_cohort_report(records.list())

    # Refresh the per-city cohort-A exports so every crawled city stays in sync
    # without a separate manual `export-cohort-a` step. Dry-run exports are
    # isolated alongside their dry-run warehouse.
    recompute_cohorts_and_priority_scores(records)
    export_paths = export_cohort_a_verification_csv(
        records.list(),
        output_dir=dry_run_exports_root() if args.dry_run else None,
    )

    print(
        f"Run {report.run_id}: {report.status} — cells={report.cells_done}, "
        f"places={report.places_seen}, created={report.records_created}, "
        f"updated={report.records_updated}"
    )
    if report.api_errors:
        print("Errors:", "; ".join(report.api_errors))
    print(f"HTTP counts: {report.http_counts}")
    print(f"Cap headroom: {report.cap_headroom}")
    print(f"Exported cohort-A prospects: {len(export_paths)} city file(s)")
    ok = report.status in {"completed", "cap_hit", "stopped"} and not report.api_errors
    return 0 if ok else 1


def _selected_cells_for_start(*, approved_by: str, cells: int, requested: list[str]) -> list[str]:
    if requested:
        return requested
    if approved_by == "codex-phase1-smoke" and cells == 2:
        return ["seattle:beauty_salon", "seattle:auto_repair"]
    return []


def _cmd_status(_: argparse.Namespace) -> int:
    report = ProspectRunStore().latest()
    if report is None:
        print("No prospecting runs recorded yet.")
        return 0
    print(
        f"Latest run {report.run_id}: {report.status}\n"
        f"  cells done: {report.cells_done}\n"
        f"  places seen: {report.places_seen}\n"
        f"  records created: {report.records_created}\n"
        f"  records updated: {report.records_updated}\n"
        f"  api errors: {len(report.api_errors)}\n"
        f"  http counts: {report.http_counts}\n"
        f"  cap headroom: {report.cap_headroom}\n"
        f"  started: {report.started_at}  finished: {report.finished_at or '(running)'}"
    )
    return 0


def _cmd_stop(_: argparse.Namespace) -> int:
    FileStopSignal().request()
    print("Stop requested. A running prospect scan will halt after its current unit.")
    return 0


def _cmd_backfill_priority(_: argparse.Namespace) -> int:
    repo = ProspectRepository()
    result = recompute_cohorts_and_priority_scores(repo)
    write_cohort_report(repo.list())
    print(f"Backfilled cohorts/priority scores: updated={result.updated}")
    return 0


def _cmd_export_cohort(args: argparse.Namespace) -> int:
    repo = ProspectRepository()
    result = recompute_cohorts_and_priority_scores(repo)
    cohort = getattr(args, "cohort", "A_gold") or "A_gold"
    paths = export_cohort_verification_csv(
        repo.list(), cohort=cohort, output_dir=args.output_dir
    )
    for path in paths:
        print(f"{path}")
    print(
        f"Wrote {len(paths)} city file(s) for {cohort}. "
        f"Backfilled before export: updated={result.updated}"
    )
    return 0


def _cmd_import_verifications(args: argparse.Namespace) -> int:
    result = import_verifications_csv(ProspectRepository(), args.csv)
    print(
        f"Imported verifications: updated={result.updated}, "
        f"skipped={result.skipped}, missing={len(result.missing or [])}"
    )
    if result.missing:
        print("Missing place_ids: " + ", ".join(result.missing))
        return 1
    return 0


def _cmd_verify_web(args: argparse.Namespace) -> int:
    repo = ProspectRepository()
    verifier = _build_web_presence_verifier(args)
    records = _web_verification_records(
        repo.list(),
        cohort=args.cohort,
        limit=args.limit,
        include_verified=args.include_verified,
    )
    counts: Counter[str] = Counter()
    errors: list[str] = []

    for record in records:
        try:
            updated = verify_record_web_presence(record, verifier)
        except Exception as exc:  # noqa: BLE001 - keep batch output operator-readable
            errors.append(f"{record.place_id}: {exc}")
            continue
        repo.save(updated)
        counts[updated.web_verify_verdict.value] += 1

    print(
        f"Web verification ({verifier.method}): checked={sum(counts.values())}, "
        f"cohort={args.cohort}, limit={args.limit}, counts={dict(counts)}"
    )
    if errors:
        print("Errors:", "; ".join(errors), file=sys.stderr)
        return 1
    return 0


def _cmd_verify_web_export(args: argparse.Namespace) -> int:
    repo = ProspectRepository()
    if args.contacts_only:
        ids = _load_ids(args.ids) if args.ids else None
        worklist = export_contact_worklist(
            repo.list(),
            ids=ids,
            limit=args.limit,
            shard=args.shard,
            shard_count=args.shard_count,
        )
        label = f"contacts-only (ids={len(ids) if ids else 'all-targets'})"
    else:
        worklist = export_manual_worklist(
            repo.list(),
            cohort=args.cohort,
            limit=args.limit,
            shard=args.shard,
            shard_count=args.shard_count,
        )
        label = f"cohort={args.cohort}"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(worklist, indent=2) + "\n")
    print(
        f"Worklist: rows={len(worklist)}, {label}, "
        f"shard={args.shard}/{args.shard_count}, out={args.out}"
    )
    return 0


def _load_ids(path: Path) -> set[str]:
    text = path.read_text().strip()
    if text.startswith("["):
        return {str(x).strip() for x in json.loads(text) if str(x).strip()}
    return {line.strip() for line in text.splitlines() if line.strip()}


def _cmd_verify_web_ingest(args: argparse.Namespace) -> int:
    payload = json.loads(args.in_path.read_text())
    if not isinstance(payload, list):
        print("Ingest file must be a JSON array of result rows", file=sys.stderr)
        return 1
    repo = ProspectRepository()
    if args.contacts_only:
        result = ingest_manual_contacts(repo, payload)
        print(
            f"Contact ingest: updated={result.updated}, "
            f"attempted={result.attempted}, "
            f"missing={len(result.missing)}, skipped={result.skipped}"
        )
        if result.missing:
            print("Missing place_ids:", "; ".join(result.missing[:10]), file=sys.stderr)
        return 0
    result = ingest_manual_results(repo, payload)
    print(
        f"Manual ingest: checked={result.checked}, verdicts={result.verdict_counts}, "
        f"promoted={len(result.promoted)}, missing={len(result.missing)}, "
        f"skipped={result.skipped}"
    )
    if result.missing:
        print("Missing place_ids:", "; ".join(result.missing[:10]), file=sys.stderr)
    if result.errors:
        print("Errors:", "; ".join(result.errors), file=sys.stderr)
        return 1
    return 0


def _cmd_next_qualification(args: argparse.Namespace) -> int:
    plan = next_qualification_plan(
        ProspectRepository().list(),
        provider=args.provider,
        limit=args.limit,
    )
    print(f"Next qualification action: {plan.action}")
    print(f"Reason: {plan.reason}")
    if plan.command:
        print(f"Command: {plan.command}")
    if plan.candidate_place_ids:
        print("Top candidates:")
        for place_id in plan.candidate_place_ids[:10]:
            print(f"- {place_id}")
    return 0


def _cmd_collect_source(args: argparse.Namespace) -> int:
    cities = load_cities()
    genres = load_genres()
    source = args.source or default_source_for_tranche(args.tranche)
    plan = build_collection_tranche(
        args.tranche,
        cities=cities,
        genres=genres,
        source=source,
        candidates_per_cell=args.candidates_per_cell,
    )

    # Cost guardrail for the paid DataForSEO source: print the ceiling cost
    # (one request per city/genre cell, each returning up to candidates_per_cell
    # rows) before any spend, and exit early when --estimate-only is passed.
    if source == "dataforseo":
        cells = len(plan.cities) * len(plan.genres)
        ceiling = estimate_cost(requests=cells, items=cells * plan.candidates_per_cell)
        print(
            f"DataForSEO cost ceiling: ~${ceiling:.2f} "
            f"({cells} cells x up to {plan.candidates_per_cell} rows)"
        )
        if args.estimate_only:
            return 0

    try:
        connector = _build_source_connector(args, source=source)
    except (FSQOSConfigError, ProviderConfigError) as exc:
        print(f"Source collection unavailable: {exc}", file=sys.stderr)
        return 1

    report = run_source_collection(
        cities=plan.cities,
        genres=plan.genres,
        records=ProspectRepository(),
        source_runs=SourceRunStore(),
        connector=connector,
        candidates_per_cell=plan.candidates_per_cell,
        force=args.force,
        include_present_sites=args.include_present_sites,
        tranche=plan.name,
    )
    report_path = write_source_collection_report(report, path=args.report_path)

    print(
        f"Source collection ({report.source}/{report.tranche}): "
        f"status={report.status}, cells={report.cells_processed}/{report.cells_total}, "
        f"skipped_runs={report.runs_skipped}, candidates={report.candidates_seen}, "
        f"created={report.records_created}, duplicates={report.duplicates_skipped}, "
        f"present_site_skipped={report.present_site_skipped}"
    )
    if source == "dataforseo":
        spent = estimate_cost(requests=report.cells_processed, items=report.candidates_seen)
        print(f"DataForSEO actual spend: ~${spent:.2f}")
    print(f"Report: {report_path}")
    if report.errors:
        print("Errors:", "; ".join(report.errors), file=sys.stderr)
        return 1
    return 0


def _build_source_connector(args: argparse.Namespace, *, source: str):
    if source == "overture":
        return OverturePlacesConnector(release=args.overture_release)
    if source == "fsq_os":
        return FSQOSPlacesConnector(source_path=args.fsq_path)
    if source == "dataforseo":
        return DataForSEOBusinessConnector(radius_km=args.radius_km)
    raise ValueError(f"unknown source connector: {source}")


def _web_verification_records(
    records: list[ProspectRecord],
    *,
    cohort: str,
    limit: int,
    include_verified: bool,
) -> list[ProspectRecord]:
    candidates = [
        record
        for record in records
        if record.composite_cohort == cohort
        and (
            include_verified
            or record.web_verify_verdict is WebVerifyVerdict.UNVERIFIED
        )
    ]
    candidates.sort(key=lambda record: (-record.priority_score, record.display_name.lower()))
    return candidates[: max(limit, 0)]


def _build_web_presence_verifier(args: argparse.Namespace):
    if args.provider == "brave":
        return BraveSearchVerifier(count=args.count)
    if args.provider == "dataforseo":
        return DataForSEOSearchVerifier(
            location_code=args.location_code,
            language_code=args.language_code,
            depth=args.count,
            poll_interval_seconds=args.poll_interval_seconds,
            max_polls=args.max_polls,
        )
    if args.provider == "stub":
        return _StubSearchVerifier()
    raise ValueError(f"unknown web verification provider: {args.provider}")


class _StubSearchVerifier:
    method = "stub"

    def search(self, query: str) -> list[SearchResult]:
        return [
            SearchResult(
                title=f"{query} - Yelp",
                url="https://www.yelp.com/biz/tonic-salon",
                description="Offline fixture result for prospect web verification.",
            )
        ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prospect scan and verification tools")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="process prospect grid cells")
    start.add_argument("--cells", type=int, default=1, help="max grid cells to process")
    start.add_argument("--approved-by", default="", help="named approver for live/bulk runs")
    start.add_argument("--dry-run", action="store_true", help="use fixture Places + mocked HTTP")
    start.add_argument(
        "--cell",
        action="append",
        help="specific cell id like seattle:beauty_salon (repeatable)",
    )
    start.add_argument("--bulk", action="store_true", help="run the bulk crawl approval gate")
    start.set_defaults(func=_cmd_start)

    sub.add_parser("status", help="show latest prospecting run").set_defaults(func=_cmd_status)
    sub.add_parser("stop", help="request a running scan stop").set_defaults(func=_cmd_stop)
    sub.add_parser(
        "backfill-priority", help="recompute cohorts and priority scores for existing records"
    ).set_defaults(func=_cmd_backfill_priority)

    export = sub.add_parser(
        "export-cohort", help="write sorted per-city verification CSVs for a cohort"
    )
    export.add_argument(
        "--cohort",
        default="A_gold",
        help="cohort to export (e.g. A_gold, B_stale_maps, C_potential_signal)",
    )
    export.add_argument("--output-dir", type=Path, default=None)
    export.set_defaults(func=_cmd_export_cohort)

    # Backward-compatible alias for the original A_gold-only command.
    export_a = sub.add_parser("export-cohort-a", help="alias: export the A_gold cohort")
    export_a.add_argument("--output-dir", type=Path, default=None)
    export_a.set_defaults(func=_cmd_export_cohort, cohort="A_gold")

    import_cmd = sub.add_parser(
        "import-verifications", help="import operator-filled verification CSV"
    )
    import_cmd.add_argument("csv", type=Path)
    import_cmd.set_defaults(func=_cmd_import_verifications)

    verify_web = sub.add_parser(
        "verify-web", help="verify prospect web presence through a search provider"
    )
    verify_web.add_argument(
        "--provider",
        required=True,
        choices=["brave", "dataforseo", "stub"],
        help="search provider; stub is offline and intended for tests/dry-runs",
    )
    verify_web.add_argument("--cohort", default="A_gold")
    verify_web.add_argument("--limit", type=int, default=50)
    verify_web.add_argument(
        "--include-verified",
        action="store_true",
        help="re-check records that already have a web_verify_verdict",
    )
    verify_web.add_argument(
        "--count",
        type=int,
        default=10,
        help="provider result count/depth per prospect",
    )
    verify_web.add_argument(
        "--location-code",
        type=int,
        default=2840,
        help="DataForSEO location code; 2840 is United States",
    )
    verify_web.add_argument("--language-code", default="en")
    verify_web.add_argument("--poll-interval-seconds", type=float, default=5.0)
    verify_web.add_argument("--max-polls", type=int, default=12)
    verify_web.set_defaults(func=_cmd_verify_web)

    verify_export = sub.add_parser(
        "verify-web-export",
        help="export a shard of unverified prospects as a manual browser worklist (no API)",
    )
    verify_export.add_argument("--cohort", default="S_source_candidate")
    verify_export.add_argument("--limit", type=int, default=25)
    verify_export.add_argument(
        "--shard", type=int, default=0, help="this chat's shard index (0..shard-count-1)"
    )
    verify_export.add_argument(
        "--shard-count",
        type=int,
        default=1,
        help="total number of parallel chats; sharding is deterministic and disjoint",
    )
    verify_export.add_argument(
        "--out",
        type=Path,
        default=Path("state/prospects/manual/worklist.json"),
        help="path to write the worklist JSON the agent will browse",
    )
    verify_export.add_argument(
        "--contacts-only",
        action="store_true",
        help="lighter pass: already-verified targets missing a digital contact (no verdict work)",
    )
    verify_export.add_argument(
        "--ids",
        type=Path,
        default=None,
        help="restrict --contacts-only to these place_ids (newline- or JSON-list file)",
    )
    verify_export.set_defaults(func=_cmd_verify_web_export)

    verify_ingest = sub.add_parser(
        "verify-web-ingest",
        help="ingest agent-collected browser observations back onto prospect records",
    )
    verify_ingest.add_argument(
        "--in",
        dest="in_path",
        type=Path,
        required=True,
        help="path to the worklist JSON the agent filled in",
    )
    verify_ingest.add_argument(
        "--contacts-only",
        action="store_true",
        help="write only contact channels; never touch the verdict/cohort",
    )
    verify_ingest.set_defaults(func=_cmd_verify_web_ingest)

    next_qualification = sub.add_parser(
        "next-qualification",
        help="print the next safest web-qualification step for the warehouse",
    )
    next_qualification.add_argument(
        "--provider",
        default="brave",
        choices=["brave", "dataforseo"],
        help="provider to include in the recommended verify-web command",
    )
    next_qualification.add_argument("--limit", type=int, default=50)
    next_qualification.set_defaults(func=_cmd_next_qualification)

    collect_source = sub.add_parser(
        "collect-source",
        help="collect open-source prospect candidates through the source-run ledger",
    )
    collect_source.add_argument(
        "--tranche",
        required=True,
        choices=["tranche1", "tranche2", "tranche3", "tranche4"],
        help="deterministic city/genre scale tranche to collect",
    )
    collect_source.add_argument(
        "--source",
        default="",
        choices=["", "fsq_os", "overture", "dataforseo"],
        help="source connector; defaults to FSQ for tranches 1/2 and Overture for tranche 3",
    )
    collect_source.add_argument(
        "--candidates-per-cell",
        type=int,
        default=50,
        help="maximum source candidates to request per city/genre cell",
    )
    collect_source.add_argument(
        "--force",
        action="store_true",
        help="re-run source cells even when the same source/city/genre/query is completed",
    )
    collect_source.add_argument(
        "--include-present-sites",
        action="store_true",
        help="import candidates even when the source already lists an owned website",
    )
    collect_source.add_argument(
        "--fsq-path",
        default="",
        help="local FSQ OS Places parquet/CSV path; also readable via FSQ_OS_PLACES_PATH",
    )
    collect_source.add_argument(
        "--overture-release",
        default=DEFAULT_OVERTURE_RELEASE,
        help="Overture release id to query from public S3",
    )
    collect_source.add_argument(
        "--radius-km",
        type=float,
        default=12.0,
        help="DataForSEO search radius in km around each city centre",
    )
    collect_source.add_argument(
        "--estimate-only",
        action="store_true",
        help="DataForSEO: print the cost ceiling and exit without calling the paid API",
    )
    collect_source.add_argument("--report-path", type=Path, default=None)
    collect_source.set_defaults(func=_cmd_collect_source)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
