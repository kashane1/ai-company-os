-- Pokemon TCG price screener — SQLite schema.
--
-- Grain notes, because the whole product depends on getting these right:
--
--   * A "card" is one TCGplayer product in category 3 (Pokemon, English).
--   * A "variant" is one (card, finish) pair — Normal, Holofoil, Reverse
--     Holofoil, 1st Edition, etc. TCGplayer prices each finish separately, so
--     the variant is the unit we screen on. Screening at the card level would
--     silently mix a $4 Reverse Holo with a $400 1st Edition Holo.
--   * Condition is NOT a dimension here. TCGplayer's group price feed reports
--     one price per (product, finish), which tracks Near Mint. Anything the UI
--     says about condition must say Near Mint.
--   * `market_price` is TCGplayer's own sales-derived market price, not a
--     listing price. That is why it is the benchmark rather than `high_price`,
--     which is only the top of the current listing stack.
--
-- Dates are stored as `day`: an integer count of days since DAY_EPOCH
-- (2024-01-01, see ingest/config.py). At ~40M observations this saves roughly
-- 300MB over ISO text. Convert with day_index()/date_from_day_index().

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- ---------------------------------------------------------------------------
-- Catalog
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sets (
    group_id         INTEGER PRIMARY KEY,
    name             TEXT    NOT NULL,
    abbreviation     TEXT,
    released_on      TEXT,             -- ISO date; TCGplayer `publishedOn`
    is_supplemental  INTEGER NOT NULL DEFAULT 0
);

-- Column order here matches what ALTER TABLE ADD COLUMN produces on an
-- existing database (see _migrate_catalog in db.py), so a freshly built
-- catalog and a migrated one are identical.
CREATE TABLE IF NOT EXISTS cards (
    product_id     INTEGER PRIMARY KEY,
    group_id       INTEGER NOT NULL REFERENCES sets(group_id),
    name           TEXT    NOT NULL,
    clean_name     TEXT,
    number         TEXT,               -- collector number, e.g. "006/165"
    rarity         TEXT,
    card_type      TEXT,               -- energy type, e.g. "Fire"
    image_url      TEXT,
    tcgplayer_url  TEXT,

    -- Raw type signals from extendedData, kept because `card_type` alone is
    -- too sparse to classify on: 295 cards have none. See ingest/classify.py
    -- for what each field actually contains.
    hp             INTEGER,            -- Pokemon HP; the feed sends 0 for non-Pokemon
    stage          TEXT,               -- "Basic"/"Stage 1"/... or, for non-Pokemon, their own class

    -- Derived by ingest/classify.py. NULL only if the feed gave no signal.
    card_class     TEXT,               -- Pokemon | Trainer | Energy
    trainer_kind   TEXT                -- Item | Supporter | Stadium | Tool | Technical Machine
);

CREATE INDEX IF NOT EXISTS cards_group_idx  ON cards(group_id);
CREATE INDEX IF NOT EXISTS cards_name_idx   ON cards(name);
CREATE INDEX IF NOT EXISTS cards_rarity_idx ON cards(rarity);
CREATE INDEX IF NOT EXISTS cards_class_idx  ON cards(card_class);

-- Release year filters compare on this as ISO text ('2015-01-01' <= x), which
-- sorts correctly and can use the index.
CREATE INDEX IF NOT EXISTS sets_released_idx ON sets(released_on);

CREATE TABLE IF NOT EXISTS card_variants (
    variant_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL REFERENCES cards(product_id),
    sub_type    TEXT    NOT NULL,      -- finish: Normal, Holofoil, ...
    UNIQUE (product_id, sub_type)
);

CREATE INDEX IF NOT EXISTS card_variants_product_idx ON card_variants(product_id);

-- ---------------------------------------------------------------------------
-- Price history
-- ---------------------------------------------------------------------------

-- One row per variant per day. WITHOUT ROWID clusters rows by
-- (variant_id, day), which makes a single card's history one contiguous read
-- and drops the redundant rowid index.
CREATE TABLE IF NOT EXISTS price_observations (
    variant_id    INTEGER NOT NULL,
    day           INTEGER NOT NULL,
    market_price  REAL,
    low_price     REAL,
    high_price    REAL,
    PRIMARY KEY (variant_id, day)
) WITHOUT ROWID;

-- Which archive days have been fully ingested, so backfill can resume.
CREATE TABLE IF NOT EXISTS ingested_days (
    day          INTEGER PRIMARY KEY,
    source       TEXT    NOT NULL,     -- 'archive' | 'live'
    row_count    INTEGER NOT NULL,
    ingested_at  TEXT    NOT NULL
);

-- ---------------------------------------------------------------------------
-- Derived screener metrics (rebuilt by ingest/metrics.py)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS card_metrics (
    variant_id                  INTEGER PRIMARY KEY,

    as_of_day                   INTEGER NOT NULL,
    current_price               REAL    NOT NULL,

    -- Peaks. `peak_price` is the highest daily market price in our recorded
    -- window, which begins 2024-02-08 — NOT a true all-time high. The UI must
    -- say "recorded peak", and window highs below are the defensible metrics.
    peak_price                  REAL,
    peak_day                    INTEGER,
    high_52w                    REAL,
    high_26w                    REAL,
    high_13w                    REAL,
    low_52w                     REAL,

    -- Discounts, as percent 0..100. 60.0 means "60% below that high".
    discount_from_peak_pct      REAL,
    discount_from_52w_high_pct  REAL,
    discount_from_26w_high_pct  REAL,
    discount_from_13w_high_pct  REAL,

    -- Where the current price sits in the 52-week range: 0 = at the low,
    -- 100 = at the high. The "is this cheap right now" one-number summary.
    pct_of_52w_range            REAL,

    -- Momentum, percent change vs N days ago.
    change_7d_pct               REAL,
    change_30d_pct              REAL,
    change_90d_pct              REAL,

    -- History quality. A 70% discount off two observations is noise.
    observation_count           INTEGER NOT NULL,
    observation_count_30d       INTEGER NOT NULL,
    first_day                   INTEGER NOT NULL,
    history_days                INTEGER NOT NULL,
    days_since_peak             INTEGER,

    -- Liquidity proxies. TCGCSV carries no sales counts, so these stand in:
    -- a tight spread and continuous daily listings imply an active market.
    spread_pct                  REAL,
    coverage_30d_pct            REAL,

    -- Price *movement*, the strongest liquidity signal available here.
    -- TCGplayer pins market price when nothing sells, so a vintage single can
    -- report a price every day for months without a single transaction, then
    -- step down hard when one finally lands. Counting days where the price
    -- actually moved separates a live market from a stale quote — coverage
    -- alone cannot, because a frozen price still has full coverage.
    distinct_prices_90d         INTEGER NOT NULL DEFAULT 0,
    days_since_price_change     INTEGER,

    -- Bad-current-price guard. The feed occasionally reports a market price
    -- wildly out of line with the card's own trading range (a $600 vintage
    -- single quoting $0.99). That produces a fake 99% discount which, sorted
    -- by deepest discount, lands at the very top of the screener. Comparing
    -- against a 90-day median catches it: one bad day, or even a bad month,
    -- cannot drag a 90-day median, so a current price far below it is a data
    -- artifact rather than a crash. A real decline moves the median with it.
    median_price_90d            REAL,
    current_vs_median_90d_pct   REAL,

    -- Release-spike guards. Many modern cards peak in release week at a price
    -- they never revisit; "80% below ATH" is meaningless for those.
    peak_is_first_observation   INTEGER NOT NULL DEFAULT 0,
    peak_within_30d_of_release  INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (variant_id) REFERENCES card_variants(variant_id)
);

CREATE INDEX IF NOT EXISTS metrics_peak_disc_idx  ON card_metrics(discount_from_peak_pct);
CREATE INDEX IF NOT EXISTS metrics_52w_disc_idx   ON card_metrics(discount_from_52w_high_pct);
CREATE INDEX IF NOT EXISTS metrics_26w_disc_idx   ON card_metrics(discount_from_26w_high_pct);
CREATE INDEX IF NOT EXISTS metrics_price_idx      ON card_metrics(current_price);
CREATE INDEX IF NOT EXISTS metrics_range_idx      ON card_metrics(pct_of_52w_range);
CREATE INDEX IF NOT EXISTS metrics_movement_idx   ON card_metrics(distinct_prices_90d);

-- Denormalized join target for the screener. Keeping this as a view means the
-- API never hand-writes the four-table join and can't drift from it.
DROP VIEW IF EXISTS screener_rows;
CREATE VIEW screener_rows AS
SELECT
    m.variant_id,
    c.product_id,
    c.name              AS card_name,
    c.number            AS card_number,
    c.rarity,
    c.card_type,
    c.hp,
    c.stage,
    c.card_class,
    c.trainer_kind,
    c.image_url,
    c.tcgplayer_url,
    v.sub_type,
    s.group_id,
    s.name              AS set_name,
    s.abbreviation      AS set_abbreviation,
    s.released_on,
    m.current_price,
    m.peak_price,
    m.peak_day,
    m.high_52w,
    m.high_26w,
    m.high_13w,
    m.low_52w,
    m.discount_from_peak_pct,
    m.discount_from_52w_high_pct,
    m.discount_from_26w_high_pct,
    m.discount_from_13w_high_pct,
    m.pct_of_52w_range,
    m.change_7d_pct,
    m.change_30d_pct,
    m.change_90d_pct,
    m.observation_count,
    m.observation_count_30d,
    m.history_days,
    m.days_since_peak,
    m.spread_pct,
    m.coverage_30d_pct,
    m.distinct_prices_90d,
    m.days_since_price_change,
    m.median_price_90d,
    m.current_vs_median_90d_pct,
    m.peak_is_first_observation,
    m.peak_within_30d_of_release,
    m.as_of_day
FROM card_metrics  m
JOIN card_variants v ON v.variant_id = m.variant_id
JOIN cards         c ON c.product_id = v.product_id
JOIN sets          s ON s.group_id   = c.group_id;
