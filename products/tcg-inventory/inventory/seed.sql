-- Reference data. Safe to re-run: every insert is OR IGNORE, so seeding an
-- existing database leaves tuned values (fitted condition multipliers, real
-- account caps) alone.


-- ─── Conditions ──────────────────────────────────────────────────────────────
-- Starting multipliers are market convention, not measured. Re-fit them from
-- real sales once there is enough history and set is_fitted = 1.

INSERT OR IGNORE INTO conditions (condition_code, label, sort_order, nm_multiplier, note) VALUES
    ('NM',  'Near Mint',       1, 1.00, 'Reference condition. TCGCSV market price is NM.'),
    ('LP',  'Lightly Played',  2, 0.85, 'Convention, unfitted'),
    ('MP',  'Moderately Played', 3, 0.70, 'Convention, unfitted'),
    ('HP',  'Heavily Played',  4, 0.55, 'Convention, unfitted'),
    ('DMG', 'Damaged',         5, 0.40, 'Convention, unfitted');


-- ─── Copy states ─────────────────────────────────────────────────────────────
-- One state per physical container, one container per state. Note that being
-- listed is NOT a state: a copy can be live on both marketplaces at once, so
-- listing status lives in `listings` where it can be many-per-copy. What the
-- state machine tracks is strictly where the physical card is.

INSERT OR IGNORE INTO copy_states (state, container, is_terminal, note) VALUES
    ('collection', 'Collection box',  0, 'Owned, not in the selling rotation'),
    ('in_binder',  'Listing binder',  0, 'Holds a slot; may be live on 0, 1 or 2 channels'),
    ('outbound',   'Outbound tray',   0, 'Pulled against an order, not yet shipped'),
    ('in_transit', 'Shipped',         0, 'Handed to the carrier'),
    ('sold',       'Gone',            1, 'Delivered'),
    ('returned',   'Returns tray',    0, 'Came back; needs regrade before restocking'),
    ('lost',       'Gone',            1, 'Lost, damaged beyond sale, or written off');


-- ─── Event kinds ─────────────────────────────────────────────────────────────
-- resulting_state NULL means the event records something real but does not move
-- the card: listing, repricing and selling all leave it sitting in its slot.

INSERT OR IGNORE INTO event_kinds (kind, resulting_state, frees_slot, note) VALUES
    ('acquired',      'collection', 0, 'Entered inventory'),
    ('slotted',       'in_binder',  0, 'Placed in the listing binder; assigns slot_number'),
    ('listed',         NULL,        0, 'Went live on a channel; opens a listings row'),
    ('price_changed',  NULL,        0, 'Reprice; see price_changes for the reason'),
    ('delisted',       NULL,        0, 'Pulled from a channel but still in its slot'),
    ('sold',           NULL,        0, 'Order received. Card is still physically in the binder.'),
    ('pulled',        'outbound',   1, 'Physically removed from the slot against an order'),
    ('shipped',       'in_transit', 0, 'Label printed, package handed off'),
    ('delivered',     'sold',       0, 'Carrier confirmed delivery'),
    ('returned',      'returned',   0, 'Buyer sent it back'),
    ('restocked',     'collection', 0, 'Returned card regraded and put back in inventory'),
    ('unslotted',     'collection', 1, 'Taken out of the binder without selling'),
    ('lost',          'lost',       0, 'Written off');


-- ─── Channels ────────────────────────────────────────────────────────────────
-- Fee rates and caps are ACCOUNT SPECIFIC and change. Read the real numbers off
-- the TCGplayer Seller Portal and eBay Seller Hub and update these rows; do not
-- trust the seeded defaults for anything that matters.
--
-- The caps below are TCGplayer Level 1 and a young eBay account. They are the
-- binding constraint on how much inventory can be deployed at all.

INSERT OR IGNORE INTO channels (
    channel, label, fee_rate, order_fee_cents, ship_cost_cents, materials_cents,
    minutes_to_list, minutes_to_ship,
    max_listing_count, max_listed_value_cents, max_item_price_cents, cap_period, note
) VALUES
    ('tcgplayer', 'TCGplayer', 0.1325, 30, 90, 20,
     0.5, 4.0,
     100, 100000, 50000, 'concurrent',
     'Level 1: 100 listings / $1,000 listed / $500 per item. 10.75% commission + 2.5% processing. Lists against a stock image, hence 30s.'),

    ('ebay', 'eBay', 0.1325, 35, 74, 20,
     5.0, 4.0,
     10, 50000, NULL, 'monthly',
     'New-seller limit ~10 items or $500/month — check Seller Hub for the real number. eBay Standard Envelope caps at $20 item price; above that use ~450c for a rigid mailer.');


-- ─── Binder ──────────────────────────────────────────────────────────────────
-- 12 pages of 9 pockets = 108 slots, comfortably over the 100-listing cap.
-- Front sides only, so there is never a question of which side of a page a
-- slot is on.

INSERT OR IGNORE INTO binders (binder_name, pockets_per_page, first_slot, last_slot, note) VALUES
    ('Binder 1', 9, 1, 108, '9-pocket side-loading pages, front sides only');


-- ─── Settings ────────────────────────────────────────────────────────────────

INSERT OR IGNORE INTO settings (key, value, note) VALUES
    ('labor_rate_cents_per_hour', '2500',
     'The hourly floor a listing must clear to be worth the handling. Drives the channel threshold — raise it and cheap cards stop qualifying for eBay.'),
    ('catalog_db_path', '../pokemon-tcg-search/data/pokemon.db',
     'Read-only. Relative to the project root.'),
    ('min_margin_cents', '50',
     'Never list where expected net proceeds fall below this, whatever the rules say.');

-- ─── Pricing rules ───────────────────────────────────────────────────────────
-- Tuned here rather than in code. Every one of these exists to stop an
-- automated repricer from doing something expensive and irreversible.

INSERT OR IGNORE INTO settings (key, value, note) VALUES
    ('price_deadband_pct', '3.0',
     'Ignore moves smaller than this. Without a deadband the repricer churns listings daily for noise, burning quota and resetting listing age for nothing.'),
    ('max_daily_move_pct', '20.0',
     'Hard clamp on any single reprice. A bad feed day cannot dump the inventory.'),
    ('auto_apply_max_pct', '10.0',
     'Moves bigger than this go to the review queue instead of applying. Raise it as trust in the rules builds.'),
    ('reserve_margin_cents', '100',
     'Required profit over cost basis. A listing is never repriced below cost plus fees plus this.');
