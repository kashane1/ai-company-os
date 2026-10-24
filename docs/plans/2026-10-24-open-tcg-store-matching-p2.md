---
status: open
change_id: open-tcg-store-matching-p2
owner: founder
last_reviewed: 2026-10-24
---

# OpenTCG store monitoring P2: listing identity matching

**Parent plan:** [independent store monitoring](2026-10-23-open-tcg-indie-store-monitoring.md), phase P2.
**Builds on:** P0 (`0a9700c`) and P1 (`d88f2e1`): 85 Shopify stores polled, about 30,000 kept Pokémon listings.
**Status:** Built 2026-10-24.

## Where matching stands (2026-10-24, all 85 stores)

| Status | Reason | Listings | In stock |
|---|---|---|---|
| exact | | 2,028 | 954 |
| unmatched | unknown_form | 18,376 | 4,036 |
| unmatched | set_not_in_catalog | 8,740 | 1,807 |
| ambiguous | variant_unclear | 370 | 132 |
| ambiguous | era_name_only | 254 | 81 |
| ambiguous | quantity_unclear | 100 | 41 |
| unmatched | form_not_in_set | 428 | 18 |

Reading samples of each bucket shows five causes:

1. **The catalog is too narrow.** The radar syncs only sets from the last 120 days plus watched sets, which is 10 groups. Phantasmal Flames, Surging Sparks, Journey Together, 151, Black Bolt, Crown Zenith, Evolving Skies and every older set are missing, so their listings are `set_not_in_catalog`.
2. **Set-less product names.** "Mega Greninja ex Premium Collection" or "Charizard ex Special Collection" name no set. The catalog has the product, but matching only searches inside a named set.
3. **Cases sold through a variant.** "Elite Trainer Box" with the variant "Factory Sealed Case of 10…", or "[x10] Sealed Case", are flagged `quantity_unclear` even though the catalog has the case product.
4. **Base-set titles.** "Mega Evolution Elite Trainer Box [Lucario]" names only the era, so it is never exact, even though Mega Evolution (ME01) is the base set's own name.
5. **Classifier gaps.**
   - Plural forms ("Tins") aren't recognized.
   - Contents wording ("…Collection with 6 booster packs") is read as a booster pack.
   - Singles written as "Holofoil", "101/null" or with a condition variant ("Lightly Played") aren't excluded.
   - "(J)" isn't recognized as Japanese.

## Scope

1. **A reference catalog owned by store matching.**
   - Sync every English Pokémon group's sealed products from tcgcsv into new `ref_groups`, `ref_products` and `ref_price_points` tables, through a new `tcgcsv_reference` source.
   - Products are refetched only when a group's `modifiedOn` changes. Prices are refreshed daily for groups from the last three years and weekly for older ones.
   - It never emits calendar events, and it never touches `catalog_groups` or `products`, which feed the radar's Bluesky set detection, alerts and calendar.
   - Store matching and the store report read only the reference catalog. Groups with no sealed products contribute no set keys.
2. **Matcher upgrades**, all keeping the rule that only one unambiguous product is `exact`:
   - **Set aliases:** "Scarlet & Violet 151" also matches "151".
   - **Set-less named products:** when no set is named, match across all sets by distinctive name tokens (at least two besides the form words), and only when exactly one product fits.
   - **Era-only titles:** match the base set only when no unexplained words remain after removing the era, form, product and generic words. "Mega Evolution Phantasmal Flames Booster Box" stays ambiguous.
   - **Cases and displays** chosen through quantity wording are no longer flagged `quantity_unclear`. Loose multiples ("Booster Pack x 50") still are.
   - **Form detection ignores contents wording** ("with 6 booster packs", "36 packs") and recognizes plurals.
   - **More single-card and Japanese markers.**
   - **Products the catalog types as `other`** (Collector Chest, First Partner Pack, Fun Pack) match by name tokens.
3. **Remembered decisions.**
   - A `listing_decisions` table keyed by store and variant holds a confirmed catalog product or a rejection, with who decided and a note.
   - A decision overrides automatic matching on every later fetch and rematch, giving status `confirmed` or `excluded` with reason `reviewed`.
   - Confirmed listings count as matched everywhere exact ones do.
4. **Review queue.**
   - `radar stores-review` lists ambiguous and unmatched English listings that are plausibly sealed. That leaves out `unknown_form` unless asked, because those are mostly video games, singles and merch.
   - Identical titles are grouped across stores, with in-stock listings and watched sets first, and candidate products are shown for ambiguous ones.
   - `radar stores-decide STORE VARIANT PRODUCT_ID|reject [--same-title] [--note]` records a decision. With `--same-title`, it applies to every listing whose title and variant read the same.
5. **Accuracy fixture.**
   - 300 real titles sampled across stores and buckets, each labeled by hand with the right product or "no single product", plus the reference products those titles need.
   - The test requires no wrong exact matches, and at least 90% of the titles that have one right product to match it exactly.

**Out of scope:** MSRP (P3), alerts (P4), non-Shopify adapters (P5), OpenFlip export (P6).

## Done when

- The reference catalog holds every English group's sealed products and prices, and the radar's own tables are unchanged.
- The 300-title fixture passes: 0 wrong exact matches and at least 90% recall.
- On live data, `set_not_in_catalog` falls sharply and `exact` plus `confirmed` rises, without any wrong exact match in a hand-checked sample of 100.
- The review queue and decisions work end to end, and a decision survives a rematch.

## As built (2026-10-24)

**Live results** (all 85 stores, after rematch):

| | Before P2 | After P2 |
|---|---|---|
| exact | 2,028 | 7,386 (2,351 in stock) |
| unmatched: set_not_in_catalog | 8,740 | 1,738 |
| unmatched: unknown_form | 18,376 | 1,661 |
| kept listings | 30,296 | 14,156 |

About 16,500 kept listings turned out to be single cards. Markers they used ("Holofoil", "101/null", "Lightly Played" variants) are now recognized, so they are no longer stored.

**Accuracy.** The 300-title fixture (`tests/fixtures/store_titles_p2.json`) has 168 titles with one right product. Matching finds 158 of them (94.0%) and makes no wrong exact match. The 10 misses are misspellings ("Mabostiff", "Ninetails", "Illustraion"), titles naming two products, or names missing a qualifier word ("Premium", "Unova").

The fixture was labeled while the matcher was being tuned, so precision was also checked on fresh live samples of exact matches outside it:

- **First 100:** three wrong. A Euro half booster box matched as a full box, and "3 Pack" and "36 Booster Pack Bundle" matched a single pack. The fixes cover hyphenated "half-booster", singular pack counts and "(Sleeved)" packs.
- **Second 100:** one wrong, plus one undated-tin case. The fixes: a case title keeps its form unless the variant names one unit, and a year in a no-set or era-only title must appear in the product name.
- **Third 100:** all correct.

**Other details:**

- `store_listings.catalog_product_id` referenced the radar's `products` table, so the first scheduled run on the new matcher failed on a foreign key. `review.ensure_schema` now rebuilds the table once to reference `ref_products`, keeping rows and snapshots. It runs before every collection and rematch.
- Review decisions live in `listing_decisions`. Rejected listings stay stored, so a decision sticks. Automatic exclusions are still dropped, both on fetch and on rematch.
- The reference sync takes about 1m40s for the first full load (220 groups, 3,548 sealed products, 181 groups priced). After that it refetches products only when tcgcsv's `modifiedOn` changes, and it reprices groups older than three years weekly.
