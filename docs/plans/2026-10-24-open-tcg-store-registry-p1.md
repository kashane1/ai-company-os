---
status: open
change_id: open-tcg-store-registry-p1
owner: founder
last_reviewed: 2026-10-24
---

# OpenTCG store monitoring P1: full registry and sealed-collection sweeps

**Parent plan:** [independent store monitoring](2026-10-23-open-tcg-indie-store-monitoring.md), phase P1.
**Builds on:** the P0 pilot (commit `0a9700c`), which reads 20 Shopify stores and has run cleanly since 2026-10-24 05:12 UTC. The pilot keeps collecting through P1, so its one-week measurements continue.

## Why P1 now, and what changes from the parent plan

P0 surfaced one problem the parent plan didn't anticipate. **12 of the 20 pilot stores hit the 40-page full-sweep cap.** Their catalogs are mostly singles: Smoke and Mirrors alone returned 36,675 Pokémon variants in 40 pages. A daily sweep of one such store costs 40 requests and still misses older sealed listings. Scaling to 86 stores the same way would mean about 3,400 requests a day for full sweeps alone, with poor coverage.

**P1 therefore adds sealed-collection sweeps alongside the registry work.** Shopify's public `/collections.json` lists a store's collections, and `/collections/<handle>/products.json` reads one of them. On-Board Gaming has `pokemon-sealed` (65 products), and Shippin Texas has `pokemon-cards` titled "Pokemon Sealed" (92). Collection names can't be trusted, though. Shippin Texas has sealed collections behind handles like `sealed-151-pokemon-copy` titled "Sealed Paradox Rift Pokemon". So **every candidate collection is validated by reading its first page and measuring what share is sealed Pokémon.**

## Scope

1. **Full registry: all 109 stores in `stores.toml`.**
   - Generate the file once from the founder's spreadsheet and the 2026-10-23 platform probe. The TOML becomes the source of truth, and the 20 pilot entries keep their values.
   - **Platform values:** `shopify_json` (86, polled), `shopify_html` (5, JSON blocked), `woocommerce` (2), `wix` (1), `ecwid` (1), `crystalcommerce` (1), `challenge` (5, Cloudflare) and `unknown` (8). In P1 only `shopify_json` is polled. The rest are recorded with their reason, and P5 handles them.
   - **Tiers:** first_pass (the 14), explore, backup (the sheet's "Backup retailer") and parked. GG Legends is parked because it ships singles only.
   - **Spreadsheet facts carried over:** `newsletter` (sheet says "Signup observed") and `notes`.
2. **Cadence by tier.** Newest-page discovery runs every 15 min for first_pass and hourly for explore and backup. Parked stores aren't polled. A per-store `discovery_every_minutes` keeps the six non-first-pass pilot stores at 15 min until the pilot ends.
3. **Sealed-collection discovery, weekly per store.**
   - Page through `/collections.json` (at most 8 pages).
   - Keep candidates whose title or handle names Pokémon and doesn't say singles, graded, Japanese or accessories.
   - Read page 1 of each candidate (at most 6 per store) and select it when at least half its Pokémon products could be sealed (not excluded by the matcher) and it holds at least one.
   - Results go in a new `store_collections` table.
4. **Daily sweep uses selected collections.** It pages each selected collection to the end (cap 40 pages each). A store with no selected collection falls back to the whole catalog, capped at 40 pages as before.
   - The 15-minute newest-page read stays catalog-wide, so a new listing is caught even if the store never files it in a sealed collection.
5. **Staggered first sweeps.** At most 8 whole-catalog sweeps per sync run, so adding 66 stores spreads their baselines over several runs. Without this, one run would block the sync job for about 20 minutes.
6. **Health.**
   - `radar sources` adds a stores summary line: ok, failing, not polled by platform.
   - `make stores` lists unpolled stores with their reason and each store's sweep mode (collections or catalog) and truncation.

**Out of scope for P1:** MSRP (P3), alerts (P4), non-Shopify adapters and inbox subscriptions (P5), OpenFlip export (P6), metric-driven tiering (P7).

## As built (2026-10-24)

- **Validation counts recognized TCG forms only.** The first live check
  selected collections of model kits, nanoblocks, Topps stickers and toys,
  because those listings aren't excluded by the matcher. A sampled listing now
  counts as sealed only when the matcher recognizes a TCG sealed form, and
  collection titles naming models, toys, blind boxes, apparel or Topps aren't
  candidates.
- **The catalog-sweep budget is spent in the fetch step.** At first, every
  store without a selected collection counted against the 8-per-run budget at
  planning time. That deferred 57 new stores whose collection check was about
  to run in the same pass. Now a store draws on the shared budget only after
  its check finds no usable collection.

## Data

There is no migration mechanism in the radar schema, so P1 adds tables instead of altering `stores`:

```sql
store_collections (store_id, handle, title, sampled_count, sealed_count,
                   is_selected, checked_at, PRIMARY KEY (store_id, handle))
store_collection_checks (store_id PRIMARY KEY, checked_at, candidate_count, selected_count, error)
```

## Request budget at steady state

| Read | Stores | Requests per day |
|---|---|---|
| Newest page, every 15 min | 20 (14 first pass, 6 pilot) | 1,920 |
| Newest page, hourly | about 66 | 1,584 |
| Daily sweep through collections (1–3 pages typical) | about 50 | about 100 |
| Daily whole-catalog sweep (no valid collection) | about 36 | up to 1,440 |
| Weekly collection discovery (up to 14) and robots.txt daily | 86 | about 260 |

That totals about 5,300 a day across 86 hosts, around 60 per store. Every store still gets at most one request at a time, 4 s apart.

## Done when

- `stores.toml` holds all 109 stores, and the 86 `shopify_json` stores are polled.
- Every polled store has a baseline, and none is failing for a reason other than its own outage.
- Stores with a valid sealed collection no longer hit the sweep cap. The report shows sweep mode per store.
- The pilot's 20 stores keep 15-minute discovery, and their history continues unbroken.
- Tests cover the collection candidate filter, validation, sweep selection, the full-sweep stagger, tier cadence and registry parsing of the new fields.
