"""Store scores and cadence (plan phase P7).

Each store is scored over the last SCORE_WINDOW from its own history:
matched listings, offers at or below an evidence MSRP right now,
alert-eligible observations, new listings, how long stock lasts, and the
read failure rate. The score sets an effective tier and discovery cadence:

| Tier | Discovery | When |
|---|---|---|
| hot | every 5 min | MSRP hits in the window, or several MSRP offers in stock now |
| first_pass / explore / backup | registry cadence (15 / 60 / 60 min) | otherwise |
| (any, failing) | registry cadence × 4, at most 4 h | half or more of 8+ reads failed |

In a drop window, hot and first-pass stores are read every 2 minutes. A
drop window is a watched set's release day (from 05:00 local), or the hour
after a Bluesky or email availability signal names a watched set.

Stores due faster than every 15 minutes are read by `radar stores-fast`
(its own LaunchAgent), the rest by the 15-minute sync, so no store is read
by both.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import statistics
from dataclasses import dataclass

from ..db import iso
from ..episodes import AVAILABILITY_SIGNALS
from ..matching import normalize
from . import msrp, registry, report

SCORE_WINDOW = dt.timedelta(days=14)
REFRESH_EVERY = dt.timedelta(minutes=60)
HOT_MINUTES = 5
DROP_WINDOW_MINUTES = 2
FAST_BELOW_MINUTES = 15  # cadences under this belong to `radar stores-fast`
HOT_MIN_MSRP_HITS = 2
HOT_MIN_MSRP_OFFERS_NOW = 3
FAILING_MIN_RUNS = 8
FAILING_SHARE = 0.5
FAILING_FACTOR = 4
FAILING_MAX_MINUTES = 240
RELEASE_DAY_FROM_HOUR = 5
SIGNAL_WINDOW = dt.timedelta(hours=1)
SIGNAL_SOURCES = ("bluesky", "email", "store_email")


@dataclass(frozen=True)
class StoreScore:
    store_id: str
    matched_listings: int
    in_stock_matched: int
    msrp_offers_now: int
    msrp_hits: int
    new_listings: int
    stock_minutes_median: float | None
    runs: int
    failures: int
    effective_tier: str
    discovery_minutes: int
    reason: str


def _tier(store: registry.Store, *, msrp_hits: int, msrp_offers_now: int, runs: int, failures: int) -> tuple[str, int, str]:
    if runs >= FAILING_MIN_RUNS and failures / runs >= FAILING_SHARE:
        minutes = min(store.discovery_minutes * FAILING_FACTOR, FAILING_MAX_MINUTES)
        return store.tier, minutes, f"failing: {failures} of {runs} reads failed"
    if msrp_hits >= HOT_MIN_MSRP_HITS:
        return "hot", HOT_MINUTES, f"{msrp_hits} MSRP hits in {SCORE_WINDOW.days} days"
    if msrp_offers_now >= HOT_MIN_MSRP_OFFERS_NOW:
        return "hot", HOT_MINUTES, f"{msrp_offers_now} offers at or below MSRP in stock"
    return store.tier, store.discovery_minutes, "registry tier"


def compute(
    connection: sqlite3.Connection, stores: list[registry.Store], *, now: dt.datetime,
    resolver: msrp.Resolver | None = None,
) -> list[StoreScore]:
    since = iso(now - SCORE_WINDOW)
    since_day = (now - SCORE_WINDOW).astimezone(dt.timezone.utc).date().isoformat()
    names = {}
    eligible_now: dict[str, int] = {}
    for offer in report.offers(connection, {}, resolver):
        if offer.price_class.is_alert_eligible:
            eligible_now[offer.store] = eligible_now.get(offer.store, 0) + 1
    listing_counts = {
        row["store_id"]: row for row in connection.execute(
            """
            SELECT store_id, COUNT(*) AS matched, SUM(is_available) AS in_stock,
                   SUM(CASE WHEN is_baseline = 0 AND first_seen_at >= ? THEN 1 ELSE 0 END) AS new
            FROM store_listings WHERE match_status IN ('exact', 'confirmed') GROUP BY store_id
            """,
            (since,),
        )
    }
    hits = {
        row["store_id"]: row["n"] for row in connection.execute(
            """
            SELECT d.store_id, COUNT(*) AS n FROM store_offer_details d JOIN observations o ON o.id = d.observation_id
            WHERE d.is_alert_eligible = 1 AND o.received_at >= ? GROUP BY d.store_id
            """,
            (since,),
        )
    }
    run_counts = {
        row["store_id"]: (row["runs"], row["failures"]) for row in connection.execute(
            "SELECT store_id, SUM(runs) AS runs, SUM(failures) AS failures FROM store_run_days WHERE day >= ? GROUP BY store_id",
            (since_day,),
        )
    }
    for row in connection.execute("SELECT store_id, name FROM stores"):
        names[row["store_id"]] = row["name"]
    spans: dict[str, list[float]] = {}
    for store_name, _, minutes in report.in_stock_spans(connection, now - SCORE_WINDOW):
        spans.setdefault(store_name, []).append(minutes)

    scores = []
    for store in stores:
        if not store.is_polled:
            continue
        counts = listing_counts.get(store.store_id)
        runs, failures = run_counts.get(store.store_id, (0, 0))
        msrp_hits = hits.get(store.store_id, 0)
        msrp_now = eligible_now.get(names.get(store.store_id, store.name), 0)
        tier, minutes, reason = _tier(store, msrp_hits=msrp_hits, msrp_offers_now=msrp_now, runs=runs, failures=failures)
        store_spans = spans.get(names.get(store.store_id, store.name), [])
        scores.append(
            StoreScore(
                store_id=store.store_id,
                matched_listings=counts["matched"] if counts else 0,
                in_stock_matched=(counts["in_stock"] or 0) if counts else 0,
                msrp_offers_now=msrp_now,
                msrp_hits=msrp_hits,
                new_listings=(counts["new"] or 0) if counts else 0,
                stock_minutes_median=statistics.median(store_spans) if store_spans else None,
                runs=runs,
                failures=failures,
                effective_tier=tier,
                discovery_minutes=minutes,
                reason=reason,
            )
        )
    return scores


def refresh(connection: sqlite3.Connection, stores: list[registry.Store], *, now: dt.datetime,
            force: bool = False) -> bool:
    """Recompute store scores when the last refresh is older than REFRESH_EVERY; True if it ran."""
    last = connection.execute("SELECT MAX(computed_at) AS at FROM store_scores").fetchone()["at"]
    if not force and last and now - dt.datetime.fromisoformat(last) < REFRESH_EVERY:
        return False
    scores = compute(connection, stores, now=now)
    connection.execute("DELETE FROM store_scores")
    connection.executemany(
        """
        INSERT INTO store_scores (store_id, computed_at, matched_listings, in_stock_matched, msrp_offers_now, msrp_hits,
            new_listings, stock_minutes_median, runs, failures, effective_tier, discovery_minutes, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (s.store_id, iso(now), s.matched_listings, s.in_stock_matched, s.msrp_offers_now, s.msrp_hits,
             s.new_listings, s.stock_minutes_median, s.runs, s.failures, s.effective_tier, s.discovery_minutes, s.reason)
            for s in scores
        ],
    )
    connection.commit()
    return True


def drop_window(connection: sqlite3.Connection, *, now: dt.datetime, set_keys: frozenset[str] | set[str]) -> str | None:
    """Why a drop window is open now (watched set release day, or a fresh availability signal), or None."""
    if not set_keys:
        return None
    local = now.astimezone()
    if local.hour >= RELEASE_DAY_FROM_HOUR:
        today = local.date().isoformat()
        for row in connection.execute(
            """
            SELECT DISTINCT g.name FROM ref_products p JOIN ref_groups g USING (group_id)
            WHERE COALESCE(p.release_on, g.published_on) = ?
            """,
            (today,),
        ):
            name = row["name"]
            if any(key in name.lower() for key in set_keys):
                return f"release day: {name}"
    placeholders = ",".join("?" for _ in SIGNAL_SOURCES)
    signals = ",".join("?" for _ in AVAILABILITY_SIGNALS)
    for row in connection.execute(
        f"""
        SELECT source_id, text, product_text FROM observations
        WHERE source_id IN ({placeholders}) AND signal IN ({signals}) AND is_tcg = 1 AND received_at >= ?
        ORDER BY received_at DESC
        """,
        (*SIGNAL_SOURCES, *sorted(AVAILABILITY_SIGNALS), iso(now - SIGNAL_WINDOW)),
    ):
        text = normalize(f"{row['product_text'] or ''} {row['text']}")
        key = next((key for key in set_keys if normalize(key) in text), None)
        if key:
            return f"{row['source_id']} signal: {key}"
    return None


def cadence(
    connection: sqlite3.Connection, stores: list[registry.Store], *, now: dt.datetime,
    set_keys: frozenset[str] | set[str] = frozenset(),
) -> dict[str, int]:
    """Store id -> discovery minutes right now: scored tier, sped up during a drop window."""
    scored = {
        row["store_id"]: (row["effective_tier"], row["discovery_minutes"], row["reason"])
        for row in connection.execute("SELECT store_id, effective_tier, discovery_minutes, reason FROM store_scores")
    }
    window = drop_window(connection, now=now, set_keys=set_keys)
    minutes: dict[str, int] = {}
    for store in stores:
        tier, store_minutes, reason = scored.get(store.store_id, (store.tier, store.discovery_minutes, ""))
        if window and tier in ("hot", "first_pass") and not reason.startswith("failing"):
            store_minutes = min(store_minutes, DROP_WINDOW_MINUTES)
        minutes[store.store_id] = store_minutes
    return minutes


def watched_set_keys(connection: sqlite3.Connection) -> frozenset[str]:
    """Watched set keys for drop windows, without sets the founder excluded."""
    from .. import watchlist
    from . import alerts, match

    policy = watchlist.load_policy()
    context = alerts.watch_context(connection, match.Catalog.from_db(connection), policy)
    excluded = [normalize(term) for term in policy.exclude_terms]
    return frozenset(key for key in context.set_keys if not any(term in normalize(key) for term in excluded))


def render(connection: sqlite3.Connection, *, now: dt.datetime, set_keys=frozenset()) -> str:
    window = drop_window(connection, now=now, set_keys=set_keys)
    lines = [f"Store scores (last {SCORE_WINDOW.days} days). Drop window: {window or 'none'}", ""]
    lines.append(
        f"{'store':<28} {'tier':<10} {'every':>5} {'MSRP now':>8} {'hits':>4} {'new':>4} {'matched':>7} "
        f"{'stock min':>9} {'fail':>7}  reason"
    )
    for row in connection.execute(
        """
        SELECT s.name, c.* FROM store_scores c JOIN stores s USING (store_id)
        ORDER BY c.discovery_minutes, c.msrp_hits DESC, c.msrp_offers_now DESC, s.name
        """
    ):
        median = "-" if row["stock_minutes_median"] is None else f"{row['stock_minutes_median']:.0f}"
        fail = f"{row['failures']}/{row['runs']}"
        lines.append(
            f"{row['name'][:28]:<28} {row['effective_tier']:<10} {row['discovery_minutes']:>4}m {row['msrp_offers_now']:>8} "
            f"{row['msrp_hits']:>4} {row['new_listings']:>4} {row['matched_listings']:>7} {median:>9} {fail:>7}  {row['reason']}"
        )
    return "\n".join(lines) + "\n"
