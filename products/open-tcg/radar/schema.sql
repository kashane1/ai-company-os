-- OpenTCG radar schema. Idempotent: every statement is safe to re-run.

-- Source registry and health. Rows are seeded from radar/sources.py.
CREATE TABLE IF NOT EXISTS sources (
    source_id            TEXT PRIMARY KEY,
    tier                 TEXT NOT NULL,        -- 'S' shippable candidate | 'L' lab-only
    kind                 TEXT NOT NULL,        -- 'poll' | 'stream' | 'inbox' | 'manual'
    cadence_s            INTEGER NOT NULL,
    enabled              INTEGER NOT NULL,
    note                 TEXT,
    last_run_at          TEXT,
    last_success_at      TEXT,
    last_error           TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0
);

-- TCGplayer groups (sets) as mirrored by tcgcsv.
CREATE TABLE IF NOT EXISTS catalog_groups (
    group_id                   INTEGER PRIMARY KEY,
    name                       TEXT NOT NULL,
    abbreviation               TEXT,
    published_on               TEXT,          -- ISO date
    modified_on                TEXT,          -- latest tcgcsv modifiedOn seen
    products_synced_modified_on TEXT          -- modifiedOn at the last product sync
);

-- Canonical sealed products. product_id is the TCGplayer product id.
CREATE TABLE IF NOT EXISTS products (
    product_id         INTEGER PRIMARY KEY,
    group_id           INTEGER NOT NULL REFERENCES catalog_groups(group_id),
    name               TEXT NOT NULL,
    product_type       TEXT NOT NULL,
    exclusive_retailer TEXT,
    release_on         TEXT,                  -- ISO date
    is_presale         INTEGER NOT NULL DEFAULT 0,
    url                TEXT,
    first_seen_at      TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS products_release_idx ON products(release_on);

-- One TCGplayer market/low price per product per day.
CREATE TABLE IF NOT EXISTS price_points (
    product_id   INTEGER NOT NULL REFERENCES products(product_id),
    day          TEXT NOT NULL,               -- ISO date
    market_price REAL,
    low_price    REAL,
    PRIMARY KEY (product_id, day)
) WITHOUT ROWID;

-- Distributor release list rows (e.g. Southern Hobby).
CREATE TABLE IF NOT EXISTS distributor_items (
    source_id     TEXT NOT NULL,
    item_key      TEXT NOT NULL,
    name          TEXT NOT NULL,
    release_on    TEXT,
    order_due_on  TEXT,
    url           TEXT,
    first_seen_at TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    PRIMARY KEY (source_id, item_key)
);

-- News feed items (e.g. PokeBeach front page).
CREATE TABLE IF NOT EXISTS news_items (
    source_id       TEXT NOT NULL,
    item_key        TEXT NOT NULL,
    title           TEXT NOT NULL,
    link            TEXT,
    published_at    TEXT,
    is_product_news INTEGER NOT NULL DEFAULT 0,
    first_seen_at   TEXT NOT NULL,
    PRIMARY KEY (source_id, item_key)
);

-- "When" events. The unique key makes every detector safe to re-run.
CREATE TABLE IF NOT EXISTS calendar_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id    TEXT NOT NULL,
    kind         TEXT NOT NULL,   -- sku_added | release_date_changed | distributor_listed | order_due_changed | news_posted
    subject_key  TEXT NOT NULL,
    subject_text TEXT NOT NULL,
    value        TEXT NOT NULL DEFAULT '',
    product_id   INTEGER,
    detected_at  TEXT NOT NULL,
    UNIQUE (source_id, kind, subject_key, value)
);
CREATE INDEX IF NOT EXISTS calendar_events_detected_idx ON calendar_events(detected_at);

-- "Now" observations from alert sources (Bluesky posts, alert emails, manual log).
CREATE TABLE IF NOT EXISTS observations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id     TEXT NOT NULL,
    external_id   TEXT NOT NULL,           -- e.g. at:// URI, Message-ID
    author        TEXT,
    text          TEXT NOT NULL,
    signal        TEXT NOT NULL,           -- in_stock | preorder | drop | queue | invites | drawing_* | cancelled | event | other
    retailer      TEXT,
    product_text  TEXT,
    price         REAL,
    url           TEXT,
    is_tcg        INTEGER NOT NULL,
    watch_matches TEXT NOT NULL DEFAULT '[]',  -- JSON list of watchlist item names
    source_time   TEXT,                    -- when the source says it happened
    received_at   TEXT NOT NULL,           -- when the radar saw it
    UNIQUE (source_id, external_id)
);
CREATE INDEX IF NOT EXISTS observations_received_idx ON observations(received_at);

-- Resume points for streaming sources.
CREATE TABLE IF NOT EXISTS stream_cursors (
    source_id  TEXT PRIMARY KEY,
    cursor     INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

-- A restock episode: one product at one retailer becoming available, however
-- many sources report it. The first report opens it; later ones record lag.
CREATE TABLE IF NOT EXISTS episodes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_key       TEXT NOT NULL,
    watch_item        TEXT,                 -- watchlist item name, when matched
    retailer          TEXT,
    family            TEXT NOT NULL,        -- availability | announcement
    first_signal      TEXT NOT NULL,
    product_text      TEXT NOT NULL,
    opened_at         TEXT NOT NULL,
    last_seen_at      TEXT NOT NULL,
    first_source_id   TEXT NOT NULL,
    verdict           TEXT                  -- real | false, set by the founder
);
CREATE INDEX IF NOT EXISTS episodes_key_idx ON episodes(episode_key, last_seen_at);

CREATE TABLE IF NOT EXISTS episode_observations (
    episode_id     INTEGER NOT NULL REFERENCES episodes(id),
    observation_id INTEGER NOT NULL REFERENCES observations(id),
    source_id      TEXT NOT NULL,
    seen_at        TEXT NOT NULL,
    lag_s          INTEGER NOT NULL,        -- seconds after the episode opened
    PRIMARY KEY (episode_id, observation_id)
);

-- Notification outbox. The unique key is the dedupe guarantee.
CREATE TABLE IF NOT EXISTS notifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key TEXT NOT NULL UNIQUE,
    episode_id INTEGER REFERENCES episodes(id),
    channel    TEXT NOT NULL,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status     TEXT NOT NULL,               -- sent | failed
    error      TEXT
);

-- Independent stores (stores.toml) and their fetch health. Registry fields
-- are refreshed from the TOML on every run; health columns are runtime only.
CREATE TABLE IF NOT EXISTS stores (
    store_id             TEXT PRIMARY KEY,
    name                 TEXT NOT NULL,
    domain               TEXT NOT NULL,
    platform             TEXT NOT NULL,       -- 'shopify_json' in the pilot
    tier                 TEXT NOT NULL,
    trust                TEXT NOT NULL,
    baseline_at          TEXT,                -- first completed full sweep
    last_discovery_at    TEXT,
    last_full_sweep_at   TEXT,
    last_success_at      TEXT,
    last_error           TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    robots_checked_at    TEXT,
    is_robots_allowed    INTEGER,
    last_sweep_pages     INTEGER,
    is_last_sweep_truncated INTEGER NOT NULL DEFAULT 0
);

-- One row per Pokémon store listing variant. Only Pokémon listings are kept.
CREATE TABLE IF NOT EXISTS store_listings (
    store_id           TEXT NOT NULL REFERENCES stores(store_id),
    variant_id         INTEGER NOT NULL,      -- Shopify variant id
    shop_product_id    INTEGER NOT NULL,
    handle             TEXT NOT NULL,
    title              TEXT NOT NULL,
    variant_title      TEXT,
    vendor             TEXT,
    url                TEXT NOT NULL,
    listed_at          TEXT,                  -- the store's created_at
    first_seen_at      TEXT NOT NULL,
    last_seen_at       TEXT NOT NULL,
    is_baseline        INTEGER NOT NULL,      -- seen before the store's first full sweep finished
    price_cents        INTEGER,
    compare_at_cents   INTEGER,
    is_available       INTEGER NOT NULL,
    language           TEXT NOT NULL,         -- 'en' | 'ja' | 'ko' | 'zh' | ...
    match_status       TEXT NOT NULL,         -- 'exact' | 'ambiguous' | 'unmatched' | 'excluded'
    match_reason       TEXT,
    catalog_product_id INTEGER REFERENCES products(product_id),
    PRIMARY KEY (store_id, variant_id)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS store_listings_product_idx ON store_listings(catalog_product_id);

-- A row only when a listing first appears or its price, compare-at price or
-- availability changes, so history stays small however often stores are polled.
CREATE TABLE IF NOT EXISTS listing_snapshots (
    store_id         TEXT NOT NULL,
    variant_id       INTEGER NOT NULL,
    observed_at      TEXT NOT NULL,
    change           TEXT NOT NULL,           -- 'first_seen' | 'price' | 'availability' | 'price_and_availability'
    price_cents      INTEGER,
    compare_at_cents INTEGER,
    is_available     INTEGER NOT NULL,
    PRIMARY KEY (store_id, variant_id, observed_at),
    FOREIGN KEY (store_id, variant_id) REFERENCES store_listings(store_id, variant_id)
) WITHOUT ROWID;

-- Sealed-collection discovery (weekly). A candidate is selected when its
-- first page is mostly sealed Pokémon product; daily sweeps read only the
-- selected collections instead of the whole catalog.
CREATE TABLE IF NOT EXISTS store_collections (
    store_id      TEXT NOT NULL REFERENCES stores(store_id),
    handle        TEXT NOT NULL,
    title         TEXT,
    sampled_count INTEGER NOT NULL,          -- Pokémon products on the first page
    sealed_count  INTEGER NOT NULL,          -- of those, not excluded by the matcher
    is_selected   INTEGER NOT NULL,
    checked_at    TEXT NOT NULL,
    PRIMARY KEY (store_id, handle)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS store_collection_checks (
    store_id        TEXT PRIMARY KEY REFERENCES stores(store_id),
    checked_at      TEXT NOT NULL,
    candidate_count INTEGER NOT NULL,
    selected_count  INTEGER NOT NULL,
    error           TEXT
);
