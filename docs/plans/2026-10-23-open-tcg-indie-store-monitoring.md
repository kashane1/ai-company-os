---
status: open
change_id: open-tcg-indie-store-monitoring
owner: founder
last_reviewed: 2026-10-23
---

# OpenTCG: independent store monitoring and MSRP pricing

**TL;DR**
- **Probe result:** 91 of the 109 stores in the founder's watchlist run on Shopify. 86 of them serve Shopify's public `/products.json`, so one request returns a store's newest 250 products with price, availability and creation time. No Pipet, browser or scraping layer is needed for most of the list.
- **The founder's worry is right.** Today's first pages held 104 in-stock English ETB listings across 25 stores. The median price was $129.97, and only 9 were within 10% of MSRP. Booster bundles had a median of $64.95, with 7 of 63 near MSRP.
- **OpenTCG owns this.** Stores become a new radar source that feeds the existing observations, episodes and Mac alerts. The tcgcsv catalog OpenTCG already syncs (940 sealed products, daily market price) gives product identity. A new MSRP reference table supplies the price classes.
- **OpenFlip consumes the result.** Price-classified offers go out through the existing OpenTCG export bridge. OpenFlip then judges them against sold comps.
- **Order:** 20-store pilot, then a store registry, Shopify collector, identity matching, MSRP classes, alerts and digest. After that come the remaining stores and OpenFlip export. Store scoring decides polling frequency.

**Status:** P0 pilot built 2026-10-23 (commit `0a9700c`). P1 built 2026-10-24: all 109 stores are registered, 85 are polled, and daily sweeps use validated sealed collections ([P1 plan](2026-10-24-open-tcg-store-registry-p1.md)). P2 built 2026-10-24: a silent reference catalog of every English set, stricter matching, and a review queue with remembered decisions ([P2 plan](2026-10-24-open-tcg-store-matching-p2.md)). P3 and P4 built 2026-10-24: MSRP references with evidence for 50 of 57 recent ETBs, bundles and displays, price classes, store alerts on MSRP hits, and the `radar deals` digest ([P3 plan](2026-10-24-open-tcg-store-msrp-p3.md), [P4 plan](2026-10-24-open-tcg-store-alerts-p4.md)). P5 built 2026-10-25: WooCommerce and sitemap/schema.org readers add four stores (88 polled), and every unpolled store records its reason ([P5 plan](2026-10-25-open-tcg-store-coverage-p5.md)). P6 radar side built 2026-10-25: each store observation records its MSRP, class and store trust for the OpenFlip export, and the export and bridge fields wait on the uncommitted OpenFlip work ([P6 plan](2026-10-25-open-tcg-openflip-export-p6.md)). P7 isn't built.

**P0 substitutions:** Thirdspace TCG isn't on Shopify JSON, and PokeMall TCG's `/products.json` is empty, so MH Deals Plus and Pokémon Plug replace them in the pilot. Hosts are spaced 4 s apart, not 5, and full sweeps stop at 40 pages. This plan builds the "local game stores on Shopify" lane. The [data-source plan](2026-09-25-open-tcg-data-sources-plan.md) called that lane the most underused, and its founder scope decision allows reads of public Shopify store JSON where `robots.txt` permits.

**Inputs:** the founder's `Pokemon_TCG_Store_Watchlist.xlsx` (109 stores, 14 marked first pass) and a ChatGPT conversation recommending Pipet. The per-store probe is saved as [`2026-10-23-indie-store-platform-probe.json`](../products/open-tcg/research/2026-10-23-indie-store-platform-probe.json).

## What the repository already has

| Capability | Where | Reuse for this plan |
|---|---|---|
| Source registry, per-source health, silent first-run baseline | `products/open-tcg/radar/sources.py`, `make sources` | Each store becomes a source with health and a baseline |
| Sealed product catalog with set, type, release date, exclusives and daily TCGplayer market price | `radar/catalog/` (tcgcsv), `products` and `price_points` tables | Product identity and market price for every match |
| Sealed vs single and product-type classifier | `radar/catalog/classify.py` | Turns listing titles into `etb`, `booster_bundle` and similar forms |
| Watch identity (language, form, packs, exact bindings, `ceiling_basis`) | `watchlist.toml` with `radar/watchlist.py` | Store bindings attach to the same identity |
| Observations, then episodes (one product, one retailer, 60 min), then one native alert | `radar/episodes.py`, `radar/notify.py` | Store hits become observations, so alerts need no new pipeline |
| Assisted open in Brave, only when the final URL is on the expected domain | `[[retailer_rule]]` (Costco) | Same domain check for each store, which also guards against lookalike domains |
| Read-only Gmail inbox reader, scored per sender | `radar/inbox/` | Newsletter and drop signups for stores we can't poll |
| Bounded fetcher with `robots.txt` and per-host spacing | `packages/openflip/source_adapters.py` | Pattern to copy into the radar's `http.py` |
| OpenTCG to OpenFlip export with typed `price_hint` | `packages/openflip/bridge.py` | Carries classified store offers to OpenFlip |
| Flip economics against sold comps | `packages/openflip/economics.py`, qualification | Decides whether an MSRP buy is worth flipping |

**Missing pieces:** a store registry, a store collector, matching listings to catalog products, and **MSRP**. The newer watches have `ceiling_basis = "Best Buy first-party retail reference, not MSRP"`. `alert_at` is a founder threshold. No MSRP value exists anywhere in the repo.

## Probe findings (2026-10-23)

Each store got one `GET /products.json?limit=250`. A store that refused got one homepage `GET`. Nothing was paginated, and no challenge was bypassed.

| Platform | Stores | How to read it |
|---|---|---|
| Shopify, JSON open | 86 | `/products.json` (newest first) and `/products/<handle>.js` |
| Shopify, JSON blocked | 5 | Decal Depo TF, OneStopTCG, PrCards, RNG-GAMEZ, Prestige Collectibles: HTML collection pages or inbox |
| Cloudflare challenge | 5 | Forge and Fire, Game Nerdz, Beckett Castle, Out of the Box, TCG Jackpot: **not bypassed**, inbox or manual only |
| WooCommerce | 2 | JD Collectibles, Rawmon: WooCommerce Store API (`/wp-json/wc/store/products`) if exposed |
| Wix | 1 | TCG Moonblast: drop-signup email to the project inbox |
| Ecwid, CrystalCommerce | 1 each | Level Up Games, Collector's Cache: small HTML adapter or inbox |
| Unknown or timeout | 8 | Thirdspace, CoreTCG, Hypno, RareTCG, TCG Slayer, Omni, PokéZone, TCG Card Depot: fingerprint during the pilot |

70 of the 86 open Shopify stores had more than 250 products. A full catalog therefore takes several pages. The newest page is still enough to catch new listings, because Shopify returns the newest products first.

**Pricing in those first pages.** These are English Pokémon titles with Japanese, graded, case and accessory listings filtered out by keyword. MSRPs are rough and per form.

| Form | In stock | Stores | Median price | Within 10% of MSRP |
|---|---|---|---|---|
| Elite Trainer Box | 104 | 25 | $129.97 | 9 |
| Booster bundle | 63 | 18 | $64.95 | 7 |
| Booster box / display | 76 | 19 | $234.97 | 18 |
| Single pack | 134 | 16 | $17.99 | 9 |

Two findings shape the design:

1. **Keyword matching isn't enough.** The near-MSRP ETB list included an "ETB Promo" single card at $6.99, and "Trick or Trade BOOster Bundle" was a $0.50 single. Identity has to go through the catalog classifier and pack-count checks.
2. **"Too good" is a risk.** One unvetted store listed out-of-print sets (Lost Origin ETB, Prismatic Evolutions booster bundle) at MSRP, far below market. Possible explanations are stale stock flags, a placeholder listing, or a scam. A below-market price on an unvetted store must alert with a clear warning, never as a plain deal.

## Pipet: decision

**Don't adopt it as a dependency.** Pipet is a good tool for hand-configured extraction, but this list doesn't need one:

- About 80% of the stores share one JSON format, so a single Python adapter of roughly 150 lines covers them. OpenTCG is Python with `httpx` already.
- Pipet would sit between scheduling, storage, matching and alerts, all of which OpenTCG already has. It would add a Go binary and a second config language without removing any of that code.
- Its HTML and Playwright modes don't help with the 5 Cloudflare stores, which the radar doesn't bypass as policy.

**Keep the idea.** Pipet's core technique is to find the store's own JSON request and call it directly. That is exactly the adapter order below: platform JSON first, HTML collection pages second, inbox third, browser never. Pipet stays useful for prototyping one odd store's selectors before porting them to Python.

## Design

### 1. Store registry: `products/open-tcg/stores.toml`

This is source configuration that Claude maintains, kept apart from `watchlist.toml`, which stays the founder's product intent. One entry per store:

```toml
[[store]]
store_id = "sunnys_card_shop"
name = "Sunny's Card Shop"
domain = "sunnyscardshop.myshopify.com"   # exact; final URLs must stay on it
platform = "shopify_json"                 # shopify_json | shopify_html | woocommerce | ecwid | inbox_only | manual
tier = "first_pass"                       # first_pass | explore | backup | parked
trust = "unvetted"                        # unvetted | checked | purchased_ok | avoid
ships_to_ca = "unknown"
newsletter = false
notes = ""
```

Import the 109 rows from the spreadsheet once, using the probe JSON for `platform`. After that, the TOML is the source of truth and the spreadsheet is retired. GG Legends (singles only) and stores reporting 0 sealed start as `parked`.

### 2. Collector: `radar/stores/`

- **Shopify adapter.**
  - *Discovery:* `GET /products.json?limit=250`, page 1, returns the newest listings.
  - *Full sweep:* page through until a short page, at most once a night per store.
  - *Hot check:* `GET /products/<handle>.js` for listings already matched to a watched product.
- **Politeness.** Read `robots.txt` once a day and honor it. Wait at least 5 s between requests to one host and send one request per host at a time. Use a descriptive User-Agent. On 429 or 5xx, back off and honor `Retry-After`.
- **Failures mean unknown.** A failed or blocked fetch never marks anything sold out. It lowers the store's source health, and `make sources` shows it.
- **Storage** (new tables in `radar.db`):
  - `store_listings`: store, handle, variant, title, first_seen, last_seen, and `catalog_product_id` (nullable).
  - `listing_snapshots`: one row per change of price, `available` or `compare_at_price`, not per poll.
- **First run is a silent baseline**, like every other radar source. Only later changes become observations.

### 3. Identity matching: listing to catalog product

1. **Normalize the title.** Strip store prefixes such as "Pokémon TCG:".
2. **Reject what can't be English sealed:** Japanese, Korean, Chinese, Thai and Indonesian titles, graded slabs, "promo", "code card", "empty", accessories, and listings where a single card number appears.
3. **Classify** with `classify.py` to get `product_type` and `set_key`.
4. **Match** to the tcgcsv `products` row by set key and form. Use pack count, variant ("Pokémon Center" ETB, exclusives) and release window to break ties.
5. **Score confidence:** `exact`, `probable` or `unmatched`. Only `exact` can alert. `probable` and `unmatched` go to a review queue (`radar listings review`). The founder or Claude confirms a match once per store handle, and the decision is remembered.

### 4. MSRP reference and price classes

**New `msrp_references` table**, keyed by catalog product. Every row records `msrp_cents`, `basis`, `evidence_url` and `checked_on`. When a product has several references, the strongest basis wins:

| Rank | Basis | Example |
|---|---|---|
| 1 | `official_listing` | Pokémon Center product page price |
| 2 | `big_box_first_party` | Target, Walmart or Best Buy sold by the retailer (the existing `ceiling_basis` references move here) |
| 3 | `distributor_or_press` | Distributor or press-release SRP |
| 4 | `form_default` | Era and form default (for example a standard ETB), marked **estimated** |
| 5 | `per_pack_estimate` | Pack count times the era's pack MSRP, for unusual collections, marked **estimated** |

Populate it from the catalog: about 25 ETBs, 15 bundles and the booster displays first, because those forms are where MSRP matters. A weekly Claude task adds upcoming tcgcsv presale products and checks prices at basis 1–2 (`radar msrp missing` lists the gaps). Estimated rows can rank a listing but can't fire an alert alone.

**Price class**, computed from total price including known shipping. Shopify JSON has no shipping, so the class uses item price until a store's shipping rule is recorded.

| Class | Rule | Default action |
|---|---|---|
| `below_msrp` | under 0.95 × MSRP | Alert. On an `unvetted` store the alert carries a warning: "unvetted store, below MSRP, check before paying". |
| `at_msrp` | 0.95–1.10 × MSRP | **Alert** (the founder's target) |
| `near_msrp` | 1.10–1.25 × MSRP | Digest only |
| `market` | above 1.25 × MSRP, at or below 1.05 × tcgcsv market | Digest only, OpenFlip ignores |
| `marked_up` | above market | Recorded, never surfaced |

`alert_at` in `watchlist.toml` still applies. A watched item alerts when its price is at or below `min(alert_at, 1.10 × MSRP)`. Unwatched English sealed products from a watched set alert at `at_msrp` or `below_msrp`. That gives the founder MSRP hits on products they didn't list. Products from unwatched sets never alert and appear only in the digest. Non-English products are excluded everywhere, as in the rest of OpenTCG.

### 5. Alerts and digest

- **Observations.** A store change becomes an observation with `source = "store:<store_id>"`. Possible signals are `new_listing`, `preorder`, `in_stock`, `price_drop` and `sold_out`. Episodes, the 15-minute freshness rule, `[exclude] terms` and the one-alert-per-episode rule are reused unchanged.
- **Alert text** names the store, its trust level, the price, MSRP and its basis, and the market price. Example: "Wulf Gaming · checked · Delta Reign ETB $54.99 (MSRP $49.99 official, market $78)".
- **Assisted open.** A Brave rule is added per store only after the store's first good purchase (`trust = purchased_ok`), and it uses the existing domain check.
- **`make deals`** prints a daily digest: the cheapest current English sealed offer per catalog product across all stores, its class, and the change since yesterday.

### 6. Stores we can't poll

Ten stores are blocked or challenged, and two (TCG Moonblast, Thirdspace) are already on Wix or unknown platforms with drop signups. Subscribe the project Gmail to their newsletters and drop lists. Claude handles the signups, as with the NowInStock and Keepa alerts. The existing inbox reader scores them per sender. Each store gets a sender entry tied to its `store_id`.

### 7. OpenFlip export

Classified offers whose class is `at_msrp` or `below_msrp` go out in the existing OpenTCG export. Each carries `price_hint`, `item_hint` (catalog product), `retailer_hint` (store) and a new optional `msrp_cents` and class. In OpenFlip they arrive as observations, and its existing qualification decides whether the spread to eBay sold comps beats fees. OpenFlip gets no new fetching, and OpenTCG gets no economics.

### 8. Store scoring and cadence

From `listing_snapshots`, compute per store: the share of matched sealed listings at MSRP, how long MSRP stock stays available, how often new sets appear, and fetch failure rate. Feed this into `make scorecard`, and let it set the tier:

| Tier | Discovery poll | Full sweep |
|---|---|---|
| Hot (frequent MSRP listings) | every 5 min | nightly |
| First pass | every 15 min | nightly |
| Explore | hourly | weekly |
| Parked | none | monthly check |

In drop windows (a release date from the calendar, or a set-level Bluesky signal), hot and first-pass stores briefly move to a 2-minute hot check of matched handles only. At steady state the whole list costs about 3,000 requests a day across 86 hosts, around 35 per store.

## Build order

| Phase | Work | Done when |
|---|---|---|
| **P0 pilot** (week 1) | Shopify adapter plus matcher on 20 stores: the 14 first pass and 6 others (TCG Hub and Hobbies, PokeMall, Thirdspace, CARDHAVEN, GoodStash, Smoke and Mirrors). Collection only, no alerts. | A one-week report on new listings per day, match rate, `at_msrp` hits, and how long they stayed available |
| P1 registry | `stores.toml`, spreadsheet import, `robots.txt` cache, `make sources` rows | All 109 stores present with platform and tier |
| P2 identity | Matcher, review queue, remembered decisions, fixtures from real titles | At least 90% of English sealed listings matched `exact` or confirmed on a fixture of 300 titles |
| P3 MSRP | `msrp_references`, basis ranking, price classes, `radar msrp missing`, weekly refresh task | Every ETB, bundle and display in the catalog from 2025 onward has a basis 1–3 MSRP |
| P4 alerts | Store observations into episodes, alert text, `make deals` | Founder receives a correct `at_msrp` alert on a test listing, and `marked_up` never alerts |
| P5 coverage | WooCommerce, Ecwid and HTML adapters; inbox subscriptions for blocked stores | Every store is polled or subscribed, or parked with a reason |
| P6 OpenFlip | Export fields, bridge validation tests | An `at_msrp` offer appears as an OpenFlip observation |
| P7 scoring | Per-store metrics and automatic tiering | Cadence follows the metrics, and the scorecard shows store rows |

The pilot comes first because it answers the open questions cheaply: whether MSRP stock appears often enough at these stores to matter, and whether it lasts minutes or seconds. If it lasts seconds, the 15-minute tier is too slow, and P7's hot tier moves into P4.

## Boundaries

- No purchases, carts or checkout automation. Assisted open in Brave is the ceiling, as today.
- No bot-challenge bypass, login-walled reads or rotating IPs. A store that blocks us goes to the inbox or `manual`.
- Store titles and prices are unverified evidence. Shipping to California, preorder terms and legitimacy are checked by a person before `trust` rises above `unvetted`. Start each store with an inexpensive first order.
- Exact registered domains only. Redirects off-domain are dropped, which is the lookalike-domain protection the research warned about.
- DexCompare (the 68-store directory) is a discovery seed and a cross-check, not a runtime dependency. Read its terms before polling it at all.

## Founder decisions (2026-10-23)

1. **Unwatched products:** English sealed products from a watched set alert at or below MSRP, even when they aren't in `watchlist.toml`. Products from other sets go to the digest only.
2. **Below MSRP on an unvetted store:** notify, with a warning that the store is unvetted and the buyer should check it before paying. Don't hold it silently.
3. **Language:** English only. Japanese and other non-English products stay excluded everywhere, including the digest.
