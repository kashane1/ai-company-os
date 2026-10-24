# OpenTCG radar

A local radar for sealed Pokémon TCG: when products are coming, where they
land, and when they restock. It is a personal lab that runs on the always-on
Mac. The plans are
[the data-source plan](../../docs/plans/2026-09-25-open-tcg-data-sources-plan.md)
and [build-out 1](../../docs/plans/2026-09-25-open-tcg-build-1.md).

```
make setup      # create .venv and install httpx, websockets, pytest
make test
make sync       # run every enabled poll source once
make calendar   # upcoming sealed releases with exclusives and presale prices
make events     # what changed in the last 7 days
make sources    # per-source health
make backfill   # recent posts from the Bluesky restock accounts
make stream     # follow Bluesky live (runs until Ctrl-C)
make feed       # restock observations from the last 72 h (TCG only)
make episodes   # restocks grouped across sources, with each source's lag
make scorecard  # per source: episodes, times first, median lag, accuracy
make stores     # independent stores: health, sweep mode, matches, prices vs market, stock duration
.venv/bin/python -m radar mark 12 real|false          # judge an episode (feeds accuracy)
.venv/bin/python -m radar log guppy "30th Celebration ETB at Target" --at "2026-09-26 04:51"
.venv/bin/python -m radar notify-test
```

**Episodes and alerts.** Reports of one watched product at one retailer
within 60 minutes form one episode, however many sources post it. Each
source's lag is measured from the first report. Each Bluesky account is
scored separately, and Guppy alerts logged with `radar log guppy` are scored
the same way. A native Mac notification fires once per episode when it is
for a watched item, is an availability signal (in stock, pre-order, drop,
queue, invites, open drawing), is under 15 minutes old, and has no known
price above the item's `alert_at`.

**Rules in `watchlist.toml`.**
- `[exclude] terms` never alert. Today these are "Pitch Black" and "Chaos Rising", newer sets that are still easy to find.
- **Set-level alerts:** at any retailer, a drop, queue, restock or open drawing that names a watched set (30th Celebration, Ascended Heroes, Prismatic Evolutions, Destined Rivals) alerts even when no specific item is named. The alert lists the watched items that retailer announced for the set in the last 72 h.
- `[[retailer_rule]]` adds assisted checkout per retailer. Today only Costco has one.
- **Assisted checkout:** with `open_in_browser`, the radar follows the post's short link. If the final URL is really on costco.com, it opens the page in Brave, where the founder is signed in, and the founder clicks Buy. Links landing anywhere else are never opened.

## Background service

Three per-user LaunchAgents run the radar without a Terminal window:

- `com.ai-company-os.open-tcg.stream` follows Bluesky live. KeepAlive restarts it, and it starts at login.
- `com.ai-company-os.open-tcg.inbox` reads the project Gmail read-only every 30 s (KeepAlive).
- `com.ai-company-os.open-tcg.sync` runs every 15 minutes and polls only the sources that are due: PokeBeach every 15 min, Southern Hobby daily, and tcgcsv once after its nightly rebuild.

A scheduled Claude task, "OpenTCG 6 AM retailer sign-in check", checks sign-in at Costco, Pokémon Center, Walmart, Target and Amazon in Brave. It writes `data/login-status.json` and notifies only when a store needs signing in.

```
scripts/launchd.sh install | uninstall | status
tail -f data/logs/stream.log        # live posts as they arrive
tail -f data/logs/sync.log
tail -f data/logs/inbox.log
```

The jobs only run while the Mac is awake and logged in.

## Inputs

- **`watchlist.toml`:** the founder's only input. Claude keeps the NowInStock
  and Keepa subscriptions in sync with it.
- **`data/`** (git-ignored): `radar.db`, `config.toml` (ntfy topic, inbox
  address), and `secrets/` (mode 0700).

## Sources so far

| Source | Tier | Cadence | Gives |
|---|---|---|---|
| tcgcsv (TCGplayer catalog mirror) | S | daily | Sealed SKUs, presale release dates, retailer exclusives, daily market price |
| Southern Hobby release list | L | daily | Distributor release and order-due dates |
| PokeBeach front-page RSS | L | 15 min | Reveals and product announcements |
| Bluesky (@pokemonrestocks, @nowinstockus) | S | live stream | Drawings, invites, queues, drops, in-stock and pre-order posts, matched to the watchlist |
| Project Gmail (NowInStock, Keepa, any Pokémon mail) | L | 30 s | Alert emails, read-only over IMAP, scored per sender |
| Guppy / sightings (manual log) | L | manual | Founder-logged benchmark entries (`radar log guppy …`) |
| pokemon.com news | S | — | Disabled: bot challenge for non-browser clients, not bypassed |
| Independent stores (`stores.toml`) | L | 15–60 min by tier, sweep daily | Pokémon listings, prices and stock at 85 Shopify stores; collection only |

The first successful run of each source is a silent baseline. After that,
new SKUs, date changes, new distributor listings and new news items become
calendar events.

## Independent stores

[The store-monitoring plan](../../docs/plans/2026-10-23-open-tcg-indie-store-monitoring.md)
tracks small online card shops. `stores.toml` holds all 109 stores from the
founder's list. The 85 with open Shopify `/products.json` (GG Legends is parked)
are polled. The others are listed with the reason they aren't: JSON blocked,
another platform, or a bot challenge. Phase status:
[P0 pilot](../../docs/plans/2026-10-23-open-tcg-indie-store-monitoring.md) and
[P1 registry](../../docs/plans/2026-10-24-open-tcg-store-registry-p1.md) and
[P2 matching](../../docs/plans/2026-10-24-open-tcg-store-matching-p2.md) are built.

- **Discovery:** the store's newest 250 products, every 15 min for first-pass
  stores and the 20 pilot stores, hourly for explore and backup stores.
- **Daily sweep:** the store's validated sealed Pokémon collections. Each week,
  candidates from `/collections.json` are sampled, and a collection is selected
  when at least half its first page is sealed product. A store without one
  sweeps its whole catalog, up to 40 pages, and at most 8 such sweeps run per
  sync so new stores' baselines spread out.
- **Politeness:** `robots.txt` is checked daily, each store gets one request at
  a time at least 4 s apart, and responses that redirect off the store's domain
  are dropped.

Only Pokémon listings that could be sealed product are kept (`store_listings`).
A row goes into `listing_snapshots` only when a listing appears or its price or
stock changes. A store's first full sweep is a silent baseline. A failed fetch
leaves listings unknown, never sold out.

Each kept listing is matched to a **reference catalog**: every English group's
sealed products and prices from tcgcsv, synced daily by the silent
`tcgcsv_reference` source into `ref_*` tables. That catalog is kept apart from
the radar's own `catalog_groups`/`products`, so it never changes the calendar,
Bluesky set detection or alerts. A listing is `exact` only when one product
fits. Titles that name no set ("Mega Greninja ex Premium Collection") or only
an era ("Mega Evolution Elite Trainer Box [Lucario]") must also leave no
unexplained words. Otherwise the listing is `ambiguous` or `unmatched`, with a
reason. Japanese, Chinese (slim packs) and other non-English products, graded
cards, singles, promos, code cards, repacks and accessories are excluded and
not stored. On a 300-title hand-labeled fixture, matching makes no wrong exact
match and finds 94% of the titles that have one right product.

The review queue lists plausible sealed listings the matcher couldn't pin
down, grouped by title. A decision is remembered per store variant and wins
over automatic matching from then on: `confirmed`, or rejected (`excluded`,
`reviewed`).

```
.venv/bin/python -m radar stores-review [--limit N] [--reason R] [--unknown-form]
.venv/bin/python -m radar stores-decide STORE VARIANT PRODUCT_ID|reject [--same-title] [--note TEXT] [--by founder|claude]
.venv/bin/python -m radar stores-rematch     # after a matcher or catalog change; decisions still apply
```

Stores create no observations, episodes or alerts yet. MSRP classes come in P3,
so `make stores` compares prices with the reference catalog's market price and
with each watched item's `alert_at`. "Matched" counts `exact` and `confirmed`. `make sources` ends with a one-line store health
summary.
