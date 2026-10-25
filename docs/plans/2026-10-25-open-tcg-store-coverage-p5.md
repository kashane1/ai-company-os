---
status: open
change_id: open-tcg-store-coverage-p5
owner: founder
last_reviewed: 2026-10-25
---

# OpenTCG store monitoring P5: coverage beyond Shopify

**Parent plan:** [independent store monitoring](2026-10-23-open-tcg-indie-store-monitoring.md), phase P5.
**Status:** Built 2026-10-25.

## Probe (2026-10-25)

Each unpolled store got one polite read: robots.txt, the homepage, the platform's public product API, the sitemap, and one product page. Requests went one at a time per store, 4 seconds apart.

| Finding | Stores | Decision |
|---|---|---|
| Public WooCommerce Store API (`/wp-json/wc/store/v1/products`) | JD Collectibles (191 products), Rawmon (110) | **WooCommerce reader** |
| Product sitemap with `lastmod`, plus schema.org `Product` data (price, availability) on each product page | TCG Moonblast (Wix, 225 products), TCG Slayer (custom site) | **Sitemap reader** |
| Cloudflare challenge on every page | Beckett Castle, Forge and Fire, Game Nerdz, Out of the Box, TCG Jackpot | Not polled: no challenge bypass (parent plan boundary). Beckett Castle and Forge and Fire are covered by email. |
| HTTP 402 or 423 (closed or locked) | Decal Depo TF, PrCards, Prestige Collectibles, RareTCG | Parked as `closed` |
| Password-protected storefront (HTTP 401) | OneStopTCG | Parked |
| Shop loaded by JavaScript with no public token or sitemap | Level Up Games (Ecwid) | Not polled; covered by email and Discord #pre-orders |
| Pages without structured product data | PokéZone, Omni Collectibles, Hypno Comics (Square/Weebly, 7,600 products) | Not polled; each would need a site-specific scraper |
| Nothing reachable by script | Thirdspace (covered by email), CoreTCG, RNG-GAMEZ, TCG Card Depot (timed out) | Not polled, with the reason in `stores.toml` |
| Search pages only | Collector's Cache (CrystalCommerce) | Not polled |

## Design

`radar/stores/readers.py` adds two readers. They have the same interface as the Shopify reader: a robots check and a newest-first `fetch`. Each returns Shopify-shaped products with their own `url`, so matching, snapshots, MSRP classes, alerts and the digest work unchanged.

- **`WooCommerceReader`:**
  - Reads the Store API, 100 products per page, newest first.
  - The price comes from `prices.price` divided by `10^currency_minor_unit`.
  - A product counts as available when `is_in_stock` and purchasable.
  - Categories become tags, so a title without "Pokémon" still counts as Pokémon when the store files it under Pokémon.
- **`SitemapReader`:**
  - Reads `/sitemap.xml`; from a sitemap index, it reads only the product sitemaps.
  - Keeps URLs under the store's `product_path` (`/product-page` on Wix, `/product` on TCG Slayer).
  - Reads only pages whose slug names Pokémon or a catalog set.
  - A discovery read fetches the 8 most recently modified pages; the daily sweep fetches up to 150.
  - Each page's schema.org `Product` gives the title, lowest offer price and availability. `PreOrder` counts as available.
  - Variant ids are a stable 60-bit hash of the page URL.
- **Collection discovery stays Shopify-only.** Other platforms sweep their whole Pokémon catalog daily.
- **The registry** gains the platforms `sitemap_jsonld`, `square` and `closed`, and a `product_path` field. The polled platforms are `shopify_json`, `woocommerce`, `wix` and `sitemap_jsonld`.
- **`radar stores`** lists every unpolled store with its reason, whether its email list covers it, and its notes.

## As built (2026-10-25)

- **88 stores are polled**, up from 84: Moonblast, TCG Slayer, JD Collectibles and Rawmon were added.
- **The first live read** of the four new stores took 106 seconds, with no failures:

  | Store | Matched listings | In stock |
  |---|---|---|
  | Moonblast | 15 | 2 |
  | TCG Slayer | 15 | 15 |
  | Rawmon | 40 | 40 |
  | JD Collectibles | 4 | 3 |

- **Moonblast now has two paths:**
  - its drop emails (once the Gmail forwarding filter exists);
  - an hourly sitemap read, plus an immediate read whenever one of its drop emails arrives.
- **Not polled: 21 stores**, each with a reason in `stores.toml`:
  - 5 behind Cloudflare
  - 6 parked (closed, password-protected, singles-only, or scam)
  - 10 without a usable product feed
  - 5 of the 21 are covered by store email.

### Follow-up (2026-10-25)

- **PokéZone:** read through its own storefront API (`/api/storefront-products`), the catalog its single-page site loads, in one request. The first read matched 75 products.
- **Omni Collectibles:** headless Shopify, now read through `/products.json` on omnicollectibles.store.
- **Collector's Cache:** its robots.txt disallows every crawler except Google, so it is never read.
- **Shipping:** the registry gains `shipping` and `free_shipping_over`. Alerts, the report and the digest show shipping; price classes stay on the item price (founder decision 8c in the handoff).
  - From published policies: 12 flat rates and 35 free-shipping thresholds. 13 stores went unverified after Shopify rate-limited the research.
- **Larry's Game Store** isn't shipping and is parked. **Rawmon** is local pickup only (La Mirada, CA) and stays polled.
- **Polled now:** 89 stores.

