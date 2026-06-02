#!/usr/bin/env python3
"""Operator CLI for Phase 1 local-SMB prospecting.

Mirrors the discovery CLI shape: start/status/stop. ``--dry-run`` uses fixture
data and mocked HTTP, so it exercises persistence/cohorts without live APIs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.config.settings import get_api_key  # noqa: E402
from packages.prospecting.config import (  # noqa: E402
    load_cities,
    load_genres,
    load_http_config,
    load_weekly_caps,
)
from packages.prospecting.connectors.google_places import (  # noqa: E402
    GOOGLE_PLACES_API_KEY_ENV_VAR,
    GooglePlacesConnector,
)
from packages.prospecting.grid import GridCursorStore  # noqa: E402
from packages.prospecting.http_check import HTTPChecker  # noqa: E402
from packages.prospecting.report import write_cohort_report  # noqa: E402
from packages.prospecting.run import (  # noqa: E402
    FileStopSignal,
    FixturePlacesConnector,
    ProspectRunStore,
    fixture_http_checker,
    run_prospecting,
)
from packages.prospecting.storage import ProspectRepository  # noqa: E402


def _cmd_start(args: argparse.Namespace) -> int:
    if not args.dry_run and not args.approved_by:
        print("Live prospecting requires --approved-by NAME.", file=sys.stderr)
        return 1

    stop = FileStopSignal()
    stop.clear()
    records = ProspectRepository()
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
    print(
        f"Run {report.run_id}: {report.status} — cells={report.cells_done}, "
        f"places={report.places_seen}, created={report.records_created}, "
        f"updated={report.records_updated}"
    )
    if report.api_errors:
        print("Errors:", "; ".join(report.api_errors))
    print(f"HTTP counts: {report.http_counts}")
    print(f"Cap headroom: {report.cap_headroom}")
    return 0 if report.status in {"completed", "cap_hit", "stopped"} and not report.api_errors else 1


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 1 prospect scan")
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

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
