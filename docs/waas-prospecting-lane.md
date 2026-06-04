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
| 1 | **Discovery sweep** | ✅ built | Places pipeline (scheduled) | `state/prospects/records/*.json`, cohorts via `packages/prospecting/cohorts.py` |
| 2 | **Verification** | ✅ built (this doc formalizes it) | web-search workflow | `web_verify_*` fields on each record; run report e.g. `state/artifacts/prospecting/agold-website-verification.md` |
| 3 | **Target selection** | ⚠️ manual | operator + analyst | this doc (selection rules below) |
| 4 | **Contact-channel resolution** | ❌ gap | — | not built; see Gaps |
| 5 | **Preview site build** | ✅ built | `packages/agency/prospect_site.py` + `scripts/agency/build_prospect_site.py` | `state/prospects/sites/<place_id>/dist/`; Netlify draft URL → `{mockup_url}` |
| 6 | **Outreach draft** | ✅ built | template library | `state/prospects/outreach/` (channel × genre) |
| 7 | **Operator send** | manual (by design) | operator | — |
| 8 | **Tracking / follow-up** | ⚠️ partial | operator | `engagement_status` on record |

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
`web_verify_method`. **Method of record:** batched multi-agent workflow, one
WebSearch per lead, schema-validated output, two passes to cover failures. Keep
the per-run report under `state/artifacts/prospecting/`.

### Stage 3 — Target selection
Rank within verified buckets, do **not** treat raw `A_gold` as the list:
1. `marketplace_only` (largest honest "no owned site" audience).
2. `none_found` (purest, but verify a reachable channel exists — many are phone-only).
3. `social_only` only with the social-specific pitch.
Cluster first on appointment/service genres (salon/barber/nails, auto/home
service) per the wedge brief — booking friction makes the offer land hardest.
Exclude chains, franchises, lead-gen/SEO operations, and `garage_door`
(deprioritized in the manifest).

### Stage 4 — Contact-channel resolution  ❌ **GAP**
Templates require a reachable channel (`email` / `instagram_dm` / `facebook_dm`)
but the warehouse only reliably stores `phone`. There is no step that resolves a
contact channel per lead. Until built:
- `none_found` leads are typically **phone-only** → phone-first outreach, not the
  with-mockup email.
- The with-mockup **email** play requires a found email address; if none, either
  enrich manually or switch channel.

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

### Stage 7 — Operator send
Operator copies the draft and sends manually. Nothing in the pipeline sends.

### Stage 8 — Tracking / follow-up
Record outcome on the lead (`engagement_status`). Follow-up cadence is manual.

## Current gaps (build backlog, priority order)

1. **Contact-channel resolution (Stage 4)** — without it, only phone-first
   outreach is possible for the cleanest leads. **Now the top gap.**
2. ~~Prospect → preview-site glue (Stage 5)~~ — ✅ **built** (playbook `dist-v2` +
   deploy glue). Remaining: automate more playbook steps; **photos** in gather.
3. **Verification as a first-class pipeline step** — Stage 2 ran as an ad-hoc
   workflow; fold it into the sweep so `A_gold` is never emitted unverified, and
   add a branded-booking-page (Fresha/Booksy/Square/Toast) detector to the
   owned-site check.
4. **Fixture hygiene** — synthetic `Fixture Local N` records leak into
   `state/prospects/records/`; purge and guard against re-entry.
5. **Outreach tracking** — formalize status transitions and follow-up beyond a
   single field.

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
- Web build lane: `packages/web/` · worker `apps/worker-web`
- Caps/cost: `packages/prospecting/config/weekly_caps.yaml`
