-- Projections over the ledger and the listing tables.
--
-- Views live apart from schema.sql because they are derived: nothing is stored
-- here, so `initialize` drops and recreates all of them on every run. That is
-- what lets a view change reach an existing database without a migration,
-- which the tables themselves cannot do.


-- The current state of every copy, derived from the last state-changing event.
DROP VIEW IF EXISTS copy_current_state;
CREATE VIEW copy_current_state AS
SELECT
    c.copy_id,
    c.variant_id,
    c.product_id,
    c.condition_code,
    c.cost_cents,
    e.kind            AS last_event_kind,
    e.occurred_at     AS last_event_at,
    k.resulting_state AS state,
    s.container
FROM copies c
LEFT JOIN events e
       ON e.event_id = (
            SELECT e2.event_id
              FROM events e2
              JOIN event_kinds k2 ON k2.kind = e2.kind
             WHERE e2.copy_id = c.copy_id
               AND k2.resulting_state IS NOT NULL
             ORDER BY e2.occurred_at DESC, e2.event_id DESC
             LIMIT 1
       )
LEFT JOIN event_kinds k ON k.kind = e.kind
LEFT JOIN copy_states s ON s.state = k.resulting_state;

-- Which slot currently holds which copy. A slot is occupied by the copy whose
-- most recent slot-bearing event put it there, unless that event freed it.
DROP VIEW IF EXISTS slot_occupancy;
CREATE VIEW slot_occupancy AS
SELECT
    e.slot_number,
    e.copy_id
FROM events e
JOIN event_kinds k ON k.kind = e.kind
WHERE e.slot_number IS NOT NULL
  AND k.frees_slot = 0
  AND e.event_id = (
        SELECT e2.event_id
          FROM events e2
         WHERE e2.slot_number = e.slot_number
         ORDER BY e2.occurred_at DESC, e2.event_id DESC
         LIMIT 1
  );

-- Live listings with current capacity consumption per channel.
DROP VIEW IF EXISTS channel_usage;
CREATE VIEW channel_usage AS
SELECT
    ch.channel,
    ch.max_listing_count,
    ch.max_listed_value_cents,
    ch.free_listings_per_period,
    ch.insertion_fee_cents,
    ch.cap_period,
    COUNT(l.listing_id)                      AS live_listing_count,
    COALESCE(SUM(l.list_price_cents), 0)     AS live_listed_value_cents
FROM channels ch
LEFT JOIN listings l
       ON l.channel = ch.channel
      AND l.ended_at IS NULL
GROUP BY ch.channel;
