"""Command line entrypoint for the ingestion pipeline.

    python -m ingest sync-catalog          # sets + singles from tcgcsv
    python -m ingest backfill --days 90    # daily history from archives
    python -m ingest refresh               # today's live prices
    python -m ingest metrics               # rebuild derived screener metrics
    python -m ingest daily                 # refresh + metrics (cron target)
    python -m ingest status                # what's loaded right now
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time

from . import backfill as backfill_module
from . import catalog as catalog_module
from . import metrics as metrics_module
from .config import ARCHIVE_START_DATE, DATABASE_PATH, date_from_day_index
from .db import open_initialised


def _log(message: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {message}", flush=True)


def _parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {value!r}") from error


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def command_sync_catalog(args: argparse.Namespace) -> int:
    connection = open_initialised()
    try:
        started = time.monotonic()
        result = catalog_module.sync_catalog(connection, progress=_log)
        _log(
            f"catalog synced in {time.monotonic() - started:.0f}s: "
            f"{result.sets_upserted:,} sets · {result.cards_upserted:,} singles · "
            f"{result.products_skipped:,} non-singles skipped"
        )
    finally:
        connection.close()
    return 0


def command_backfill(args: argparse.Namespace) -> int:
    connection = open_initialised()
    try:
        end = args.end or dt.date.today() - dt.timedelta(days=1)
        if args.days is not None:
            start = end - dt.timedelta(days=args.days - 1)
        else:
            start = args.start or ARCHIVE_START_DATE

        _log(f"backfilling {start} → {end}")
        started = time.monotonic()
        result = backfill_module.run_backfill(
            connection,
            start=start,
            end=end,
            keep_cache=args.keep_cache,
            progress=_log,
        )
        elapsed = time.monotonic() - started
        _log(
            f"backfill done in {elapsed / 60:.1f}m: {result.days_loaded:,} days · "
            f"{result.observations_written:,} observations · "
            f"{result.variants_created:,} new variants · "
            f"{result.days_missing} days unpublished · {len(result.failures)} failures"
        )
        for failure in result.failures[:20]:
            _log(f"  ! {failure}")
    finally:
        connection.close()
    return 0


def command_refresh(args: argparse.Namespace) -> int:
    connection = open_initialised()
    try:
        result = backfill_module.ingest_today(connection, progress=_log)
        _log(
            f"live refresh: {result.observations_written:,} observations · "
            f"{result.variants_created:,} new variants · {len(result.failures)} set failures"
        )
        for failure in result.failures[:20]:
            _log(f"  ! {failure}")
    finally:
        connection.close()
    return 0


def command_metrics(args: argparse.Namespace) -> int:
    connection = open_initialised()
    try:
        started = time.monotonic()
        written = metrics_module.rebuild_metrics(connection, progress=_log)
        _log(f"metrics rebuilt in {time.monotonic() - started:.0f}s: {written:,} screener rows")
        if args.prune:
            removed = catalog_module.prune_variants_without_prices(connection)
            _log(f"pruned {removed:,} variants with no price history")
    finally:
        connection.close()
    return 0


def command_daily(args: argparse.Namespace) -> int:
    """The cron target: catch up on archives, pull today live, rebuild metrics."""
    connection = open_initialised()
    try:
        yesterday = dt.date.today() - dt.timedelta(days=1)
        gaps = backfill_module.missing_dates(connection, end=yesterday)
        if gaps:
            _log(f"catching up {len(gaps)} missing archive day(s)")
            backfill_module.run_backfill(connection, end=yesterday, progress=_log)

        live = backfill_module.ingest_today(connection, progress=_log)
        _log(f"live refresh: {live.observations_written:,} observations")

        written = metrics_module.rebuild_metrics(connection, progress=_log)
        _log(f"daily complete: {written:,} screener rows")
    finally:
        connection.close()
    return 0


def command_status(args: argparse.Namespace) -> int:
    if not DATABASE_PATH.exists():
        _log(f"no database at {DATABASE_PATH} — run `sync-catalog` first")
        return 1

    connection = open_initialised()
    try:
        def scalar(sql: str) -> int:
            row = connection.execute(sql).fetchone()
            return row[0] if row and row[0] is not None else 0

        size_mb = DATABASE_PATH.stat().st_size / 1024 / 1024
        print(f"database          {DATABASE_PATH} ({size_mb:,.0f} MB)")
        print(f"sets              {scalar('SELECT COUNT(*) FROM sets'):,}")
        print(f"singles           {scalar('SELECT COUNT(*) FROM cards'):,}")
        print(f"variants          {scalar('SELECT COUNT(*) FROM card_variants'):,}")
        print(f"observations      {scalar('SELECT COUNT(*) FROM price_observations'):,}")
        print(f"days ingested     {scalar('SELECT COUNT(*) FROM ingested_days'):,}")
        print(f"screener rows     {scalar('SELECT COUNT(*) FROM card_metrics'):,}")

        span = connection.execute(
            "SELECT MIN(day) AS lo, MAX(day) AS hi FROM price_observations"
        ).fetchone()
        if span and span["lo"] is not None:
            print(
                f"history span      {date_from_day_index(span['lo'])} → "
                f"{date_from_day_index(span['hi'])}"
            )
    finally:
        connection.close()
    return 0


# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ingest", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("sync-catalog", help="pull sets and singles from tcgcsv").set_defaults(
        handler=command_sync_catalog
    )

    backfill_parser = subparsers.add_parser("backfill", help="load daily price archives")
    backfill_parser.add_argument("--start", type=_parse_date, help="first day (YYYY-MM-DD)")
    backfill_parser.add_argument("--end", type=_parse_date, help="last day (YYYY-MM-DD)")
    backfill_parser.add_argument(
        "--days", type=int, help="load only the most recent N days, ending at --end"
    )
    backfill_parser.add_argument(
        "--keep-cache",
        action="store_true",
        help="keep downloaded .7z archives on disk (uses many GB; useful when re-running)",
    )
    backfill_parser.set_defaults(handler=command_backfill)

    subparsers.add_parser("refresh", help="pull today's live prices").set_defaults(
        handler=command_refresh
    )

    metrics_parser = subparsers.add_parser("metrics", help="rebuild derived screener metrics")
    metrics_parser.add_argument(
        "--prune", action="store_true", help="also delete variants that never had a price"
    )
    metrics_parser.set_defaults(handler=command_metrics)

    subparsers.add_parser("daily", help="catch up, refresh live, rebuild metrics").set_defaults(
        handler=command_daily
    )
    subparsers.add_parser("status", help="show what is loaded").set_defaults(handler=command_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
