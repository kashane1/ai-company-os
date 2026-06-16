# Plan: DataForSEO as a prospect discovery source

**Date:** 2026-06-15
**Status:** ✅ Built and live-validated (Parts 1–3 done). Account verified; pilot run remains.
**Owner:** kashane1

> **Build note (2026-06-15):** the Business Listings endpoint has **no general
> free-text keyword search** — it filters by `categories` / `title` /
> `description` only, so discovery must use `categories`. The live smoke test
> proved DataForSEO's category taxonomy differs from Overture's (e.g.
> `barber_shop` not `barber`, `plumber` not `plumbing`, `roofing_contractor` not
> `roofing`), so the initial Overture-borrowed map returned **0 results**. Fixed
> by adding a dedicated `DATAFORSEO_GENRE_CATEGORIES` map built from the free
> `business_listings/categories` endpoint and validated live: `barber_shop` in
> Seattle returned 289 businesses (10 fetched, correctly classified into
> present / marketplace / absent). All 20 catalog genres are now mapped; a guard
> test fails if a genre is added without a slug. Live spend to validate: ~$0.05.

## TL;DR

DataForSEO is already wired as a *verification* provider (search a known
business by name → does it own a website). It is **not** wired as a *discovery*
source (search a category + city → get a list of new businesses). This plan adds
the missing discovery half by building a `DataForSEOBusinessConnector` against
the **Business Listings Search** endpoint, plugged into the existing
`collect-source` command and `SourceConnector` protocol so dedupe, cohorting,
verification, site builds, and outreach all work downstream unchanged. It also
covers a small live validation of the existing verifier. Discovery cost is
~$0.01/request + $0.0003/business (≈$0.31 per 1,000 leads).

---

## 1. Current state (what already exists)

| Piece | Status | Location |
|---|---|---|
| `DataForSEOSearchVerifier` (per-prospect SERP check) | ✅ Built, tested | `packages/prospecting/web_presence.py:252` |
| Env vars `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` | ✅ Defined, **not set** | `.env.example:56`, `packages/config/settings.py:26` |
| `verify-web --provider dataforseo` CLI | ✅ Built | `scripts/prospect_scan.py` |
| Verifier unit tests (mocked) | ✅ Built | `tests/python/unit/test_prospecting_web_presence.py` |
| **Discovery connector** (search → new businesses) | ❌ **Missing** | — |
| Live credential validation (verifier or discovery) | ❌ Never run | — |

The discovery side of the pipeline uses the `SourceConnector` protocol
(`packages/prospecting/source_import.py:24`) and currently has three
implementations: `GooglePlacesConnector`, `OverturePlacesConnector`,
`FSQOSPlacesConnector`. **DataForSEO is not one of them** — that is the gap.

## 2. Goal

Use DataForSEO's Business Listings data as a fourth discovery source that emits
new `ProspectRecord`s by category + location, and validate the existing verifier
against the live API with real credentials.

## 3. The endpoint we'll use

**`POST https://api.dataforseo.com/v3/business_data/business_listings/search/live`**

- **Live** (synchronous) — returns results in one call, no task-queue polling
  (simpler than the verifier's `task_post` → poll `task_get` flow).
- **Inputs that map cleanly to our config:**
  - `categories` (array, up to 10) — DataForSEO taxonomy (e.g. `pizza_restaurant`).
  - `location_coordinate` — `"lat,lng,radius_km"`. Maps to `CityConfig.lat/lng`
    and `radius_m` (convert metres → km).
  - `title` / `description` — free-text keyword fallback when we don't have a
    clean category mapping.
  - `filters`, `order_by`, `limit` (max 1000), `offset`.
- **Per-listing fields returned** (all map to `ProspectCandidate`):
  `title`, `address`, `address_info{city,zip,region}`, `phone`, `url`, `domain`,
  `cid`, `place_id`, `latitude`, `longitude`, `category`, `rating{value,votes_count}`,
  `is_claimed`.
- **Pricing:** $0.01 per request + $0.0003 per returned item
  (≈$0.31 / 1,000 businesses). PAYG, $50 minimum top-up.

Source: [Business Listings endpoint docs](https://docs.dataforseo.com/v3/business_data/business_listings/search/live/),
[Business Listings pricing](https://dataforseo.com/pricing/business-data/business-listings-api).

## 4. Design decision: category mapping (the one real unknown)

Our genres (`packages/prospecting/config.py` `GenreConfig`) carry a text
`query` and optional `included_types` (Google Places taxonomy). DataForSEO uses
its **own** category taxonomy. Two options:

- **A — keyword search (ship first):** pass `genre.query_for(city)` into the
  `title`/`description` field and rely on `location_coordinate` for geo. No
  taxonomy mapping needed; works for every genre immediately. Slightly noisier
  results.
- **B — category mapping (follow-up):** add an optional
  `dataforseo_categories: list[str]` field to `GenreConfig` / the genre catalog
  and pass it as `categories` for precision. Falls back to A when unmapped.

**Recommendation:** build A now (zero catalog changes, full genre coverage), add
B's optional field as a clean extension point. Flag in the plan, don't block on it.

## 5. Work breakdown

### Part 1 — Discovery connector (the net-new work)

1. **`packages/prospecting/connectors/dataforseo.py`** — new
   `DataForSEOBusinessConnector` implementing `SourceConnector`:
   - `source = "dataforseo"`, `connector_version = "dataforseo-business-v1"`.
   - `__init__(login, password, client, endpoint, location_radius_km, limit, ...)`
     — credentials via `get_api_key(DATAFORSEO_LOGIN_ENV_VAR/...)`, same
     `ProviderConfigError` guard as the verifier.
   - `query_for(city, genre)` — stable string for the dedupe/run-key
     (`source_runs` skip logic depends on this being deterministic).
   - `fetch_candidates(city, genre, *, limit)` — POST the live request, map each
     listing → `ProspectCandidate` (website from `url`/`domain`; phone; address;
     `source_confidence` from `is_claimed`/rating presence). Reuse a
     `RateLimiter` like the Places connector.
   - A small `_candidate_from_listing(payload, city, genre)` pure function so the
     mapping is unit-testable without HTTP.

2. **Wire into the CLI** — `scripts/prospect_scan.py`:
   - Add `"dataforseo"` to the `collect-source --source` choices.
   - Add a branch in `_build_source_connector()` (`:389`) constructing the connector.
   - Reuse existing `--candidates-per-cell`, `--force`, `--include-present-sites`.

3. **Cost guardrail** — add `--max-items` / a dry-run cost estimate print
   (`requests × $0.01 + items × $0.0003`) before spend, given the deliberate
   shift away from paid APIs noted in `docs/agency/manual-verification-sop.md`.

No changes needed to `run_source_collection`, dedupe (`IdentityIndex`), cohort
derivation, or anything downstream — the connector conforms to the existing
protocol, so collected records flow through verification → site build → outreach
exactly like Overture/FSQ records.

### Part 2 — Validate the existing verifier (live)

4. **Set credentials** — founder adds real `DATAFORSEO_LOGIN` /
   `DATAFORSEO_PASSWORD` to `.env` (one-time; account top-up ≥ $50 min).
5. **Small live smoke run** — `verify-web --provider dataforseo --limit 3` on a
   handful of known records; confirm verdicts + cost, per the go-live-cheaply
   posture (`feedback_go_live_caution`). Record the actual per-call cost.

### Part 3 — Tests & docs

6. **`tests/python/unit/test_prospecting_connectors_dataforseo.py`** — mocked
   `httpx.MockTransport`: a realistic Business Listings response → assert correct
   `ProspectCandidate` mapping (website class, phone, dedupe key) and request
   shape (categories/coordinate/limit). Mirrors the verifier test pattern.
7. **Docs** — update `docs/waas-prospecting-lane.md` (Stage 1 discovery sources)
   and `docs/agency/manual-verification-sop.md` to note DataForSEO is now a
   discovery option, with its cost. Run `make doc-index` after.

## 6. Out of scope

- No automated send — Stage 7 stays human-driven.
- No category-taxonomy catalog (Option B) in v1; left as an extension point.
- No live API call in CI (credentials never enter CI; all tests mocked).

## 7. Open questions for founder

1. **Build vs. defer Part 1?** Discovery reintroduces paid-API spend the team
   deliberately moved away from. Worth it for net-new lead volume beyond
   Places/Overture/FSQ? (Cost is low: ~$0.31/1k.)
2. **Category mapping:** OK to ship keyword-search (Option A) first?
3. **Geography/genres:** run against the full city×genre grid, or a small pilot
   tranche first to evaluate lead quality before scaling spend?

## 8. Effort estimate

- Part 1 (connector + CLI + guardrail): ~half a day.
- Part 2 (live validation): ~30 min once credentials exist.
- Part 3 (tests + docs): ~2 hours.
