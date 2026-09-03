"""Load daily price history from tcgcsv.com archives into price_observations.

Downloads dominate wall-clock, so archives are fetched on a small thread pool
and handed to a single writer thread — SQLite wants one writer, and the parse
step is cheap by comparison (~1.6s per archive).

The job is resumable: `ingested_days` records every day already loaded, so an
interrupted backfill picks up where it stopped.
"""

from __future__ import annotations

import datetime as dt
import queue
import sqlite3
import threading
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from . import catalog, tcgcsv
from .config import ARCHIVE_START_DATE, day_index

DOWNLOAD_WORKERS = 4
# Sentinel pushed once per worker to signal the writer that a producer is done.
_DONE = object()


@dataclass
class BackfillResult:
    days_loaded: int = 0
    days_skipped: int = 0
    days_missing: int = 0
    observations_written: int = 0
    variants_created: int = 0
    failures: list[str] = field(default_factory=list)


def already_ingested_days(connection: sqlite3.Connection) -> set[int]:
    return {row[0] for row in connection.execute("SELECT day FROM ingested_days")}


def known_single_product_ids(connection: sqlite3.Connection) -> set[int]:
    return {row[0] for row in connection.execute("SELECT product_id FROM cards")}


def missing_dates(
    connection: sqlite3.Connection,
    *,
    start: dt.date | None = None,
    end: dt.date | None = None,
) -> list[dt.date]:
    """Dates in [start, end] that have no observations loaded yet."""
    start = max(start or ARCHIVE_START_DATE, ARCHIVE_START_DATE)
    end = end or dt.date.today()
    loaded = already_ingested_days(connection)
    dates: list[dt.date] = []
    cursor = start
    while cursor <= end:
        if day_index(cursor) not in loaded:
            dates.append(cursor)
        cursor += dt.timedelta(days=1)
    return dates


def _write_day(
    connection: sqlite3.Connection,
    date: dt.date,
    rows: list[tcgcsv.PriceRow],
    singles: set[int],
    variant_ids: dict[tuple[int, str], int],
) -> tuple[int, int]:
    """Insert one day's observations. Returns (rows written, variants created)."""
    relevant = [row for row in rows if row.product_id in singles]

    unseen = {
        (row.product_id, row.sub_type)
        for row in relevant
        if (row.product_id, row.sub_type) not in variant_ids
    }
    if unseen:
        catalog.ensure_variants(connection, unseen)
        for key, variant_id in catalog.variant_id_map(connection).items():
            variant_ids[key] = variant_id

    day = day_index(date)
    payload = [
        (
            variant_ids[(row.product_id, row.sub_type)],
            day,
            row.market_price,
            row.low_price,
            row.high_price,
        )
        for row in relevant
        if (row.product_id, row.sub_type) in variant_ids
    ]

    connection.executemany(
        """
        INSERT INTO price_observations (variant_id, day, market_price, low_price, high_price)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(variant_id, day) DO UPDATE SET
            market_price = excluded.market_price,
            low_price    = excluded.low_price,
            high_price   = excluded.high_price
        """,
        payload,
    )
    connection.execute(
        """
        INSERT INTO ingested_days (day, source, row_count, ingested_at)
        VALUES (?, 'archive', ?, ?)
        ON CONFLICT(day) DO UPDATE SET
            source      = excluded.source,
            row_count   = excluded.row_count,
            ingested_at = excluded.ingested_at
        """,
        (day, len(payload), dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")),
    )
    connection.commit()
    return len(payload), len(unseen)


def run_backfill(
    connection: sqlite3.Connection,
    *,
    start: dt.date | None = None,
    end: dt.date | None = None,
    keep_cache: bool = False,
    progress=None,
) -> BackfillResult:
    """Download and load every archive day that is not already present."""
    result = BackfillResult()
    dates = missing_dates(connection, start=start, end=end)
    if not dates:
        if progress:
            progress("nothing to backfill — all days present")
        return result

    singles = known_single_product_ids(connection)
    if not singles:
        raise RuntimeError("catalog is empty — run `sync-catalog` before backfilling")
    variant_ids = catalog.variant_id_map(connection)

    pending: queue.Queue = queue.Queue(maxsize=DOWNLOAD_WORKERS * 2)
    date_queue: queue.Queue = queue.Queue()
    for date in dates:
        date_queue.put(date)

    def download_worker() -> None:
        with httpx.Client(
            timeout=tcgcsv.REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "pokemon-tcg-search/0.1 (+local screener)"},
        ) as client:
            while True:
                try:
                    date = date_queue.get_nowait()
                except queue.Empty:
                    break
                try:
                    archive_path = tcgcsv.download_archive(
                        date, client, keep_cache=keep_cache
                    )
                    if archive_path is None:
                        pending.put((date, None, None))
                        continue
                    rows = list(tcgcsv.read_pokemon_prices_from_archive(archive_path))
                    if not keep_cache:
                        Path(archive_path).unlink(missing_ok=True)
                    pending.put((date, rows, None))
                except Exception as error:  # noqa: BLE001 - reported, not fatal
                    pending.put((date, None, f"{date}: {type(error).__name__}: {error}"))
        pending.put(_DONE)

    workers = [
        threading.Thread(target=download_worker, name=f"tcgcsv-dl-{index}", daemon=True)
        for index in range(min(DOWNLOAD_WORKERS, len(dates)))
    ]
    for worker in workers:
        worker.start()

    finished_workers = 0
    total = len(dates)
    while finished_workers < len(workers):
        item = pending.get()
        if item is _DONE:
            finished_workers += 1
            continue

        date, rows, error = item
        if error:
            result.failures.append(error)
        elif rows is None:
            result.days_missing += 1
        else:
            written, created = _write_day(connection, date, rows, singles, variant_ids)
            result.days_loaded += 1
            result.observations_written += written
            result.variants_created += created

        done = result.days_loaded + result.days_missing + len(result.failures)
        if progress and (done % 20 == 0 or done == total):
            progress(
                f"  backfill {done}/{total} days · "
                f"{result.observations_written:,} observations · "
                f"{result.days_missing} missing · {len(result.failures)} failed"
            )

    for worker in workers:
        worker.join(timeout=5)
    return result


def ingest_today(connection: sqlite3.Connection, *, progress=None) -> BackfillResult:
    """Pull today's live prices from the per-set endpoints.

    Used by the daily refresh: the archive for the current day is not published
    until after the day rolls over, so live endpoints keep the screener current.
    """
    result = BackfillResult()
    singles = known_single_product_ids(connection)
    if not singles:
        raise RuntimeError("catalog is empty — run `sync-catalog` first")
    variant_ids = catalog.variant_id_map(connection)
    today = dt.date.today()

    with httpx.Client(
        base_url=tcgcsv.TCGCSV_BASE,
        timeout=tcgcsv.REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "pokemon-tcg-search/0.1 (+local screener)"},
    ) as client:
        groups = tcgcsv.fetch_groups(client)
        collected: list[tcgcsv.PriceRow] = []
        for index, group in enumerate(groups, start=1):
            try:
                collected.extend(tcgcsv.fetch_group_prices(int(group["groupId"]), client))
            except (httpx.HTTPError, tcgcsv.TcgCsvError) as error:
                result.failures.append(f"set {group.get('groupId')}: {error}")
            if progress and index % 50 == 0:
                progress(f"  live prices {index}/{len(groups)} sets · {len(collected):,} rows")

    written, created = _write_day(connection, today, collected, singles, variant_ids)
    connection.execute(
        "UPDATE ingested_days SET source = 'live' WHERE day = ?", (day_index(today),)
    )
    connection.commit()
    result.days_loaded = 1
    result.observations_written = written
    result.variants_created = created
    return result
