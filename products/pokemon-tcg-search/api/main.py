"""HTTP API for the Pokemon TCG price screener.

Run with:  uvicorn api.main:app --reload --port 8787

The database is opened read-only per request. SQLite in WAL mode lets the
nightly ingest write while the API keeps serving, so a refresh never takes the
site down.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ingest.config import DATABASE_PATH, PRODUCT_ROOT, date_from_day_index, day_index
from ingest.metrics import MAX_STALENESS_DAYS

from .screener import BENCHMARKS, MAX_LIMIT, SORT_COLUMNS, ScreenerFilters, build_query

WEB_DIR = PRODUCT_ROOT / "web"

app = FastAPI(
    title="Pokemon TCG price screener",
    description=(
        "Find Pokemon singles trading below their recent highs. Prices are "
        "TCGplayer market prices for Near Mint, ungraded, English cards."
    ),
    version="1.0.0",
)


def get_connection() -> Any:
    """Yield a read-only connection, closing it when the request finishes."""
    if not DATABASE_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="database not built yet — run `python -m ingest sync-catalog` then `backfill`",
        )
    # check_same_thread=False is required, not merely convenient: FastAPI runs
    # sync dependencies and sync endpoints in a threadpool, and the thread that
    # opens the connection is not guaranteed to be the one that uses or closes
    # it. Safe here because each request gets its own read-only connection and
    # uses it serially — no connection is ever shared between requests.
    connection = sqlite3.connect(
        f"file:{DATABASE_PATH}?mode=ro", uri=True, check_same_thread=False
    )
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


Connection = Annotated[Any, Depends(get_connection)]


def _day_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    return date_from_day_index(int(value)).isoformat()


def _round(value: Any, digits: int = 2) -> Any:
    return round(value, digits) if isinstance(value, (int, float)) else value


def _serialise_row(row: sqlite3.Row, benchmark: str) -> dict[str, Any]:
    """Shape one screener row for the client.

    `discount_pct` and `reference_price` are echoes of whichever benchmark the
    request selected, so the UI renders one column without re-deriving which
    field it asked for.
    """
    discount_column, reference_column, label = BENCHMARKS.get(
        benchmark, BENCHMARKS["52w"]
    )
    data = {key: row[key] for key in row.keys()}

    for key in list(data):
        if key.endswith("_pct") or key.endswith("_price") or key in {"current_price"}:
            data[key] = _round(data[key])

    data["peak_date"] = _day_to_iso(data.pop("peak_day", None))
    data["as_of_date"] = _day_to_iso(data.pop("as_of_day", None))
    data["benchmark"] = benchmark
    data["benchmark_label"] = label
    data["discount_pct"] = data.get(discount_column)
    data["reference_price"] = data.get(reference_column)
    data["peak_is_first_observation"] = bool(data.get("peak_is_first_observation"))
    data["peak_within_30d_of_release"] = bool(data.get("peak_within_30d_of_release"))
    return data


# ---------------------------------------------------------------------------
# Screener
# ---------------------------------------------------------------------------


@app.get("/api/screener", summary="Filter cards by discount from a recent high")
def screener(
    connection: Connection,
    benchmark: str = Query("52w", pattern="^(peak|52w|26w|13w)$"),
    min_discount_pct: float | None = Query(25.0, ge=0, le=100),
    max_discount_pct: float | None = Query(None, ge=0, le=100),
    min_price: float | None = Query(1.0, ge=0),
    max_price: float | None = Query(None, ge=0),
    search: str | None = Query(None, max_length=120),
    group_ids: list[int] = Query(default_factory=list),
    rarities: list[str] = Query(default_factory=list),
    sub_types: list[str] = Query(default_factory=list),
    exclude_group_ids: list[int] = Query(default_factory=list),
    exclude_rarities: list[str] = Query(default_factory=list),
    exclude_sub_types: list[str] = Query(default_factory=list),
    min_release_year: int | None = Query(None, ge=1996, le=2100),
    max_release_year: int | None = Query(None, ge=1996, le=2100),
    card_classes: list[str] = Query(default_factory=list),
    exclude_card_classes: list[str] = Query(default_factory=list),
    trainer_kinds: list[str] = Query(default_factory=list),
    min_change_7d_pct: float | None = None,
    max_change_7d_pct: float | None = None,
    min_change_30d_pct: float | None = None,
    max_change_30d_pct: float | None = None,
    min_history_days: int = Query(180, ge=0),
    min_observations_30d: int = Query(10, ge=0, le=31),
    max_spread_pct: float | None = Query(None, ge=0),
    min_distinct_prices_90d: int = Query(5, ge=0),
    min_range_position_pct: float | None = Query(None, ge=0, le=100),
    max_range_position_pct: float | None = Query(None, ge=0, le=100),
    exclude_release_spikes: bool = True,
    exclude_truncated_peaks: bool = False,
    exclude_price_outliers: bool = True,
    outlier_floor_pct: float = Query(25.0, ge=0, le=100),
    sort: str = Query("discount"),
    descending: bool = True,
    limit: int = Query(50, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    if sort not in SORT_COLUMNS:
        raise HTTPException(
            status_code=422,
            detail=f"unknown sort {sort!r}; expected one of {sorted(SORT_COLUMNS)}",
        )

    filters = ScreenerFilters(
        benchmark=benchmark,
        min_discount_pct=min_discount_pct,
        max_discount_pct=max_discount_pct,
        min_price=min_price,
        max_price=max_price,
        search=search,
        group_ids=group_ids,
        rarities=rarities,
        sub_types=sub_types,
        exclude_group_ids=exclude_group_ids,
        exclude_rarities=exclude_rarities,
        exclude_sub_types=exclude_sub_types,
        min_release_year=min_release_year,
        max_release_year=max_release_year,
        card_classes=card_classes,
        exclude_card_classes=exclude_card_classes,
        trainer_kinds=trainer_kinds,
        min_change_7d_pct=min_change_7d_pct,
        max_change_7d_pct=max_change_7d_pct,
        min_change_30d_pct=min_change_30d_pct,
        max_change_30d_pct=max_change_30d_pct,
        min_history_days=min_history_days,
        min_observations_30d=min_observations_30d,
        max_spread_pct=max_spread_pct,
        min_distinct_prices_90d=min_distinct_prices_90d,
        min_range_position_pct=min_range_position_pct,
        max_range_position_pct=max_range_position_pct,
        exclude_release_spikes=exclude_release_spikes,
        exclude_truncated_peaks=exclude_truncated_peaks,
        exclude_price_outliers=exclude_price_outliers,
        outlier_floor_pct=outlier_floor_pct,
        sort=sort,
        descending=descending,
        limit=limit,
        offset=offset,
    )

    rows_sql, count_sql, params = build_query(filters)
    total = connection.execute(count_sql, params).fetchone()[0]
    rows = connection.execute(rows_sql, params).fetchall()

    return {
        "total": total,
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "benchmark": benchmark,
        "benchmark_label": BENCHMARKS[benchmark][2],
        "results": [_serialise_row(row, benchmark) for row in rows],
    }


# ---------------------------------------------------------------------------
# Card detail
# ---------------------------------------------------------------------------


@app.get("/api/variants/{variant_id}", summary="One card's metrics and price history")
def variant_detail(
    variant_id: int,
    connection: Connection,
    history_days: int = Query(400, ge=7, le=1200),
) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM screener_rows WHERE variant_id = ?", (variant_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="variant not found or has no metrics")

    cutoff = int(row["as_of_day"]) - history_days
    history = connection.execute(
        """
        SELECT day, market_price, low_price, high_price
        FROM price_observations
        WHERE variant_id = ? AND day > ?
        ORDER BY day
        """,
        (variant_id, cutoff),
    ).fetchall()

    detail = _serialise_row(row, "52w")
    detail["history"] = [
        {
            "date": _day_to_iso(point["day"]),
            "market_price": _round(point["market_price"]),
            "low_price": _round(point["low_price"]),
            "high_price": _round(point["high_price"]),
        }
        for point in history
    ]
    return detail


# ---------------------------------------------------------------------------
# Filter options and metadata
# ---------------------------------------------------------------------------


@app.get("/api/filters", summary="Options for the filter controls")
def filter_options(connection: Connection) -> dict[str, Any]:
    """Only values that actually appear in the screener are returned, so the UI
    can never offer a filter that yields zero rows."""
    sets = connection.execute(
        """
        SELECT group_id, set_name AS name, released_on, COUNT(*) AS variant_count
        FROM screener_rows
        GROUP BY group_id, set_name, released_on
        ORDER BY released_on DESC, set_name
        """
    ).fetchall()
    rarities = connection.execute(
        """
        SELECT rarity, COUNT(*) AS variant_count
        FROM screener_rows
        WHERE rarity IS NOT NULL AND rarity <> ''
        GROUP BY rarity
        ORDER BY variant_count DESC
        """
    ).fetchall()
    sub_types = connection.execute(
        """
        SELECT sub_type, COUNT(*) AS variant_count
        FROM screener_rows
        GROUP BY sub_type
        ORDER BY variant_count DESC
        """
    ).fetchall()
    card_classes = connection.execute(
        """
        SELECT card_class, COUNT(*) AS variant_count
        FROM screener_rows
        WHERE card_class IS NOT NULL
        GROUP BY card_class
        ORDER BY variant_count DESC
        """
    ).fetchall()
    trainer_kinds = connection.execute(
        """
        SELECT trainer_kind, COUNT(*) AS variant_count
        FROM screener_rows
        WHERE trainer_kind IS NOT NULL
        GROUP BY trainer_kind
        ORDER BY variant_count DESC
        """
    ).fetchall()
    # The year bounds the UI should offer, taken from the data rather than
    # hardcoded, so the range can never point at years with nothing in them.
    years = connection.execute(
        """
        SELECT MIN(substr(released_on, 1, 4)) AS min_year,
               MAX(substr(released_on, 1, 4)) AS max_year
        FROM screener_rows
        WHERE released_on IS NOT NULL
        """
    ).fetchone()

    return {
        "sets": [dict(row) for row in sets],
        "rarities": [dict(row) for row in rarities],
        "sub_types": [dict(row) for row in sub_types],
        "card_classes": [dict(row) for row in card_classes],
        "trainer_kinds": [dict(row) for row in trainer_kinds],
        "release_years": {
            "min": int(years["min_year"]) if years and years["min_year"] else None,
            "max": int(years["max_year"]) if years and years["max_year"] else None,
        },
        "benchmarks": [
            {"key": key, "label": label} for key, (_, _, label) in BENCHMARKS.items()
        ],
        "sorts": sorted(SORT_COLUMNS),
    }


@app.get("/api/meta", summary="Data coverage and the caveats that go with it")
def meta(connection: Connection) -> dict[str, Any]:
    # Read the span and total from ingested_days, not price_observations.
    # COUNT(*) over 33M WITHOUT ROWID rows scans the whole primary key and took
    # ~5s on every page load; the per-day row counts are already recorded here
    # and sum to exactly the same total.
    span = connection.execute(
        "SELECT MIN(day) AS lo, MAX(day) AS hi, SUM(row_count) AS n FROM ingested_days"
    ).fetchone()
    screener_rows = connection.execute("SELECT COUNT(*) FROM card_metrics").fetchone()[0]
    cards = connection.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    sets_count = connection.execute("SELECT COUNT(*) FROM sets").fetchone()[0]
    days_ingested = connection.execute("SELECT COUNT(*) FROM ingested_days").fetchone()[0]

    history_start = _day_to_iso(span["lo"])
    latest = _day_to_iso(span["hi"])
    recorded_days = (span["hi"] - span["lo"] + 1) if span["lo"] is not None else 0

    return {
        "source": "tcgcsv.com (TCGplayer market prices)",
        "price_basis": "TCGplayer market price · Near Mint · ungraded · English",
        "history_start": history_start,
        "latest_price_date": latest,
        "recorded_days": recorded_days,
        "days_ingested": days_ingested,
        "observation_count": (span["n"] if span else 0) or 0,
        "screener_rows": screener_rows,
        "card_count": cards,
        "set_count": sets_count,
        "staleness_limit_days": MAX_STALENESS_DAYS,
        "caveats": [
            f"Price history begins {history_start}, so the 'recorded peak' is the "
            "highest price since then — not a true all-time high. Cards that "
            "peaked in the 2020-2021 boom will show a smaller drawdown than reality.",
            "The 52-week, 6-month and 3-month highs sit entirely inside our "
            "history, which makes them the defensible benchmarks. They are the default.",
            "TCGplayer market price is derived from recent sales, not from the "
            "current listing stack. It is not a guaranteed buy price.",
            "No sales-volume data is available from this source. Liquidity is "
            "approximated by the bid-ask spread, how many days of the last 30 "
            "carried a price at all, and how often the price actually moved.",
            "The feed sometimes reports a market price far out of line with a "
            "card's own trading range — a $600 vintage single quoting $0.99. That "
            "fake 99% discount would top the list, so cards priced under 25% of "
            "their own 90-day median are filtered out by default as data errors.",
            "TCGplayer holds the last market price when nothing sells, so an "
            "illiquid vintage card can sit at one price for months and then step "
            "down sharply. Cards whose price never moved in the last 90 days are "
            "filtered out by default, because the high they are measured against "
            "may never have been a price anything traded at.",
        ],
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "checked_at": dt.datetime.now(dt.timezone.utc).isoformat()}


# ---------------------------------------------------------------------------
# Static site
# ---------------------------------------------------------------------------

if WEB_DIR.exists():
    # `no-cache` means "revalidate before use", not "do not store". Without it
    # the responses carry an ETag but no freshness directive, so browsers fall
    # back to heuristic caching and keep serving a stale app.js after an edit.
    # Revalidation costs one conditional request and answers 304.
    _NO_CACHE = {"Cache-Control": "no-cache"}

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html", headers=_NO_CACHE)

    class RevalidatingStaticFiles(StaticFiles):
        def file_response(self, *args: Any, **kwargs: Any) -> Any:
            response = super().file_response(*args, **kwargs)
            response.headers.update(_NO_CACHE)
            return response

    app.mount("/", RevalidatingStaticFiles(directory=WEB_DIR, html=True), name="web")
