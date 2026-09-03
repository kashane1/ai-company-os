# TCG Highs and Lows — Pokémon card price screener

**TL;DR** — A local screener for Pokémon singles trading below their recent
highs. Ingests ~900 days of daily TCGplayer market prices from
[tcgcsv.com](https://tcgcsv.com) into SQLite, derives drawdown metrics per card
finish, and serves a filterable web UI. Run `make setup && make build && make serve`,
then open <http://localhost:8787>.

The screener answers: *which cards are X% below their 52-week / 6-month /
3-month high, are still liquid, and have stopped falling?*

---

## Why this exists

No existing app screens the whole catalog by distance from a high. Card apps
show you one card's chart; stock screeners do the filtering but not for cards.
This does the filtering.

## Data source

**tcgcsv.com** — a free, unauthenticated mirror of TCGplayer's price feed with
daily archives going back to **2024-02-08**.

The alternatives were checked before building:

| Source | Status when probed | Verdict |
| --- | --- | --- |
| tcgcsv.com | 200, no auth | **Used.** Only free source with real daily history |
| pokemontcg.io | HTTP 500 | Down, and snapshot-only anyway |
| PkmnPrices | 401 | Real but paid |
| PokeTrace | 401 | Real but paid |
| TCG Price Lookup | 401 | Real but paid |
| PokemonPriceTracker | 404 on documented path | Unverifiable |
| TCGplayer official API | Not granting new access | Unavailable |
| eBay Marketplace Insights | Limited release | Unavailable |

### Two honest limitations

1. **There is no true all-time high.** History starts 2024-02-08, so what the
   UI calls the **recorded peak** is the highest daily market price since then.
   A card that peaked in the 2020–21 boom will show a smaller drawdown than
   reality. This is why the **52-week / 6-month / 3-month highs are the default
   benchmarks** — those windows fit entirely inside the data, so they are exact.
2. **No sales-volume data exists in this feed.** The "minimum 10 sales in 30
   days" liquidity filter is impossible. Three proxies stand in, and are
   labelled as proxies: the **listing spread**, **how many of the last 30 days
   carried a price at all**, and — the most useful of them — **how many distinct
   prices the card actually printed over 90 days**.

## Grain: what one row is

One screener row is **one (card, finish)** pair — a Reverse Holofoil and a 1st
Edition Holofoil of the same card are separate rows, because TCGplayer prices
them separately and averaging them is meaningless.

All prices are **TCGplayer market price · Near Mint · ungraded · English**.
Market price is derived from recent sales, not from the current listing stack —
which is why it, and not the feed's `highPrice`, is the benchmark.

## Layout

```
ingest/
  config.py     paths, category ids, the day-integer epoch
  db.py         tuned SQLite connections
  schema.sql    catalog, price_observations, card_metrics, screener_rows view
  tcgcsv.py     API client + 7z archive reader
  catalog.py    sets/singles sync, single-vs-sealed discrimination
  backfill.py   threaded archive download → single SQLite writer, resumable
  metrics.py    the drawdown math (pure functions, unit tested)
  __main__.py   CLI
api/
  screener.py   filter → SQL, the only place SQL is built
  main.py       FastAPI routes + static file serving
web/            index.html, styles.css, app.js — no build step
tests/          metrics math and query semantics
```

## Setup

```bash
make setup
```

## Build the database

```bash
make build
```

That runs, in order:

```bash
python -m ingest sync-catalog     # ~6s   → 217 sets, ~27,800 singles
python -m ingest backfill         # ~15m  → ~894 days, ~31M observations, ~1.3GB
python -m ingest metrics          # ~2m   → derived screener metrics
```

The backfill is **resumable** — `ingested_days` records every loaded day, so an
interrupted run picks up where it stopped. Archives are streamed and discarded
by default; pass `--keep-cache` to keep the `.7z` files (many GB) when
re-running repeatedly.

For a quick smoke test without the full history:

```bash
python -m ingest backfill --days 120 && python -m ingest metrics
```

## Serve

```bash
make serve      # uvicorn on http://localhost:8787
```

**Sharing a screen.** *Export filters* at the foot of the filter rail copies a
link that reopens the page with the same filters, and puts that link in the
address bar so the tab can be bookmarked or reloaded. The link carries only the
controls that were changed, under the names of the form controls themselves —
`?benchmark=26w&min_discount_pct=40&rarity_mode=exclude&rarities=Common` — so it
stays short and readable, and a default revised later is not frozen into links
already sent. Values a control does not recognise are ignored rather than
applied, so a truncated or hand-edited link degrades to the defaults.

## Keep it current

```bash
python -m ingest daily
```

Catches up any missing archive days, pulls today's live prices from the per-set
endpoints (the current day's archive isn't published until the day rolls over),
and rebuilds metrics. Suitable for a launchd/cron job. Because SQLite runs in
WAL mode, this can run while the API keeps serving.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/screener` | The screener. All filters below. |
| `GET /api/variants/{id}` | One card's metrics plus price history for the chart |
| `GET /api/filters` | Sets, rarities and finishes that actually appear in results |
| `GET /api/meta` | Coverage, freshness, and the caveats the UI renders |
| `GET /docs` | Generated OpenAPI docs |

Screener parameters: `benchmark` (`52w`/`26w`/`13w`/`peak`),
`min_discount_pct`, `max_discount_pct`, `min_price`, `max_price`, `search`,
`group_ids`, `rarities`, `sub_types`, `exclude_group_ids`, `exclude_rarities`,
`exclude_sub_types`, `min_release_year`, `max_release_year`, `card_classes`,
`exclude_card_classes`, `trainer_kinds`, `min_change_7d_pct`,
`max_change_7d_pct`, `min_change_30d_pct`, `max_change_30d_pct`,
`min_history_days`, `min_observations_30d`, `max_spread_pct`,
`min_distinct_prices_90d`, `min_range_position_pct`, `max_range_position_pct`,
`exclude_release_spikes`, `exclude_truncated_peaks`, `exclude_price_outliers`,
`outlier_floor_pct`, `sort`, `descending`, `limit`, `offset`.

The `exclude_*` list parameters are the mirror of the plain lists — say
`exclude_rarities=Common` for "everything but commons". Include and exclude on
the same dimension would return nothing, so the UI sends one or the other.

Defaults are deliberately conservative — `min_price=1`, `min_discount_pct=25`,
`min_history_days=180`, `min_observations_30d=10`, `min_distinct_prices_90d=5`,
`exclude_release_spikes=true`, `exclude_price_outliers=true`. They exist to keep
the first page trustworthy; set them to `0`/`false` to see everything.

Example — cards 40–70% below their 52-week high, $10–50, that have stopped
falling, excluding release-week spikes:

```bash
curl 'http://localhost:8787/api/screener?benchmark=52w&min_discount_pct=40&max_discount_pct=70&min_price=10&max_price=50&min_change_7d_pct=0&exclude_release_spikes=true'
```

## Metric definitions

| Metric | Meaning |
| --- | --- |
| `peak_price` | Highest daily market price **since 2024-02-08**. Not a true ATH. |
| `high_52w` / `26w` / `13w` | Highest daily market price in the trailing window. Exact. |
| `discount_from_*_pct` | Percent below that reference. `60.0` = 60% below. Clamped at 0. |
| `pct_of_52w_range` | 0 = at the 52-week low, 100 = at the high. |
| `change_7d/30d/90d_pct` | Percent change vs the last price at or before N days ago. |
| `spread_pct` | `(high listing − low listing) / market price`. Spans all conditions, so hundreds of percent is normal. |
| `coverage_30d_pct` | Share of the last 30 days that carried a price. Liquidity proxy. |
| `distinct_prices_90d` | Distinct market prices in 90 days. The best liquidity signal here. |
| `median_price_90d` | 90-day median, used to detect an implausible current price. |
| `current_vs_median_90d_pct` | Current price as a share of that median. Under 25% ⇒ treated as a feed error. |
| `peak_within_30d_of_release` | Peak landed in release week. Excluded by default. |
| `peak_is_first_observation` | Peak is our oldest datapoint, so the real peak may be higher. |

### Two data problems found by running it, and what they cost

Both were discovered by inspecting the actual top of the result list, not in
theory. Both are now guarded by default, and both defaults were chosen by
measurement rather than taste.

**1. Bad current prices manufacture fake 99% discounts.** The feed reported
Shining Charizard (Neo Destiny) at `$19.99` after it traded `$250–$2,000` all
year, and Entei Star at `$0.99` after a year in the `$420–$990` range. Sorted by
deepest discount, these *are* the first page. The guard compares the current
price to the card's own 90-day median: a real decline drags the median down with
it, a one-off error cannot. Cards under 25% of their own median are excluded
(`exclude_price_outliers`).

**2. A price can be quoted daily for months without anything selling.**
TCGplayer holds the last market price when there are no sales, so an illiquid
vintage single sits at one value and then steps down hard. Coverage cannot see
this — a frozen price has *perfect* coverage. Counting distinct prices can.
Every implausible survivor sat at 2–4 distinct prices in 90 days; raising the
floor from 5 to 20 removed 400 more rows without changing the top of the list,
so `min_distinct_prices_90d` defaults to **5** — the junk is entirely below it
and anything stricter only costs coverage.

A third, smaller one: sorting by percentage puts `$0.01 → $0.98` bulk commons
above everything real, so `min_price` defaults to **$1**.

### Guards that stop the screener lying

- **Staleness.** A variant whose last price is more than 7 days old is dropped
  rather than quoted as "current".
- **Release spikes**, on by default. Many modern cards spike in release week and
  never return; being 90% below that is normal, not a bargain.
- **Clamped discounts.** A card at a fresh high reports 0%, not a negative
  number that would sort to the top of a "most discounted" list.
- **NULL is not "passes".** A filter on a metric that couldn't be computed
  excludes the row instead of silently admitting it.
- **Recency-biased peak ties.** On tied peaks the latest day wins, so
  "days since peak" reads as *when was it last this expensive*.
- **Implausible current prices**, on by default — see the two data problems above.
- **Frozen quotes**, on by default: a price that never moved is not a market.

## Tests

```bash
make test
```

73 tests covering the drawdown math (window nesting, tie-breaking, staleness,
momentum carry-forward, outlier detection, and that a *genuine* decline is not
mistaken for one), the query layer (every filter, NULL handling, pagination
stability, LIKE-wildcard escaping, parameter binding), catalog single-vs-sealed
discrimination, the write path, and a full ingest → metrics → view pipeline test.

Two bugs these caught before they shipped: searching `%` matched every card
(LIKE wildcards were not escaped), and the read connection was created on one
threadpool thread and used on another, which 500s the moment two requests
overlap — invisible under sequential testing.

## Not investment advice

A card being below a past high is not a prediction. Market prices are estimates
derived from past sales, availability is not guaranteed, and thin markets move
on single transactions.
