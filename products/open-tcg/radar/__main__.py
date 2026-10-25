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
    python -m radar stores [--days N] [--unmatched N]   # independent store report
    python -m radar stores-rematch                      # re-run listing matching after a catalog change
    python -m radar stores-review [--limit N] [--reason R] [--unknown-form]   # listings to identify by hand
    python -m radar stores-decide STORE VARIANT PRODUCT_ID|reject [--same-title] [--note TEXT] [--by founder|claude]
    python -m radar store-mail [--once]          # store drop emails: attribute, check the store, notify
    python -m radar store-mail-filter            # Gmail search for the founder's forwarding filter
    python -m radar inbox [--once]            # read alert emails (read-only IMAP)
    python -m radar inbox-export [--limit N]  # save recent Pokémon/alert emails to data/inbox-samples/
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time

from . import calendar, db, episodes, manual, notify, sources, watchlist
from .catalog import sync as catalog_sync
from .catalog.tcgcsv import TcgCsvClient
from .export import ExportError, export_observations
from .feeds import pokebeach, southern_hobby
from .http import make_client
from .inbox import message as inbox_message
from .inbox import reader as inbox_reader
from .social import bluesky
from .stores import collect as store_collect
from .stores import registry as store_registry
from .stores import reference as store_reference
from .stores import mail as store_mail
from .stores import alerts as store_alerts
from .stores import deals as store_deals
from .stores import msrp as store_msrp
from .stores import review as store_review
from .stores import scoring as store_scoring
from .stores import report as store_report


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


def _run_tcgcsv_reference(connection, now: dt.datetime) -> str:
    client = TcgCsvClient()
    try:
        result = store_reference.sync_reference(connection, client, now=now)
    finally:
        client.close()
    return (
        f"{result.groups_seen} groups, {result.groups_refetched} refreshed, {result.products_upserted} sealed "
        f"products, prices for {result.price_groups} groups ({result.prices_recorded})"
    )


def _run_stores(connection, now: dt.datetime) -> str:
    stores = store_registry.load()
    store_scoring.refresh(connection, stores, now=now)
    cadence = store_scoring.cadence(connection, stores, now=now, set_keys=store_scoring.watched_set_keys(connection))
    summary = store_collect.collect(connection, now=now, stores=stores, cadence=cadence, mode="slow")
    store_msrp.sync(connection, store_msrp.load())
    alerted = store_alerts.evaluate(connection, now=now)
    for failure in summary.failures:
        print(f"  store failed: {failure}", file=sys.stderr, flush=True)
    if summary.stores_polled and summary.stores_failed == summary.stores_polled:
        raise RuntimeError(f"all {summary.stores_polled} stores failed")
    return (
        f"{summary.stores_polled} stores ({summary.full_sweeps} full sweeps, {summary.collection_checks} collection "
        f"checks, {summary.catalog_sweeps_deferred} sweeps deferred, {summary.stores_failed} failed), "
        f"{summary.listings_new} new listings, {summary.listings_changed} changed, "
        f"{alerted.observations} store observations, {alerted.alerts} alerts"
    )


RUNNERS = {
    "tcgcsv": _run_tcgcsv,
    "southern_hobby": _run_southern_hobby,
    "pokebeach_rss": _run_pokebeach,
    "tcgcsv_reference": _run_tcgcsv_reference,
    "stores": _run_stores,
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
    print(store_report.store_health(connection, store_registry.load()))
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


def cmd_inbox(args: argparse.Namespace) -> int:
    connection = _open()
    watch = watchlist.load()

    def on_observation(observation_id: int) -> None:
        _print_observation(connection, observation_id)
        _settle(connection, episodes.assign(connection, observation_id), watch)

    if not args.once:
        print("reading the project inbox read-only every 30 s (Ctrl-C to stop)", flush=True)
        try:
            inbox_reader.run_inbox(connection, watch=watch, on_observation=on_observation)
        except KeyboardInterrupt:
            return 0
        return 0

    mailbox = inbox_reader.ImapMailbox(*inbox_reader.credentials())
    try:
        new_ids = inbox_reader.poll(connection, mailbox, watch=watch, now=_now())
    finally:
        mailbox.close()
    sources.record_run(connection, "email", ok=True, now=_now())
    for observation_id in new_ids:
        on_observation(observation_id)
    print(f"email: {len(new_ids)} new alert emails")
    return 0


def cmd_inbox_export(args: argparse.Namespace) -> int:
    """Save relevant recent emails so parsers can be built against real ones."""
    out_dir = db.DB_PATH.parent / "inbox-samples"
    out_dir.mkdir(parents=True, exist_ok=True)
    mailbox = inbox_reader.ImapMailbox(*inbox_reader.credentials())
    saved = 0
    try:
        since = dt.date.today() - dt.timedelta(days=args.days)
        for uid in reversed(mailbox.search(after_uid=None, since=since)):
            raw = mailbox.fetch(uid)
            alert = inbox_message.parse_email(raw)
            if not inbox_message.is_relevant(alert):
                continue
            (out_dir / f"{uid}.eml").write_bytes(raw)
            print(f"{uid}: {alert.sender_domain:<20} {alert.subject[:90]}")
            saved += 1
            if saved >= args.limit:
                break
    finally:
        mailbox.close()
    print(f"saved {saved} emails to {out_dir}")
    return 0


def cmd_stores(args: argparse.Namespace) -> int:
    connection = _open()
    print(store_report.render(connection, now=_now(), days=args.days, show_unmatched=args.unmatched), end="")
    return 0


def cmd_msrp(args: argparse.Namespace) -> int:
    connection = _open()
    try:
        config = store_msrp.load()
    except ValueError as exc:
        print(f"msrp: {exc}", file=sys.stderr)
        return 2
    count = store_msrp.sync(connection, config)
    resolver = store_msrp.Resolver.from_db(connection, config)
    forms = tuple(args.forms.split(",")) if args.forms else store_msrp.TARGET_FORMS
    if args.view != "missing":
        print(f"{count} evidence references synced")
    print(
        store_msrp.render_coverage(connection, resolver, forms=forms, since=args.since,
                                   missing_only=args.view == "missing"),
        end="",
    )
    return 0


FAST_LOOP_S = 30
FAST_SET_KEYS_EVERY = dt.timedelta(minutes=15)


def cmd_stores_fast(args: argparse.Namespace) -> int:
    """Read hot stores (and drop-window stores) on their sub-15-minute cadence; the sync reads the rest."""
    connection = _open()
    print("reading fast-cadence stores every 30 s (Ctrl-C to stop)", flush=True)
    set_keys: frozenset[str] = frozenset()
    keys_at: dt.datetime | None = None
    while True:
        now = _now()
        try:
            if keys_at is None or now - keys_at >= FAST_SET_KEYS_EVERY:
                set_keys, keys_at = store_scoring.watched_set_keys(connection), now
            stores = store_registry.load()
            cadence = store_scoring.cadence(connection, stores, now=now, set_keys=set_keys)
            summary = store_collect.collect(connection, now=now, stores=stores, cadence=cadence, mode="fast")
            if summary.stores_polled:
                alerted = store_alerts.evaluate(connection, now=now) if (
                    summary.listings_new or summary.listings_changed) else None
                print(
                    f"{now.isoformat()} fast: {summary.stores_polled} stores, {summary.stores_failed} failed, "
                    f"{summary.listings_new} new, {summary.listings_changed} changed"
                    + (f", {alerted.alerts} alerts" if alerted else ""),
                    flush=True,
                )
                for failure in summary.failures:
                    print(f"  store failed: {failure}", file=sys.stderr, flush=True)
        except Exception as exc:  # keep the loop alive; launchd restarts on a crash anyway
            print(f"{now.isoformat()} fast: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        if args.once:
            return 0
        time.sleep(FAST_LOOP_S)


def cmd_store_scores(_: argparse.Namespace) -> int:
    connection = _open()
    now = _now()
    store_scoring.refresh(connection, store_registry.load(), now=now, force=True)
    print(store_scoring.render(connection, now=now, set_keys=store_scoring.watched_set_keys(connection)), end="")
    return 0


def cmd_deals(args: argparse.Namespace) -> int:
    connection = _open()
    store_msrp.sync(connection, store_msrp.load())
    print(store_deals.render(connection, now=_now(), limit=args.limit), end="")
    return 0


def cmd_stores_rematch(_: argparse.Namespace) -> int:
    connection = _open()
    print(f"rematched {store_collect.rematch(connection)} listings")
    return 0


def cmd_stores_review(args: argparse.Namespace) -> int:
    connection = _open()
    store_review.ensure_schema(connection)
    items = store_review.queue(
        connection, limit=args.limit, reason=args.reason, include_unknown_form=args.unknown_form
    )
    print(store_review.render_queue(items), end="")
    return 0


def cmd_stores_decide(args: argparse.Namespace) -> int:
    connection = _open()
    store_review.ensure_schema(connection)
    try:
        count = store_review.decide(
            connection,
            store_id=args.store,
            variant_id=args.variant,
            product=args.product,
            decided_by=args.by,
            now=_now(),
            note=args.note,
            same_title=args.same_title,
        )
    except store_review.DecisionError as exc:
        print(f"stores-decide: {exc}", file=sys.stderr)
        return 2
    print(f"decision recorded for {count} listing(s)")
    return 0


def _print_store_email(email) -> None:
    store = email.store_id or f"unattributed {email.sender}"
    print(f"{_now().isoformat(timespec='seconds')} store_email {email.kind}{' pokemon' if email.is_pokemon else ''} "
          f"[{store}] {email.subject[:100]}", flush=True)


def cmd_store_mail(args: argparse.Namespace) -> int:
    connection = _open()
    store_review.ensure_schema(connection)
    if not args.once:
        print("reading store emails in the project inbox read-only every 30 s (Ctrl-C to stop)", flush=True)
        try:
            store_mail.run(connection, on_email=_print_store_email)
        except KeyboardInterrupt:
            return 0
        return 0
    mailbox = store_mail.StoreMailbox(*inbox_reader.credentials())
    try:
        emails = store_mail.poll(
            connection,
            mailbox,
            stores=store_registry.load(),
            now=_now(),
            check_store=lambda c, s, n: store_collect.check_store_now(c, s, now=n),
            notifier=notify.macos_notify,
        )
    finally:
        mailbox.close()
    sources.record_run(connection, store_mail.SOURCE_ID, ok=True, now=_now())
    for email in emails:
        _print_store_email(email)
    print(f"store_email: {len(emails)} new store emails")
    return 0


def cmd_store_mail_filter(_: argparse.Namespace) -> int:
    connection = _open()
    print(store_mail.forwarding_filter(connection, store_registry.load()))
    return 0


def cmd_init_db(_: argparse.Namespace) -> int:
    _open()
    print(f"database ready at {db.DB_PATH}")
    return 0


def cmd_export_observations(args: argparse.Namespace) -> int:
    """Emit radar observations as NDJSON without opening the normal radar DB."""
    try:
        records = export_observations(args.db, after=args.after, limit=args.limit)
    except ExportError as exc:
        print(f"export-observations: {exc}", file=sys.stderr)
        return 2
    for record in records:
        print(json.dumps(record, separators=(",", ":"), sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radar", description="OpenTCG radar")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db").set_defaults(func=cmd_init_db)
    export_observations_parser = commands.add_parser(
        "export-observations", help="write read-only observation evidence as NDJSON"
    )
    export_observations_parser.add_argument("--db", required=True, help="existing radar SQLite database")
    export_observations_parser.add_argument("--after", help="cursor from a prior export record")
    export_observations_parser.add_argument("--limit", type=int, default=100)
    export_observations_parser.set_defaults(func=cmd_export_observations)
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
    stores_parser = commands.add_parser("stores", help="independent store report")
    stores_parser.add_argument("--days", type=int, default=7)
    stores_parser.add_argument("--unmatched", type=int, default=0, help="also list N unmatched English titles")
    stores_parser.set_defaults(func=cmd_stores)
    msrp_parser = commands.add_parser("msrp", help="MSRP reference coverage, or the products still missing one")
    msrp_parser.add_argument("view", nargs="?", choices=("coverage", "missing"), default="coverage")
    msrp_parser.add_argument("--since", default=store_msrp.TARGET_SINCE, help="release date floor (YYYY-MM-DD)")
    msrp_parser.add_argument("--forms", help="comma-separated product types (default etb,booster_bundle,booster_box)")
    msrp_parser.set_defaults(func=cmd_msrp)
    fast_parser = commands.add_parser("stores-fast", help="read hot and drop-window stores every few minutes")
    fast_parser.add_argument("--once", action="store_true")
    fast_parser.set_defaults(func=cmd_stores_fast)
    commands.add_parser("store-scores", help="store scores, tiers and cadence").set_defaults(func=cmd_store_scores)
    deals_parser = commands.add_parser("deals", help="cheapest store offer per product, by MSRP class")
    deals_parser.add_argument("--limit", type=int, default=40, help="rows per class")
    deals_parser.set_defaults(func=cmd_deals)
    commands.add_parser("stores-rematch", help="re-run store listing matching").set_defaults(func=cmd_stores_rematch)
    store_mail_parser = commands.add_parser("store-mail", help="read store drop emails from the project inbox")
    store_mail_parser.add_argument("--once", action="store_true")
    store_mail_parser.set_defaults(func=cmd_store_mail)
    commands.add_parser("store-mail-filter", help="Gmail search for the store-mail forwarding filter").set_defaults(
        func=cmd_store_mail_filter
    )
    review_parser = commands.add_parser("stores-review", help="store listings to identify by hand")
    review_parser.add_argument("--limit", type=int, default=30)
    review_parser.add_argument("--reason", help="only this match reason")
    review_parser.add_argument("--unknown-form", action="store_true", help="include listings with no recognized form")
    review_parser.set_defaults(func=cmd_stores_review)
    decide_parser = commands.add_parser("stores-decide", help="confirm or reject a store listing's product")
    decide_parser.add_argument("store")
    decide_parser.add_argument("variant", type=int)
    decide_parser.add_argument("product", help="reference product id, or 'reject'")
    decide_parser.add_argument("--same-title", action="store_true", help="apply to every listing with the same title")
    decide_parser.add_argument("--note")
    decide_parser.add_argument("--by", choices=("founder", "claude"), default="founder")
    decide_parser.set_defaults(func=cmd_stores_decide)
    inbox_parser = commands.add_parser("inbox", help="read alert emails from the project inbox")
    inbox_parser.add_argument("--once", action="store_true")
    inbox_parser.set_defaults(func=cmd_inbox)
    export_parser = commands.add_parser("inbox-export", help="save recent relevant emails as samples")
    export_parser.add_argument("--limit", type=int, default=15)
    export_parser.add_argument("--days", type=int, default=30)
    export_parser.set_defaults(func=cmd_inbox_export)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
