# Prospecting Phase 2 Operator Note

Phase 2 turns the Seattle Phase 1 warehouse into a prioritized cohort-A shortlist
for manual operator verification. It does not add the deferred Google Search
verification layer, review collection, national scale-out, or outreach sending.

## Priority Formula

`packages/prospecting/cohorts.py` computes:

```text
priority_score = cohort_weight * demand_factor
demand_factor = min(user_ratings_total / 100, 1.0)
```

Weights are deterministic:

- `A_gold`: 100
- `B_stale_maps`: 80
- `Z_needs_review`: 40
- `D_low_signal`: 15
- `E_has_site`: 5

The score is rounded to two decimals. Re-running `backfill-priority` or
`export-cohort-a` recomputes the score idempotently for every stored record.

## Z Reduction

The Phase 1 Z backlog was mostly `maps_website_class=present` rows with
`http_check_class=skipped` because present-site rows were only sampled for HTTP.
Phase 2 treats those deterministic-sample skips as `E_has_site` instead of
ambiguous Z. Actual timeout/error cases remain reviewable, and HTTP checks now
retry transient timeout/request errors once while preserving the configured
timeout, redirect, and per-host RPM settings.

## Seattle Sweep Result

The bounded Phase 2 Seattle run covered every existing Seattle genre cell in the
catalog. It completed 20 cells, saw 392 Places results, created 353 records, and
updated 39 records. The resulting warehouse had 399 records and 30 `A_gold`
rows, below the target of 50. Four `A_gold` rows are dry-run fixture records
left in the local runtime state, so the operator export contains 26 real
shortlist rows. Treat this as an honest shortfall from the current Places query
catalog rather than a reason to add new APIs or expand beyond Seattle.

## Manual Spot-Check Workflow

Export the operator shortlist:

```bash
python3 scripts/prospect_scan.py export-cohort-a
```

This writes `state/prospects/exports/seattle-cohortA-{date}.csv`, sorted by
`priority_score` descending. The export includes blank `human_verified` and
`human_verify_note` columns. Codex and the pipeline must leave these blank.

For each row, manually open the `maps_url`, inspect the Google Business Profile,
and fill:

- `human_verified`: `true` only when the no-owned-website signal is still valid;
  `false` when the spot-check finds a public owned website or another blocker;
  leave blank when not checked.
- `human_verify_note`: short operator note such as `GBP spot-check passed` or
  `found owned website`.

Import the operator-filled file:

```bash
python3 scripts/prospect_scan.py import-verifications state/prospects/exports/seattle-cohortA-{date}.csv
```

The import updates only matching stored records and sets `human_verified`,
`human_verified_at`, and `human_verify_note` from operator-filled rows. Blank
`human_verified` rows are skipped.

## Deferred Phase 3

Keep these deferred:

- Google Search / SERP verification
- Review text or review-tiering beyond `R0`
- National or multi-city expansion
- Email sending, mail integrations, recipient list population

For Phase 2, `google_search_check` remains `skipped` and `review_tier` remains
`R0` on every row.

## Phase 2.1 fixes (2026-06-02, after manual verification of the first export)

Manual spot-checking the first 26-row Seattle export (via Places API + web
search) surfaced four corrections, now in code:

1. **Marketplace is its own bucket, not a drop and not A_gold.** A business whose
   only web presence is a third-party booking page (Vagaro, Square, Fresha, Yelp)
   has no owned site and is often an excellent pitch target — but page quality
   varies, so it routes to the new `A2_marketplace_review` cohort
   (`priority_score` weight 85) for manual review before outreach. See
   `packages/prospecting/cohorts.py`.
2. **Website builders are real sites.** `squarespace.com` (and wix/weebly/webs/
   godaddysites) were being mislabeled marketplace. They are owned websites and
   now classify as `present` → `E_has_site`. Only true booking/marketplace hosts
   remain in `MARKETPLACE_HOSTS` (`connectors/google_places.py`).
3. **`maps_url` now resolves.** The export built `...?api=1&query_place_id=X`
   with no `query` param, which Google rejects. `maps_url()` now includes the
   business name as `query` so every link opens. (Future option: store the
   Places `googleMapsUri` for an even more canonical link.)
4. **Junk genres can be disabled.** `GenreConfig` gained an `enabled` flag;
   `build_grid` skips disabled genres. `garage_door` is disabled (verification
   showed it's dominated by lead-gen/service-area operations, not local SMBs);
   `plumber` is review-only — confirm each is a real local shop.

Known limitation: backfilling re-derives cohorts from each record's stored
`maps_website_class`, but does not re-run host classification. Records ingested
before fix #2 keep their old class until re-ingested, so a Squarespace site
stored as `marketplace` will sit in `A2_marketplace_review` (manual review will
catch it) rather than `E_has_site`. New sweeps classify correctly.

The bigger finding — ~23% of the "absent" cohort actually had a real website that
Maps simply didn't list — is what justifies building the Phase 3 Google Search
verification layer next.
