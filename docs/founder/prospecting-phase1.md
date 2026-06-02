# Prospecting Phase 1 Operator Note

Phase 1 builds a local-SMB prospect warehouse under `state/prospects/`. It is
separate from the discovery opportunity inbox: prospects are businesses with a
possible no-public-website signal, not validated product opportunities.

## Compliance

- Use the official Google Places API only.
- Do not scrape `google.com` or `maps.google.com`.
- Do not use Playwright, Selenium, browser automation, or Google Maps HTML.
- Do not store review text. Phase 1 stores only `rating` and
  `user_ratings_total`; `review_tier` is always `R0`.
- Do not run Google Search/SERP verification in Phase 1;
  `google_search_check` is always `skipped`.
- Do not send outreach from this pipeline.
- Bulk HTTP fan-out must use `--bulk --approved-by NAME`, which wires through
  `assert_bulk_crawl_allowed`.

## Inclusion Principle

The qualifying signal is that the business has no publicly available owned
website: missing, social-only, marketplace-only, or broken. Genres are not an
inclusion filter. `packages/prospecting/config/genres.yaml` is only a
non-exhaustive Places query catalog because Places search needs text queries.

## Commands

Dry-run the pipeline with fixtures and mocked HTTP:

```bash
python3 scripts/prospect_scan.py start --cells 2 --approved-by codex-phase1-test --dry-run
```

Run the bounded Seattle smoke test. The first two catalog cells are
`seattle:beauty_salon` and `seattle:auto_repair`.

```bash
python3 scripts/prospect_scan.py start --cells 2 --approved-by codex-phase1-smoke
```

Check status:

```bash
python3 scripts/prospect_scan.py status
```

Write the cohort report:

```bash
python3 scripts/prospect_report.py
```

The report is written to
`state/artifacts/prospecting/phase1-cohort-report.md`.

## Caps

Weekly caps live in `packages/prospecting/config/weekly_caps.yaml`:

- `text_search_requests`: 100
- `place_details_essentials`: 6000
- `http_checks`: 6000
- `place_details_pro_reviews`: 0
- `google_search_verifications`: 0

The shipped catalog is 20 cities x 20 genres, about 400 cells. At 100 cells per
week, run a four-week full-grid rotation. Use `--cells N` to process a bounded
chunk each invocation.

## Phase 2, Not Implemented Here

Phase 2 can add Google Search verification, review-tiering beyond `R0`, richer
HTTP diagnostics, SQLite storage, and outreach experiment handoff. None of that
is part of Phase 1.

