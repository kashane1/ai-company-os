"""OpenTCG radar command line.

    python -m radar init-db
    python -m radar sync [--only SOURCE]
    python -m radar calendar
    python -m radar events [--days N]
    python -m radar sources
    python -m radar backfill          # recent posts from the Bluesky restock accounts
    python -m radar stream            # follow Bluesky live (runs until stopped)
    python -m radar feed [--hours N] [--all]
    python -m radar episodes [--hours N]       # restocks grouped across sources
    python -m radar scorecard                  # which source is first, and how accurate
    python -m radar mark EPISODE_ID real|false
    python -m radar log guppy|sighting "TEXT" [--retailer R] [--at "YYYY-MM-DD HH:MM"]
    python -m radar notify-test
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from . import calendar, db, episodes, manual, notify, sources, watchlist
from .catalog import sync as catalog_sync
from .catalog.tcgcsv import TcgCsvClient
from .feeds import pokebeach, southern_hobby
from .http import make_client
from .social import bluesky


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
        if not args.force and not args.only and not sources.is_due(connection, source_id, now):
            continue
        try:
            summary = runner(connection, now)
        except Exception as exc:  # one failing source must not stop the others
            failures += 1
            connection.rollback()
            sources.record_run(connection, source_id, ok=False, error=f"{type(exc).__name__}: {exc}", now=now)
            print(f"{source_id}: FAILED ({type(exc).__name__}: {exc})", file=sys.stderr)
            continue
        sources.record_run(connection, source_id, ok=True, now=now)
        print(f"{now.isoformat(timespec='seconds')} {source_id}: {summary}", flush=True)
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


def _settle(connection, episode_ids: list[int], watch) -> None:
    """Notify for fresh watched episodes; the freshness gate keeps backfills quiet."""
    for episode_id in episode_ids:
        if notify.maybe_notify(connection, episode_id, now=_now(), watch=watch):
            print(f"  notified: episode {episode_id}", flush=True)


def cmd_backfill(_: argparse.Namespace) -> int:
    connection = _open()
    watch = watchlist.load()
    with make_client() as client:
        inserted = bluesky.backfill(connection, client, watch=watch, now=_now())
    _settle(connection, episodes.assign_pending(connection), watch)
    print(f"bluesky: {inserted} new posts")
    return 0


def _print_observation(connection, observation_id: int) -> None:
    row = connection.execute("SELECT * FROM observations WHERE id = ?", (observation_id,)).fetchone()
    matches = json.loads(row["watch_matches"])
    flag = "WATCHED" if matches else ("tcg" if row["is_tcg"] else "-")
    when = (row["source_time"] or row["received_at"])[:16].replace("T", " ")
    print(f"{when}  {flag:<7} {row['signal']:<17} {row['retailer'] or '?':<14} {row['product_text'][:90]}", flush=True)
    for name in matches:
        print(f"{'':>25}↳ {name}", flush=True)


def cmd_stream(_: argparse.Namespace) -> int:
    connection = _open()
    watch = watchlist.load()
    with make_client() as client:
        print(f"backfill: {bluesky.backfill(connection, client, watch=watch, now=_now())} new posts", flush=True)
    _settle(connection, episodes.assign_pending(connection), watch)
    print("following Bluesky restock accounts (Ctrl-C to stop)", flush=True)

    def on_observation(observation_id: int) -> None:
        _print_observation(connection, observation_id)
        _settle(connection, episodes.assign(connection, observation_id), watch)

    try:
        bluesky.run_stream(connection, watch=watch, on_observation=on_observation)
    except KeyboardInterrupt:
        return 0
    return 0


def cmd_feed(args: argparse.Namespace) -> int:
    connection = _open()
    since = (_now() - dt.timedelta(hours=args.hours)).isoformat(timespec="seconds")
    query = "SELECT id FROM observations WHERE COALESCE(source_time, received_at) >= ?"
    if not args.all:
        query += " AND is_tcg = 1"
    ids = [row["id"] for row in connection.execute(query + " ORDER BY COALESCE(source_time, received_at)", (since,))]
    if not ids:
        print(f"No {'' if args.all else 'TCG '}observations in the last {args.hours} hours.")
    for observation_id in ids:
        _print_observation(connection, observation_id)
    return 0


def _minutes(seconds: int | None) -> str:
    return "-" if seconds is None else (f"{seconds // 60}m {seconds % 60:02d}s" if seconds >= 60 else f"{seconds}s")


def cmd_episodes(args: argparse.Namespace) -> int:
    connection = _open()
    episodes.assign_pending(connection)
    since = (_now() - dt.timedelta(hours=args.hours)).isoformat(timespec="seconds")
    rows = connection.execute(
        "SELECT * FROM episodes WHERE last_seen_at >= ? ORDER BY opened_at DESC", (since,)
    ).fetchall()
    if not rows:
        print(f"No episodes in the last {args.hours} hours.")
    for row in rows:
        reports = connection.execute(
            "SELECT source_id, MIN(lag_s) AS lag FROM episode_observations WHERE episode_id = ? GROUP BY source_id ORDER BY lag",
            (row["id"],),
        ).fetchall()
        who = ", ".join(f"{r['source_id']} +{_minutes(r['lag'])}" if r["lag"] else r["source_id"] for r in reports)
        label = row["watch_item"] or row["product_text"][:70]
        verdict = f" [{row['verdict']}]" if row["verdict"] else ""
        print(f"#{row['id']:<5} {row['opened_at'][:16].replace('T', ' ')}  {row['first_signal']:<17} "
              f"{row['retailer'] or '?':<14} {label}{verdict}")
        print(f"{'':>7}reported by: {who}")
    return 0


def cmd_scorecard(_: argparse.Namespace) -> int:
    connection = _open()
    episodes.assign_pending(connection)
    scores = episodes.scorecard(connection)
    if not scores:
        print("No episodes yet.")
        return 0
    print(f"{'source':<26}{'episodes':>9}{'first':>7}{'median lag when not first':>28}{'accuracy':>10}")
    for score in scores:
        accuracy = "-" if score.accuracy is None else f"{score.accuracy:.0%}"
        print(f"{score.source_id:<26}{score.episodes:>9}{score.first:>7}{_minutes(score.median_lag_s):>28}{accuracy:>10}")
    print("\naccuracy counts episodes you marked with: radar mark EPISODE_ID real|false")
    return 0


def cmd_mark(args: argparse.Namespace) -> int:
    connection = _open()
    episodes.set_verdict(connection, args.episode_id, args.verdict)
    print(f"episode {args.episode_id} marked {args.verdict}")
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    connection = _open()
    watch = watchlist.load()
    at = dt.datetime.strptime(args.at, "%Y-%m-%d %H:%M").astimezone() if args.at else _now()
    observation_id = manual.log(
        connection, kind=args.kind, text=args.text, at=at, watch=watch,
        set_keys=bluesky.catalog_set_keys(connection), now=_now(), retailer=args.retailer,
    )
    episode_ids = episodes.assign(connection, observation_id)
    _print_observation(connection, observation_id)
    print(f"joined episode(s): {', '.join(map(str, episode_ids)) or 'none'}")
    return 0


def cmd_notify_test(_: argparse.Namespace) -> int:
    notify.macos_notify("OpenTCG test", "Mac notifications are working.")
    print("sent a test notification")
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
    sync_parser.add_argument("--force", action="store_true", help="poll every source even if not due")
    sync_parser.set_defaults(func=cmd_sync)
    commands.add_parser("calendar", help="upcoming sealed releases").set_defaults(func=cmd_calendar)
    events_parser = commands.add_parser("events", help="recent calendar events")
    events_parser.add_argument("--days", type=int, default=7)
    events_parser.set_defaults(func=cmd_events)
    commands.add_parser("sources", help="source health").set_defaults(func=cmd_sources)
    commands.add_parser("backfill", help="fetch recent Bluesky restock posts").set_defaults(func=cmd_backfill)
    commands.add_parser("stream", help="follow Bluesky live").set_defaults(func=cmd_stream)
    feed_parser = commands.add_parser("feed", help="recent restock observations")
    feed_parser.add_argument("--hours", type=int, default=72)
    feed_parser.add_argument("--all", action="store_true", help="include non-TCG posts")
    feed_parser.set_defaults(func=cmd_feed)
    episodes_parser = commands.add_parser("episodes", help="restocks grouped across sources")
    episodes_parser.add_argument("--hours", type=int, default=72)
    episodes_parser.set_defaults(func=cmd_episodes)
    commands.add_parser("scorecard", help="source speed and accuracy").set_defaults(func=cmd_scorecard)
    mark_parser = commands.add_parser("mark", help="mark an episode real or false")
    mark_parser.add_argument("episode_id", type=int)
    mark_parser.add_argument("verdict", choices=["real", "false"])
    mark_parser.set_defaults(func=cmd_mark)
    log_parser = commands.add_parser("log", help="log a Guppy alert or a sighting")
    log_parser.add_argument("kind", choices=list(manual.KINDS))
    log_parser.add_argument("text")
    log_parser.add_argument("--retailer")
    log_parser.add_argument("--at", help='local time, "YYYY-MM-DD HH:MM" (default now)')
    log_parser.set_defaults(func=cmd_log)
    commands.add_parser("notify-test", help="send a test Mac notification").set_defaults(func=cmd_notify_test)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
