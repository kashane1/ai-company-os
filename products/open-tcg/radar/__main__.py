"""OpenTCG radar command line.

    python -m radar init-db
    python -m radar sync [--only SOURCE]
    python -m radar calendar
    python -m radar events [--days N]
    python -m radar sources
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from . import calendar, db, sources
from .catalog import sync as catalog_sync
from .catalog.tcgcsv import TcgCsvClient
from .feeds import pokebeach, southern_hobby
from .http import make_client


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _open() -> "db.sqlite3.Connection":
    connection = db.connect()
    db.init(connection)
    sources.ensure_registered(connection)
    return connection


def _run_tcgcsv(connection, now: dt.datetime) -> str:
    client = TcgCsvClient()
    try:
        result = catalog_sync.sync_catalog(connection, client, now=now)
    finally:
        client.close()
    return (
        f"{result.groups_selected} sets checked, {result.groups_refetched} refreshed, "
        f"{result.products_upserted} sealed products, {result.prices_recorded} prices, "
        f"{result.events_emitted} new events"
    )


def _run_southern_hobby(connection, now: dt.datetime) -> str:
    with make_client() as client:
        emitted = southern_hobby.sync(connection, fetch_page=southern_hobby.fetch_page_with(client), now=now)
    return f"{emitted} new events"


def _run_pokebeach(connection, now: dt.datetime) -> str:
    with make_client() as client:
        emitted = pokebeach.sync(connection, fetch_feed=pokebeach.fetch_feed_with(client), now=now)
    return f"{emitted} new events"


RUNNERS = {
    "tcgcsv": _run_tcgcsv,
    "southern_hobby": _run_southern_hobby,
    "pokebeach_rss": _run_pokebeach,
}


def cmd_sync(args: argparse.Namespace) -> int:
    connection = _open()
    failures = 0
    for source_id, runner in RUNNERS.items():
        if args.only and source_id != args.only:
            continue
        if not sources.get(source_id).enabled:
            continue
        now = _now()
        try:
            summary = runner(connection, now)
        except Exception as exc:  # one failing source must not stop the others
            failures += 1
            connection.rollback()
            sources.record_run(connection, source_id, ok=False, error=f"{type(exc).__name__}: {exc}", now=now)
            print(f"{source_id}: FAILED ({type(exc).__name__}: {exc})", file=sys.stderr)
            continue
        sources.record_run(connection, source_id, ok=True, now=now)
        print(f"{source_id}: {summary}")
    return 1 if failures else 0


def cmd_calendar(_: argparse.Namespace) -> int:
    connection = _open()
    today = dt.date.today()
    print(calendar.render(calendar.upcoming(connection, today=today), today=today), end="")
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    connection = _open()
    rows = calendar.recent_events(connection, since=_now() - dt.timedelta(days=args.days))
    if not rows:
        print(f"No new events in the last {args.days} days.")
    for row in rows:
        value = f" ({row['value']})" if row["value"] else ""
        print(f"{row['detected_at'][:16]}  {row['kind']:<21} {row['source_id']:<15} {row['subject_text']}{value}")
    return 0


def cmd_sources(_: argparse.Namespace) -> int:
    connection = _open()
    for row in sources.health(connection, _now()):
        detail = row.last_error if row.status == "failing" else (row.note if row.status == "disabled" else "")
        last = row.last_success_at[:16] if row.last_success_at else "-"
        print(f"{row.source_id:<15} {row.tier}  {row.status:<9} last ok {last:<16} {detail}")
    return 0


def cmd_init_db(_: argparse.Namespace) -> int:
    _open()
    print(f"database ready at {db.DB_PATH}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radar", description="OpenTCG radar")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db").set_defaults(func=cmd_init_db)
    sync_parser = commands.add_parser("sync", help="run every enabled poll source once")
    sync_parser.add_argument("--only", choices=sorted(RUNNERS))
    sync_parser.set_defaults(func=cmd_sync)
    commands.add_parser("calendar", help="upcoming sealed releases").set_defaults(func=cmd_calendar)
    events_parser = commands.add_parser("events", help="recent calendar events")
    events_parser.add_argument("--days", type=int, default=7)
    events_parser.set_defaults(func=cmd_events)
    commands.add_parser("sources", help="source health").set_defaults(func=cmd_sources)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
