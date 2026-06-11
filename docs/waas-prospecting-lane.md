# WaaS Prospecting → Outreach Lane

This document defines the end-to-end process for the Website-as-a-Service (WaaS)
local-SMB lane: from raw discovery to a personalized, human-sent outreach
message. It is the single source of truth that ties together pieces that
previously lived in separate artifacts (strategy brief, outreach template
library, the web build lane, ad-hoc verification runs).

It complements:
- `state/artifacts/discovery/waas-local-smb-wedge-brief.md` — the **strategy** (why this wedge).
- `state/prospects/outreach/README.md` — the **template library** (how messages are written).
- `packages/web/` — the **web build lane** (how a site is built, validated, deployed).

## Purpose

Turn local SMBs that lack a credible owned website into customers for a simple
one-page site, by: (1) discovering them, (2) **verifying** the no-website signal
is real, (3) building a preview site as the conversion edge, (4) drafting
personalized outreach, and (5) letting the operator send by hand. Every
irreversible/external action is human-gated.

## Hard boundaries (binding)

- **No automated sending.** No skill, script, tool, or MCP sends email or DMs.
  All outreach output is a **draft** the operator personalizes and sends
  manually. First-person send claims ("I sent…", "message delivered") are
  forbidden (see `skills/canonical/creator-outreach-draft` lint + `docs/failure-modes/gtm-lane.md`).
- **No bulk-crawl without an approval gate.** Discovery runs against the Places
  pipeline under `weekly_caps.yaml`; no scraping of Yelp/Google outside it.
- **Honesty in the offer.** A preview site is "built for you / hosted privately,"
  never claimed as already-published. Never imply the business is failing.
- **Verify before contact.** A lead is never contacted on the raw Maps signal
  alone — it must pass the verification stage below.

## The stages

| # | Stage | Status | Owner | Artifact / location |
|--:|---|---|---|---|
| 0 | **Coverage + dedupe guard** | ✅ built | prospecting platform | `packages/prospecting/identity.py`, `packages/prospecting/source_runs.py`, `packages/prospecting/source_import.py` |
| 1 | **Discovery sweep** | ✅ built | Places pipeline (scheduled) | `state/prospects/records/*.json`, cohorts via `packages/prospecting/cohorts.py` |
| 2 | **Verification** | ✅ built | browser verify (primary) or paid API | `web_verify_*` fields; SOP: [agency/manual-verification-sop.md](agency/manual-verification-sop.md) |
| 3 | **Target selection** | ⚠️ manual | operator + analyst | this doc (selection rules below) |
| 4 | **Contact-channel resolution** | ✅ built | browser contacts pass | `contact_*` fields; `verify-web-export --contacts-only` → `verify-web-ingest --contacts-only` |
| 5 | **Preview site build** | ✅ built | `packages/agency/prospect_site.py` + `scripts/agency/build_prospect_site.py` | `state/prospects/sites/<place_id>/dist/`; Netlify draft URL → `{mockup_url}` |
| 6 | **Outreach draft** | ✅ built | template library | `state/prospects/outreach/` (channel × genre) |
| 7 | **Operator send** | manual (by design) | operator | — |
| 8 | **Tracking / follow-up** | ⚠️ partial | operator | `engagement_status` on record |

### Stage 0 — Coverage + dedupe guard
The current Google Places warehouse is canonical. New sources (Overture,
Foursquare OS Places, OSM extracts, Socrata/open-data catalogs) must never write
directly to `state/prospects/records/`. They first pass through:

- `IdentityIndex` (`packages/prospecting/identity.py`) — matches by normalized
  phone, URL, and name+address before creating anything new.
- `SourceRunStore` (`packages/prospecting/source_runs.py`) — records
  `source + city_id + genre_id + query + connector_version`, so the same source
  query is not re-run blindly.
- `collect-source` (`scripts/prospect_scan.py`) — imports source candidates only
  after identity matching, and keeps source provenance on the record.
- `prospect_scan.py next-qualification` — decides whether the next operator
  move should verify the current warehouse or collect new source data.

Safe next-step check:

```bash
python scripts/prospect_scan.py next-qualification --provider brave --limit 50
```

### Stage 0.5 — Open-source collection tranches
Open-source collection is deterministic and ledgered. The scale plan is:

| tranche | cells | intended source | purpose |
|---|---:|---|---|
| `tranche1` | 10 cities × 6 genres = 60 | FSQ OS or override | prove volume/quality on focused cities |
| `tranche2` | 40 cities × 6 genres = 240 | FSQ OS or override | scale the first source across the full grid |
| `tranche3` | 40 cities × 6 genres = 240 | Overture | second-source coverage and duplicate collision test |
| `tranche4` | 40 cities × 13 genres = 520 | Overture | expanded genres after the first six are covered |

Commands:

```bash
# FSQ OS requires a local portal export/catalog path.
python scripts/prospect_scan.py collect-source \
  --tranche tranche1 --source fsq_os --fsq-path "$FSQ_OS_PLACES_PATH"

# Overture uses public S3 via DuckDB.
python scripts/prospect_scan.py collect-source \
  --tranche tranche3 --source overture --candidates-per-cell 50

# Expanded Overture discovery across the remaining enabled genres.
python scripts/prospect_scan.py collect-source \
  --tranche tranche4 --source overture --candidates-per-cell 50
```

2026-06-10 Overture execution: all 240 tranche-3 source/city/genre cells are
completed in `state/prospects/source-runs/overture/`: 8,496 candidates seen,
8,155 new source records created, 335 duplicate collisions skipped, and 6
owned-site source rows skipped. The tranche-4 expansion also completed all 520
remaining enabled Overture cells: 7,503 candidates seen, 7,138 new source
records created, 358 duplicate collisions skipped, and 7 owned-site rows
skipped. FSQ OS importer is built but was not executed because
`FSQ_OS_PLACES_PATH` is not configured yet.

### Stage 1 — Discovery sweep
The Places pipeline populates the warehouse and assigns cohorts. The WaaS
inclusion signal is "no usable owned website link." `A_gold` = no website field
on the Maps profile. **This signal is a candidate flag only** — see Stage 2.

### Stage 2 — Verification (the step that was previously undocumented)
The Maps "no website field" signal is **unreliable** — a 2026-06-02 web-search
pass over 980 `A_gold` leads found only **1.1%** were genuinely websiteless;
**37%** had an owned site not linked on Google. So every candidate gets one live
web search (`name + city + state + genre`) and is classified:

| Verdict | Meaning | Outreach disposition |
|---|---|---|
| `owned_site` | has own domain / dedicated branded booking page | **Drop** — not a WaaS target |
| `social_only` | only Facebook/Instagram/Linktree | Different pitch: "you're social-only" |
| `marketplace_only` | only Yelp/Booksy/BBB-type directories, no owned site | **Primary target** — honest "no owned site" |
| `none_found` | no web presence at all | **Purest target** (but smallest, often phone-only) |
| `ambiguous` | name collision / unclear | Hand-review before use |

Verdicts are written back to each record as `web_verify_verdict`,
`web_verify_url`, `web_verify_confidence`, `web_verify_note`, `web_verified_at`,
`web_verify_method`.

**Primary method (no API cost): manual browser verification.** An agent drives the
operator's logged-in Chrome to check each prospect on Google Maps / Google / social,
sets the verdict, and captures the demand (review count) and best contact channel in
one sweep. Work is sharded across N parallel chats. This is the current method of
record — see the full procedure in
[agency/manual-verification-sop.md](agency/manual-verification-sop.md).

```bash
# export a shard of unverified prospects, browse them, ingest the results:
python scripts/prospect_scan.py verify-web-export --cohort S_source_candidate \
  --shard 0 --shard-count 4 --limit 15 --out state/prospects/manual/chat1-batch.json
python scripts/prospect_scan.py verify-web-ingest --in state/prospects/manual/chat1-batch.json

# contacts-only pass for already-verified targets missing a digital channel:
python scripts/prospect_scan.py verify-web-export --contacts-only \
  --ids <id-list> --shard 0 --shard-count 4 --out state/prospects/manual/contacts.json
python scripts/prospect_scan.py verify-web-ingest --contacts-only --in state/prospects/manual/contacts.json
```

**Legacy path (paid APIs, optional):** `scripts/prospect_scan.py verify-web
--provider brave|dataforseo` runs the same `classify_web_presence` logic through
Brave Search or DataForSEO (`BRAVE_SEARCH_API_KEY` or `DATAFORSEO_LOGIN`/`_PASSWORD`
in `.env`). Retained for automated/bulk runs, but the browser method is preferred to
avoid API spend. The 2026-06-02 method of record was a batched multi-agent WebSearch
workflow (one search per lead, schema-validated, two passes). Keep per-run reports
under `state/artifacts/prospecting/` for operator analysis.

### Stage 3 — Target selection
Rank within verified buckets, do **not** treat raw `A_gold` as the list:
1. `marketplace_only` (largest honest "no owned site" audience).
2. `none_found` (purest, but verify a reachable channel exists — many are phone-only).
3. `social_only` only with the social-specific pitch.
Cluster first on appointment/service genres (salon/barber/nails, auto/home
service) per the wedge brief — booking friction makes the offer land hardest.
Exclude chains, franchises, lead-gen/SEO operations, and `garage_door`
(deprioritized in the manifest).

### Stage 4 — Contact-channel resolution  ✅ **built** (browser contacts pass)
Templates need a reachable channel (`email` / `instagram_dm` / `facebook_dm`); the
warehouse always stores `phone`, and a dedicated contacts pass now resolves the
digital channels into `contact_email` / `contact_instagram` / `contact_facebook` /
`contact_booking_url`. Run it on already-verified targets (it never re-touches the
verdict) — see the "Contacts-only pass" section of
[agency/manual-verification-sop.md](agency/manual-verification-sop.md):

```bash
python scripts/prospect_scan.py verify-web-export --contacts-only --ids <id-list> \
  --shard 0 --shard-count 4 --out state/prospects/manual/contacts.json
python scripts/prospect_scan.py verify-web-ingest --contacts-only --in state/prospects/manual/contacts.json
```

- `none_found` leads have no web presence by definition → still **phone-only**
  (phone-first outreach, not the with-mockup email). Nothing to collect.
- `marketplace_only` / `social_only` leads often expose an email/IG/FB on their
  Yelp/social page — the pass captures the best one; phone remains the fallback.

> **Default path (customer-facing):** **`docs/demo-site-build-playbook.md`** —
> evidence-grounded bespoke HTML at
> `state/prospects/sites/<place_id>/dist-v2/index.html`, Craft Pass, localhost
> review, gated deploy. **Do not** show owners token-fill pages.

### Stage 5 — Preview site build  ✅ **built** (quality default + deploy glue)

**Build** (human/agent, playbook): gather → brief → `dist-v2/` → screenshot QA.

**Deploy** (platform): `packages/agency/prospect_site.py` +
`scripts/agency/build_prospect_site.py` publish **only** `dist-v2/` — if it is
missing, the CLI fails with *run playbook first* (no silent fallback to `dist/`).

```bash
# After dist-v2 exists — package metadata / draft-deploy:
python scripts/agency/build_prospect_site.py --place-id <PID>
NETLIFY_AUTH_TOKEN=… python scripts/agency/build_prospect_site.py \
    --place-id <PID> --deploy --account <netlify-team-slug>
```

Outputs per lead: `state/prospects/sites/<place_id>/{dist-v2/index.html,
preview.json, outreach-with-mockup.md}`. On deploy, the record gains
`mockup_url`, `mockup_site_id`, `mockup_deploy_id`, `mockup_built_at`.

Each mockup is a **draft deploy to one shared preview site**
(`PREVIEW_SITE_NAME`, default `bbw-previews`), so every prospect gets a private
permalink `<deploy_id>--bbw-previews.netlify.app` without a new Netlify site per
prospect. Promoting to **production** (`packages/agency/launch.py`) and **custom
domain / DNS** remain approval-gated. Tests:
`tests/python/unit/test_prospect_site.py`.

#### Legacy token-fill path (deprecated — bulk/internal only)

`render_landing_html` + `demo_theme` → `dist/` is **not** the customer-facing
default. Use only with `--legacy-build` for bulk regeneration or internal
experiments. Paid **client sites** use `packages/web/scaffold.py` (Astro under
`products/<slug>-site/`), not prospect token-fill.

```bash
# Deprecated — do not use for mockups you will show a business owner:
python scripts/agency/build_prospect_site.py --place-id <PID> --legacy-build
```

`demo_theme.py` remains for portfolio anonymization (`build_portfolio_demos.py`)
and tests, not for bespoke prospect mockups.

### Stage 6 — Outreach draft
Use `state/prospects/outreach/`: pick the channel from the manifest's
`channel_priority` for the genre; prefer `email/with-mockup.md` whenever a
preview URL exists (`prefer_mockup: true`); pull `{observed_gap}` / `{genre_noun}`
from `genre-snippets.md`; personalize ≥1 line by hand.

Hard copy rule: outreach must read human-written and must never use an em dash.
The maintained rule sheet is `docs/agency/outreach-copy-rules.md`.

### Stage 7 — Operator send
Operator copies the draft and sends manually. Nothing in the pipeline sends.

The **outreach action panel** (localhost only, `127.0.0.1:8765/dashboard/outreach`)
makes this one-tap-per-channel: each deployed prospect gets Email / SMS / Call /
FB DM / IG DM buttons that open the native composer *prefilled* (Gmail compose,
Messages, `tel:`, m.me, instagram.com). A button is greyed until its contact
field has a value; an inline edit adds the value and lights it up. The buttons
only *open* a draft — the human still clicks send. After sending, "✓ Log sent"
records a touch (Stage 8). See `packages/dashboard/outreach_panel.py`,
`packages/agency/outreach_actions.py`, `apps/api/outreach_endpoint.py`, and the
plan at `docs/plans/2026-06-10-outreach-action-dashboard.md`.

### Stage 8 — Tracking / follow-up
Use the outreach operations ledger:

```bash
python scripts/agency/outreach_lane.py refresh
python scripts/agency/outreach_lane.py list --status ready_to_send
python scripts/agency/outreach_lane.py log --place-id <PID> --channel email --outcome sent --next-follow-up 2026-06-12
```

The operator-facing status list lives at
`state/prospects/outreach-lane/client-status.md`; the machine ledger (status
rollup) lives at `state/prospects/outreach-lane/client-status.json`. The
**action panel logs touches and contact overrides to SQLite**
(`state/prospects/outreach-lane/outreach.sqlite3`, via the `control_plane_db`
backend pattern — Postgres when `AI_COMPANY_OS_DATABASE_URL` is set). The legacy
`touches.jsonl` is imported once via `OutreachStore.import_legacy_jsonl`. The
`worker-outreach` lane may refresh/draft/reconcile this state, but outbound send
tasks fail closed.

## Current gaps (build backlog, priority order)

1. ~~Contact-channel resolution (Stage 4)~~ — ✅ **built** (browser contacts-only
   pass writes `contact_*`). Remaining: an automated/API fallback for bulk
   enrichment so it isn't browse-only.
2. ~~Prospect → preview-site glue (Stage 5)~~ — ✅ **built** (playbook `dist-v2` +
   deploy glue). Remaining: automate more playbook steps; **photos** in gather.
3. **Fold verification into sweep completion** — `verify-web` is now a
   first-class CLI, but the Places sweep still emits raw candidate cohorts before
   verification. Next step: make "outreach-ready" exports require
   `web_verify_verdict` and keep branded booking pages (Fresha/Booksy/Square/
   Toast) in the detector.
4. **Fixture hygiene** — synthetic `Fixture Local N` records leak into
   `state/prospects/records/`; purge and guard against re-entry.
5. ~~Outreach tracking~~ — ✅ built as `packages/agency/outreach_lane.py`,
   `scripts/agency/outreach_lane.py`, and `apps/worker-outreach/`. Remaining:
   optional CRM adapter for email/reply sync.

## Client delivery (after they say yes)

Phases 3–5 (promote → intake → launch) are documented in
**`docs/agency/client-lifecycle.md`**. Operator CLIs: `scripts/promote_prospect.py`,
`scripts/agency/client_intake.py`, `scripts/agency/launch_client.py`.

## Where things live (quick reference)

- Strategy: `state/artifacts/discovery/waas-local-smb-wedge-brief.md`
- Client lifecycle: `docs/agency/client-lifecycle.md`
- Warehouse: `state/prospects/records/*.json` · cohorts `packages/prospecting/cohorts.py`
- Verification reports: `state/artifacts/prospecting/*-verification.md`
- Outreach templates: `state/prospects/outreach/` (README, manifest, genre-snippets, channel dirs)
- Outreach status: `state/prospects/outreach-lane/client-status.md`
- Web build lane: `packages/web/` · worker `apps/worker-web`
- Caps/cost: `packages/prospecting/config/weekly_caps.yaml`
