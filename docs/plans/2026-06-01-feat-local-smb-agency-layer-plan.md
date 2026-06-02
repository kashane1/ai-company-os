---
title: "feat: Local-SMB Agency Layer"
type: feat
status: open
date: 2026-06-01
change_id: agency-layer-v1
related_brainstorm: docs/brainstorms/2026-06-01-agency-layer-brainstorm.md
owner: kashane
last_reviewed: 2026-06-01
---

# Local-SMB Agency Layer

## Overview

Turn `ai-company-os` into the operating system for a local-SMB agency: not "we
sell websites" but **"we operate the digital presence for local businesses."**
The website is product #1 of a four-tier service stack; the recurring tiers
above it (reviews, local SEO, reporting, ads, automation) are where margin and
defensibility live.

Source analysis: [docs/brainstorms/2026-06-01-agency-layer-brainstorm.md](../brainstorms/2026-06-01-agency-layer-brainstorm.md).

This plan sequences the build so that each phase ships something usable and
unblocks the next. It deliberately reuses the already-shipped lanes — prospecting
(Phase 1–2), the web/webdeploy lane (F1–F8), `landing-page-build`, and
`web-ux-audit` — and adds only the missing client-lifecycle seam plus the
service-stack scaffolding.

The first shipping target (Phases 1–5) delivers an end-to-end path from a
`human_verified` prospect to a launched Package-A client website. Phases 6–7 add
the first high-margin recurring services (local SEO, monthly reporting). Phase 8
is demand-driven and intentionally deferred.

## Problem Statement

Two halves of the agency already exist and are not connected. The prospecting
pipeline produces exactly the target businesses (local SMBs with no owned
website, demand signal, human-verified). The web lane can scaffold, build,
deploy, audit, and monetize a site. **Nothing turns a verified prospect into a
registered, paying, recurring client**, and there is no model for the services
that sit above the website — the part of the stack that actually makes money.

We also have no typed source of truth for what we sell. Pricing, edit limits,
ownership, and cancellation terms would otherwise live in ad-hoc markdown and
drift from anything that bills or reports.

## Constraints & conventions

- **Python-first** platform code; lightweight frameworks (REPO_MAP / CLAUDE.md).
- New schemas in `packages/schemas/` and policy edits in `packages/policies/`
  **require founder approval** (REPO_MAP "must NOT go" table). Phases that touch
  them call this out explicitly.
- Skills follow canonical → adapter → `registry.yaml` → `.claude/skills/` wiring
  (`skills/WIRING.md`). No skill logic in `.claude/skills/`.
- Runtime state writes go to `state/`, never source folders.
- Every platform feature ships with tests under `tests/python/unit/`.
- Irreversible/external actions go behind the existing approval surface
  (`packages/policies/approvals.py`).

## Phase 1 — Service catalog as typed config

**Goal:** one typed source of truth for every service and the A/B/C bundles.
Smallest phase; unblocks everything downstream.

Deliverables:

- `packages/schemas/offer.py` — `Service` and `OfferTier`/`Bundle` dataclasses:
  `service_id`, `bill_type` (`one_time` | `recurring`), `setup_fee`,
  `monthly_fee`, `edit_limit`, `includes[]`, `ownership`, `cancellation`,
  `support_sla`. (**Founder approval required** — new schema.)
- `packages/agency/__init__.py`, `packages/agency/catalog.yaml` — the actual
  services + `package_a` / `package_b` / `package_c` bundles from the brainstorm.
- `packages/agency/catalog.py` — loader + validation (every bundle references
  real `service_id`s; fees non-negative; recurring services carry a monthly fee).
  Mirror the existing dataclass `from_dict`/`to_dict` round-trip convention
  (`packages/schemas/prospect.py`, `packages/prospecting/storage.py`) rather than
  ad-hoc YAML parsing. (`packages/agency/` is a new shared subpackage — allowed;
  not gated by the REPO_MAP "must NOT go" table.)
- `docs/agency/service-catalog.md` — human-readable render of the same data.
- `tests/python/unit/test_agency_catalog.py` — schema round-trip, bundle
  integrity, render parity.

Acceptance: `catalog.py` loads `catalog.yaml`, validates referential integrity,
and the three bundles resolve to concrete service lists with totals.

## Phase 2 — Client model in the product registry

**Goal:** represent a client engagement as a managed product without forking a
parallel `clients/` tree.

> **Reviewer correction (P1):** the registry is **not** a tolerant schema. It is
> a strict typed loader — `packages/config/products.py:load_product_configs`
> reads `platform`, `repo_id`, `source_path`, `docs_root` as **required keys**
> (no `.get` fallback) and builds a `frozen` `ProductConfig`
> (`packages/schemas/product.py`). `ProductPlatform` has only `IOS`/`WEB` and
> there is no `type` field; a partial `client-site` record raises
> `KeyError`/`ValueError` and breaks `apps/api/platform.py:register_product`.
> This phase is therefore a **schema + loader change, not a products.json-only
> edit.**

Deliverables:

- **(Founder approval required — schema edit.)** Extend `ProductConfig`
  (`packages/schemas/product.py`) with a `type` field (`ios` | `client-site`) and
  an optional `client {}` block: `ownership`, `bundle` (FK to catalog),
  `services[]`, `from_prospect`, `billing_status`,
  `phase` (`onboarding|building|live|offboarding`). Decide: add `CLIENT_SITE` to
  `ProductPlatform` vs. keep `platform: web` and discriminate on `type`.
- Make `load_product_configs` branch on `type`: relax the `repo_id` /
  `source_path` requirements that don't apply to client sites and parse the
  `client {}` block. Add a `client-site` record to `infra/products.json`.
- Audit registry consumers for `config.platform` assumptions —
  `apps/api/platform.py:register_product` and
  `packages/tools/product_artifacts/projection.py` — and make them tolerate or
  skip `client-site` as appropriate.
- `tests/python/unit/test_product_registry_client.py` — a `client-site` record
  loads through `load_product_configs`, validates `bundle` against the catalog,
  round-trips, and does **not** break `register_product`.

Acceptance: a hand-written `joes-plumbing-site` record loads, validates against
the catalog, is selectable by `type == client-site`, and existing iOS/web product
loading is unaffected.

Dependency: Phase 1 (bundle FK).

## Phase 3 — Prospect → client promotion (the crown jewel)

**Goal:** the one-way, approval-gated transition that connects the two existing
halves.

> **Reviewer corrections (P1/P2):**
> - The approval mechanism is **not** "add an enum code and wire through a gate."
>   `packages/policies/approvals.py` holds only the `PolicyViolationCode` enum,
>   the `PolicyViolation` class, and `is_approval_granted`. The real pattern is a
>   **dedicated `assert_<action>(..., *, approval_granted: bool)` function in its
>   own policy module** that raises `PolicyViolation(code, detail)` — see
>   `deploy_readiness.assert_deploy_ready` / `assert_custom_domain_allowed` and
>   `discovery_gates.assert_bulk_crawl_allowed`. The enum member alone is inert.
> - `human_verified` is a **tri-state enum** (`HumanVerified.UNSET|TRUE|FALSE`,
>   `packages/schemas/prospect.py:40`), not a boolean.
> - The "no-outreach boundary" is a **documentation convention, not a code gate**
>   — there is no enforcement in the prospect layer today, so adding
>   outreach-implying states is a new risk surface, not a reuse of an existing
>   guard.

Deliverables:

- **(Founder approval required — schema edit.)** Extend `packages/schemas/prospect.py`
  with an `engagement_status` track: `none → contacted → replied → proposal_sent →
  won → onboarded` (+ `lost`). Document these as **operator-set-only, no automated
  transitions**, until the Phase 8 consent model lands; no send path is introduced
  here. Leave `ProspectStatus` (scan-pipeline status) untouched.
- New policy module **`packages/policies/agency_gates.py`** with
  `assert_promotion_allowed(...)` and `assert_proposal_send_allowed(...)`,
  mirroring `deploy_readiness.assert_custom_domain_allowed`. Decide bool-param vs.
  `is_approval_granted(approval_id, expected_type)` token audit (the latter is the
  precedent for typed approvals — `release_readiness.approve_app_store_submission`).
- **(Founder approval required — policy edit.)** Add `PROPOSAL_SEND_NOT_APPROVED`
  and `CLIENT_PROMOTION_NOT_APPROVED` to `PolicyViolationCode` under a new
  `# --- Agency layer ---` group, and add an agency-codes-present assertion to
  `tests/python/unit/test_policy_violation_codes.py` (mirroring
  `test_x1_plan_codes_all_present`) so the new codes and their raise sites land
  together.
- `packages/agency/promotion.py` —
  `promote_prospect_to_client(prospect_id, bundle, *, approval_granted)`: calls
  `assert_promotion_allowed`, asserts
  `record.human_verified is HumanVerified.TRUE` (rejecting `UNSET` and `FALSE`),
  writes a `type: client-site` registry record, scaffolds the client docs
  workspace from the **Phase 3-owned template stubs** (below), backlinks
  `client.from_prospect`.
- **Minimal client-workspace template stubs** are owned here so promotion has
  something to scaffold; Phase 4 fleshes out their content. (Resolves the former
  Phase 3 → Phase 4 forward dependency.)
- `scripts/promote_prospect.py` — operator CLI (mirrors `scripts/prospect_scan.py`).
- `tests/python/unit/test_agency_promotion.py` — refuses `UNSET`/`FALSE`
  prospects, refuses without approval (raises `CLIENT_PROMOTION_NOT_APPROVED`),
  idempotent re-runs, correct backlink.

Acceptance: a `HumanVerified.TRUE` prospect + granted approval produces a valid
`client-site` registry record and a scaffolded docs workspace; an `UNSET`/`FALSE`
or unapproved attempt raises the right `PolicyViolation`.

Dependency: Phases 1–2.

## Phase 4 — Client intake + site scaffold (delivers Package A's website)

**Goal:** generate the anchor website from a structured intake, reusing the web
scaffold.

> **Reviewer corrections (P1/P2/P3):**
> - `landing-page-build` and `web-ux-audit` are `kind: agentic`,
>   `fixture_status: missing` (`skills/registry.yaml`), so the loader
>   (`packages/tools/skills/loader.py`) **refuses to load them in autonomous
>   mode**. The composable, callable building blocks are the **packages**, not the
>   skills: `packages/web/scaffold.py`, `packages/web/ux_audit.audit_dist()`,
>   `packages/web/validation.validate_web_dist()`.
> - `validate_web_dist` validates a **built `dist/`**, not Astro source — the
>   acceptance path needs a Node/Astro build, or use
>   `scaffold.render_landing_html()` for the offline-no-Node preview path.
> - Any **new** skill defaults to `fixture_status: missing` and is unloadable
>   autonomously until fixtures exist (see cross-cutting "Skill loadability").

Deliverables:

- `client-intake` skill (canonical + claude adapter + `registry.yaml` entry +
  `.claude/` pointer + **trigger phrases in `docs/skills-index.md`**). Either
  author `client-intake.fixtures.yaml` and set `fixture_status: passing`, **or**
  declare it operator-invoked (`mode="manual"`, no autonomous dispatch). Output:
  `CLIENT_BRIEF.md` (business type, services, location, ideal customer, hours,
  photos, reviews, competitors).
- Flesh out the client docs workspace templates (stubs from Phase 3) under
  `docs/products/<slug>-site/`: `OFFER.md` (renders from catalog + bundle),
  `SITE_MAP.md`, `COPY.md`, `LOCAL_SEO.md`, `BOOKING.md`, `REVIEWS.md`,
  `MAINTENANCE_PLAN.md`, `LAUNCH_CHECKLIST.md`, `reports/`.
- Extend `packages/web/scaffold.py` token context to accept intake +
  service-category theme (extend it, do not fork a new "site factory"). Source
  lands in `products/<slug>-site/`.
- `tests/python/unit/test_client_intake_scaffold.py` — intake → workspace +
  buildable scaffold; `OFFER.md` matches the catalog bundle.

Acceptance: `client-intake` + scaffold yields a workspace and an Astro project
that builds and passes `packages/web/validation.validate_web_dist()` on the built
`dist/` (or `render_landing_html()` passes the offline preview check).

Dependency: Phases 1–3; reuses `packages/web/scaffold.py`,
`packages/web/validation.py`.

## Phase 5 — Launch checklist (delivery gate)

**Goal:** a repeatable, gated launch.

Deliverables:

- `launch-checklist` skill that **composes the pure callable
  `packages/web/ux_audit.audit_dist()` (`UxAuditReport.passed()`)** — not the
  agentic `web-ux-audit` skill (blocked autonomously; see Phase 4). Checks:
  domain, DNS, SSL, contact form, mobile test, SEO metadata
  (title/description/OG), GBP link, analytics tag. Register trigger phrases in
  `docs/skills-index.md`; set `fixture_status: passing` (+ fixtures) or declare
  operator-invoked.
- Route deploy through existing gates — `deploy_readiness.assert_deploy_ready`
  (`DEPLOY_DNS_NOT_APPROVED`, `DEPLOY_SPEND_NOT_APPROVED`) and
  `assert_custom_domain_allowed`. Add a distinct
  `CLIENT_DOMAIN_DEPLOY_NOT_APPROVED` code only if client-owned domains need a
  separate token (decide during this phase).
- `tests/python/unit/test_launch_checklist.py` — checklist fails closed on any
  missing item; passes only when `audit_dist().passed()` is true and gates are
  approved.

Acceptance: a scaffolded client site cannot be marked `live` until the checklist
passes (`audit_dist().passed()`) and deploy approvals are granted.

Dependency: Phase 4; reuses `packages/web/ux_audit.py`, `packages/web/deploy.py`,
`packages/policies/deploy_readiness.py`.

**— End of first shipping target (prospect → launched Package-A site) —**

## Phase 6 — Local SEO page generator (first high-margin recurring service)

**Goal:** mass-generate locally targeted pages from a service × geo matrix — the
highest-leverage AI service.

Deliverables:

- Extend `packages/web/scaffold.py` (or a sibling `local-seo-pages` skill —
  fixtures/operator-invoked per Phase 4) to take a `service × geo` matrix from
  `LOCAL_SEO.md` and emit differentiated pages (e.g. "Roof Repair Dallas",
  "Emergency Roof Repair Dallas") with per-page metadata, internal linking, and
  dedup/near-dup guards so pages aren't thin.
- Audit hook: pages run through `ux_audit.audit_dist()` + a thin-content check
  before publish.
- `tests/python/unit/test_local_seo_pages.py` — matrix → N distinct pages,
  metadata correctness, near-duplicate rejection.

Acceptance: a 4-service × 3-city matrix produces 12 distinct, audit-passing pages
with unique titles/metadata.

Dependency: Phase 4.

## Phase 7 — Monthly report generator (retainer engine)

**Goal:** owner-friendly recurring report + scheduling.

**Blocked on the analytics-source decision** (see Open Decisions). Resolve first.

Deliverables:

- Analytics adapter seam (mirrors `DeployTarget`): pluggable source
  (Plausible/Umami or GA4) + form-submission capture + optional call-tracking.
- `monthly-report` skill (fixtures/operator-invoked per Phase 4; register trigger
  phrases in `docs/skills-index.md`): emits
  `docs/products/<slug>-site/reports/MONTHLY_REPORT-YYYY-MM.md` with
  owner-friendly metrics (phone calls, form submissions, bookings, edits done,
  recommended next action) — not sessions/bounce rate.
- Per-client scheduled task drafts the report monthly and routes it to the
  operator for review before send.
- Optional: surface the report as a live re-openable artifact.
- `tests/python/unit/test_monthly_report.py` — given a fixture analytics payload,
  the report renders the right metrics and the recommended-action prose.

Acceptance: a fixture analytics payload produces a correct dated report; the
scheduled task drafts (does not auto-send) it.

Dependency: Phases 2, 4; analytics-source decision.

## Phase 8 — Demand-driven services (deferred)

Built only as clients buy up the stack, each behind its own connector + approval
gate; not upfront. Each becomes its own follow-up plan when scheduled:

- **GBP optimize** — `gbp-optimize` skill + Google Business Profile connector +
  `GBP_EDIT_NOT_APPROVED` gate.
- **Booking setup** — Calendly/Square/Vagaro/Acuity/Mindbody integration.
- **Review system** — Twilio SMS + GBP review link + cadence; **TCPA consent
  model required** before any send.
- **Follow-up automation** — SMS + email + scheduler; **TCPA/CAN-SPAM** gates.
- **Ads (Google/Meta)** — connectors + **ad-spend approval gates**; avoid until
  we choose to learn them.
- **CRM setup** and **Tier-4 fractional-CTO** projects — bespoke, quoted per
  engagement; QuickBooks and other financial systems are **read-only/categorize
  only, never move money** (platform financial-action rule).

## Cross-cutting: approvals & compliance

| Action | Gate |
|---|---|
| Deploy / DNS / spend | existing `DEPLOY_*`, `PAYMENTS_LIVE_NOT_APPROVED` |
| Send proposal | new `PROPOSAL_SEND_NOT_APPROVED` (Phase 3) |
| Promote prospect → client | new `CLIENT_PROMOTION_NOT_APPROVED` (Phase 3) |
| Deploy to client-owned domain | reuse `DEPLOY_DNS_*` or new `CLIENT_DOMAIN_DEPLOY_*` (Phase 5) |
| Edit live GBP | new `GBP_EDIT_NOT_APPROVED` (Phase 8) |
| Launch/adjust ad spend | new ad-spend gate (Phase 8) |
| Touch client finances (QuickBooks) | read-only only; never move money |
| Outreach / SMS / email send | TCPA/CAN-SPAM consent + deferred (Phase 8) |

Each new code ships with a **dedicated `assert_*` function** in a policy module
(e.g. `packages/policies/agency_gates.py`) that raises `PolicyViolation` — the
enum member alone is inert. All policy/schema edits flagged above require founder
approval per REPO_MAP.

## Cross-cutting: skill loadability

Every skill this plan adds (`client-intake`, `launch-checklist`, `monthly-report`,
`gbp-optimize`, …) and every existing skill it leans on (`landing-page-build`,
`web-ux-audit`) is governed by the loader gate in
`packages/tools/skills/loader.py`: a skill with `kind: agentic` and
`fixture_status != "passing"` **cannot be loaded in `mode="autonomous"`**, and
`reconciliation.py` fails any skill marked `passing` without fixtures on disk.
The existing reusable logic therefore lives in the **`packages/web` callables**
(`scaffold.py`, `ux_audit.audit_dist()`, `validation.validate_web_dist()`), which
compose freely today. For each new skill, choose explicitly: author a
`<skill>.fixtures.yaml` and set `fixture_status: passing`, or declare it
operator-invoked (`mode="manual"`) with no autonomous dispatch. Register trigger
phrases in `docs/skills-index.md` either way (no collisions with the existing
recon/polish family were found).

## Open Decisions (resolve before the blocked phases)

1. **Analytics source** (blocks Phase 7): Plausible/Umami vs GA4; lead/call capture.
2. **Billing system of record**: Stripe-as-retainer-biller vs PoC only.
3. **SMS/email provider** + consent model (blocks Phase 8 review/follow-up).
4. **Domain & DNS ownership**: client-owned-we-manage vs we-hold-it (affects
   Phase 5 gate + offboarding).
5. **Offboarding/cancellation**: export / freeze / hand over a `client-owned`
   asset — define before the first paying client.
6. **Tier-4 scope**: explicit offering vs opportunistic upsell.
7. **Geography**: prospecting is Seattle-only; national scale-out stays deferred.

## Sequencing summary

```
Phase 1  catalog ──┐
Phase 2  registry ─┼─► Phase 3  promotion ─► Phase 4  intake+scaffold ─► Phase 5  launch
                   │                                     │
                   └─────────────────────────────────────┼─► Phase 6  local SEO
                                                          └─► Phase 7  reporting (needs analytics decision)
Phase 8  demand-driven services (deferred, per-service plans)
```

First shipping target: Phases 1–5 (prospect → launched Package-A site).
