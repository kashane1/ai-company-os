-- tcg-inventory — what I own, where it is, and what it is worth.
--
-- This database is SOURCE OF TRUTH and cannot be rebuilt from anything else.
-- It is deliberately separate from pokemon-tcg-search's pokemon.db, which is a
-- derived market-data store with a `make clean-db` target that deletes it. The
-- catalog is attached read-only as `catalog` and joined on product_id /
-- variant_id; nothing here ever writes to it.

PRAGMA foreign_keys = ON;


-- ─── Reference data ──────────────────────────────────────────────────────────

-- Card condition. TCGCSV carries no condition dimension — its prices are per
-- *finish* (Normal / Holofoil), not per *condition* — so a condition price is
-- derived by haircutting the NM market price. These multipliers are market
-- convention as a starting point and should be re-fit from real sales once
-- there are enough of them; `is_fitted` marks a row that has been.
CREATE TABLE conditions (
    condition_code  TEXT    PRIMARY KEY,   -- NM, LP, MP, HP, DMG
    label           TEXT    NOT NULL,
    sort_order      INTEGER NOT NULL,
    nm_multiplier   REAL    NOT NULL,      -- price as a fraction of NM market
    is_fitted       INTEGER NOT NULL DEFAULT 0,
    note            TEXT
);

-- A marketplace, and everything needed to compute net proceeds and capacity on
-- it. These are data, not constants in code, because every one of them changes:
-- fee rates get revised, and the caps move as the account levels up.
--
-- The caps are the binding constraint at low seller levels. TCGplayer Level 1
-- allows 100 listings / $1,000 of listed value / $500 per item; a young eBay
-- account allows roughly 10 new listings or $500 per month. Both are account
-- specific — read the real numbers off the Seller Portal and Seller Hub.
CREATE TABLE channels (
    channel                 TEXT    PRIMARY KEY,   -- tcgplayer, ebay
    label                   TEXT    NOT NULL,
    is_enabled              INTEGER NOT NULL DEFAULT 1,

    -- Economics
    fee_rate                REAL    NOT NULL,      -- 0.1325 = 13.25%
    order_fee_cents         INTEGER NOT NULL,      -- charged per ORDER, not per card
    ship_cost_cents         INTEGER NOT NULL,
    materials_cents         INTEGER NOT NULL,

    -- eBay charges a smaller per-order fee on small orders ($0.30 at or under
    -- $10, $0.40 above). TCGplayer charges one flat fee, so these stay NULL
    -- there and order_fee_cents applies to every order.
    small_order_fee_cents   INTEGER,
    small_order_max_cents   INTEGER,

    -- Listing carrying cost, which is not a per-sale cost. eBay's Good 'Til
    -- Cancelled listings renew once per calendar month and the insertion fee
    -- is charged again on every renewal, so a monthly free allowance is really
    -- a cap on CONCURRENT listings: hold 300 listings against a 250 allowance
    -- and you pay for 50 of them every month until they sell.
    free_listings_per_period INTEGER,              -- NULL = no allowance to model
    insertion_fee_cents      INTEGER NOT NULL DEFAULT 0,  -- per listing per renewal, beyond the allowance

    -- Labor. The difference between these two numbers is most of the reason a
    -- cheap card belongs on one platform and not the other: TCGplayer lists
    -- against a stock image, eBay needs photos, a title and item specifics.
    minutes_to_list         REAL    NOT NULL,
    minutes_to_ship         REAL    NOT NULL,

    -- Capacity. NULL means no limit.
    max_listing_count       INTEGER,
    max_listed_value_cents  INTEGER,
    max_item_price_cents    INTEGER,
    cap_period              TEXT    NOT NULL DEFAULT 'concurrent',  -- concurrent | monthly

    note                    TEXT
);

-- Free-form config that does not deserve its own table.
CREATE TABLE settings (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL,
    note   TEXT
);


-- ─── Acquisitions and copies ─────────────────────────────────────────────────

-- A lot you bought: one collection, one box, one trade. Cost basis starts here
-- and is allocated down to the individual copies, because you almost never buy
-- a single card at a known price.
CREATE TABLE acquisitions (
    acquisition_id    INTEGER PRIMARY KEY,
    acquired_on       TEXT    NOT NULL,            -- ISO date
    source            TEXT,                        -- who you bought it from
    total_cost_cents  INTEGER NOT NULL,
    note              TEXT,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ONE physical card. Identity only — never state.
--
-- Where a copy is and whether it is listed are NOT columns here; they are
-- projections of `events`. A mutable `status` column is the thing that silently
-- goes wrong when a webhook fires twice, and it cannot answer "why is this card
-- in the outbound tray?" six weeks later.
--
-- product_id is denormalized alongside variant_id on purpose: variant_id is an
-- AUTOINCREMENT surrogate in the catalog database, so a full catalog rebuild
-- can renumber it. product_id is TCGplayer's own id and is stable.
CREATE TABLE copies (
    copy_id         INTEGER PRIMARY KEY,
    variant_id      INTEGER NOT NULL,              -- catalog.card_variants
    product_id      INTEGER NOT NULL,              -- TCGplayer product id (stable)
    condition_code  TEXT    NOT NULL REFERENCES conditions(condition_code),
    language        TEXT    NOT NULL DEFAULT 'EN',
    acquisition_id  INTEGER REFERENCES acquisitions(acquisition_id),
    cost_cents      INTEGER,                       -- allocated share of the lot
    note            TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX copies_variant_idx  ON copies(variant_id);
CREATE INDEX copies_product_idx  ON copies(product_id);


-- ─── The ledger ──────────────────────────────────────────────────────────────

-- Every state a copy can be in, and the physical container that holds it.
-- The invariant worth protecting: every state has exactly one container, and
-- every container maps to exactly one state. A card that can sit somewhere with
-- no corresponding state is a card the ledger will eventually be wrong about.
CREATE TABLE copy_states (
    state       TEXT PRIMARY KEY,
    container   TEXT NOT NULL,       -- where it physically lives in this state
    is_terminal INTEGER NOT NULL DEFAULT 0,
    note        TEXT
);

CREATE TABLE event_kinds (
    kind             TEXT PRIMARY KEY,
    resulting_state  TEXT REFERENCES copy_states(state),  -- NULL = no state change
    frees_slot       INTEGER NOT NULL DEFAULT 0,
    note             TEXT
);

-- Append-only. Nothing in here is ever updated or deleted; a mistake is
-- corrected by appending the correcting event.
--
-- idempotency_key is the single most important column in this schema. Order
-- notifications arrive as eBay webhooks and TCGplayer emails, both of which
-- will be delivered twice sooner or later. A UNIQUE key means a replayed
-- notification is a no-op at the database level rather than a phantom second
-- sale that decrements stock you still own.
CREATE TABLE events (
    event_id         INTEGER PRIMARY KEY,
    copy_id          INTEGER NOT NULL REFERENCES copies(copy_id),
    kind             TEXT    NOT NULL REFERENCES event_kinds(kind),
    occurred_at      TEXT    NOT NULL,
    channel          TEXT    REFERENCES channels(channel),
    slot_number      INTEGER,
    price_cents      INTEGER,
    external_ref     TEXT,                  -- order id, listing id
    detail           TEXT,                  -- JSON, for anything not above
    idempotency_key  TEXT    UNIQUE,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX events_copy_idx      ON events(copy_id, occurred_at);
CREATE INDEX events_kind_idx      ON events(kind);
CREATE INDEX events_occurred_idx  ON events(occurred_at);
CREATE INDEX events_external_idx  ON events(external_ref);


-- ─── Physical storage ────────────────────────────────────────────────────────

-- A slot is a permanent address in a binder. Cards move; slot numbers never do.
-- Page and pocket are derived from slot_number and pockets_per_page rather than
-- stored, so re-sleeving into different pages is a config change, not a migration.
--
-- Slots are reused. When a card is pulled the slot returns to the free list and
-- the next card listed drops into it, which keeps the binder dense and bounded
-- instead of growing holes forever.
CREATE TABLE binders (
    binder_name      TEXT    PRIMARY KEY,
    pockets_per_page INTEGER NOT NULL DEFAULT 9,
    first_slot       INTEGER NOT NULL,
    last_slot        INTEGER NOT NULL,
    note             TEXT
);


-- ─── Listings ────────────────────────────────────────────────────────────────

-- Current and historical listings. This is a projection maintained alongside
-- `events` — every row here has corresponding ledger events. It exists because
-- "what is live right now, and at what price" is asked constantly and
-- reconstructing it from the log every time is wasteful.
--
-- A NULL ended_at means live.
CREATE TABLE listings (
    listing_id        INTEGER PRIMARY KEY,
    copy_id           INTEGER NOT NULL REFERENCES copies(copy_id),
    channel           TEXT    NOT NULL REFERENCES channels(channel),
    external_ref      TEXT,                  -- marketplace listing id, once known
    -- What the listing is actually called on the marketplace. eBay's sale
    -- notification carries no item number, so the title is the only thing
    -- tying a sale email back to the copy that sold.
    listing_title     TEXT,
    list_price_cents  INTEGER NOT NULL,
    listed_at         TEXT    NOT NULL,
    ended_at          TEXT,
    end_reason        TEXT                   -- sold | delisted | expired | oversold
);

CREATE INDEX listings_copy_idx     ON listings(copy_id);
CREATE INDEX listings_live_idx     ON listings(channel, ended_at);

-- Every price change, so "why is this card at $3?" is always answerable.
CREATE TABLE price_changes (
    price_change_id  INTEGER PRIMARY KEY,
    listing_id       INTEGER NOT NULL REFERENCES listings(listing_id),
    changed_at       TEXT    NOT NULL,
    from_cents       INTEGER NOT NULL,
    to_cents         INTEGER NOT NULL,
    reason           TEXT    NOT NULL,       -- which rule fired
    was_auto_applied INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX price_changes_listing_idx ON price_changes(listing_id, changed_at);


-- ─── Photos ──────────────────────────────────────────────────────────────────

-- Photos belong to a COPY, not to a card. A stock image cannot defend a
-- not-as-described claim; a full-resolution shot of the actual card at intake
-- can. `original_path` is kept forever for exactly that reason, while
-- `listing_path` is the resized derivative that goes to eBay.
CREATE TABLE photos (
    photo_id       INTEGER PRIMARY KEY,
    copy_id        INTEGER NOT NULL REFERENCES copies(copy_id),
    shot           TEXT    NOT NULL,         -- front | back | angled
    original_path  TEXT    NOT NULL,
    listing_path   TEXT,
    captured_at    TEXT    NOT NULL,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX photos_copy_idx ON photos(copy_id, shot);



-- Views live in views.sql; `initialize` recreates them on every run.
