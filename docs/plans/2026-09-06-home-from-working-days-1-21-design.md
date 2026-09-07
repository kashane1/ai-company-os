# HomeFromWorking Days 1–21 Operating System Design

**Date:** 2026-09-06  
**Status:** Approved by founder through acceptance of the business-model audit and authorization to proceed  
**Source:** `state/home-from-working/audits/20260906-business-model/report-source.md`

## Objective

Turn the first 21 days of the HomeFromWorking launch plan into a safe, repeatable operating system. The system must establish trustworthy live inventory, unit economics, policy status, brand structure, opportunity evidence, and controlled experiments before more products are published.

The optimization target is **verified learning per founder minute**, not listing volume.

## Founder decisions carried forward

- Pause blanket conversion of all shirts into multi-product listings.
- Keep a shirt-with-color-and-size-variations listing as the default format.
- Test six comparable shirt-only listings against six shirt, hoodie, and crewneck multi-product listings.
- Use the working brand promise and four sections: Workday, Tiny Morale, Useful Useless, and Seasonal.
- Do not order physical samples during this phase.
- AI-assisted hero images may be explored, but they may not imply that a synthetic scene is an actual product photograph. Product color, print placement, scale, texture, and included items must remain accurate.
- Charge buyers **$4.95 for standard U.S. shipping** for the launch baseline. Do not enable a free-shipping guarantee yet.
- Keep shipping outside the item price until real single-item and combined-order fulfillment costs establish that an embedded-shipping price is both profitable and competitive.
- Turn Offsite Ads off while participation is optional. Continue modeling a 15% Offsite Ads scenario so every listing is safe if attribution becomes unavoidable later.
- Use a provisional approval floor of positive contribution in the 15% Offsite Ads scenario and at least 30% contribution after expected shipping subsidy and a conservative reserve.
- Authorize read-only Etsy and Printify reconciliation. Creating or publishing an Etsy listing remains a separate, revision-bound founder approval.

## Scope

### Days 1–7

1. Record the pause and operating decisions in a canonical launch configuration.
2. Export or retrieve active Etsy listing identity, shop state, visibility issues, stats, and buyer-query evidence where permitted.
3. Reconcile historical local records, Printify products, multi-product receipts, and Etsy listings.
4. Classify every record as matched, local-only, Printify-only, Etsy-only, ambiguous, or unresolved.
5. Resolve the two historical unresolved records by live lookup, without recreating them after a missing result.
6. Audit production-partner, AI disclosure, policy, pricing, and shipping status.
7. Produce per-variant economics for current shirt pricing and mark unknown shipping/product combinations as blocked.
8. Turn Offsite Ads off and retain evidence of the verified setting.

### Days 8–21

1. Create a manual-import format for Etsy Marketplace Insights results. Automated scraping is out of scope under current Etsy API terms.
2. Create opportunity cards from founder-provided or manually exported evidence.
3. Group the existing catalog into the four sections plus an exception bucket.
4. Apply intellectual-property, policy, evidence-quality, economics, and production-feasibility hard gates before weighted scoring.
5. Score at least 20 existing concepts using the available evidence, clearly distinguishing evidence-backed values from provisional values.
6. Record a proposed 12-listing matched pilot cohort, subject to live Etsy reconciliation.
7. Define a production-master asset standard and flag failures without regenerating approved artwork automatically.
8. Create concise HomeFromWorking ChatGPT Project instructions and outcome-specific chat templates.

## Architecture

### Canonical state

Versioned files under `state/home-from-working/operations/` are the local source of truth:

- `launch-policy.json` — founder decisions, thresholds, shipping, ads, and approval boundaries.
- `registry.json` — one normalized relationship record per design/listing/product.
- `reconciliation-report.json` — immutable run summary and mismatches.
- `economics.json` — assumptions and per-variant contribution scenarios.
- `sections.json` — catalog classification with rationale and confidence.
- `pilot.json` — matched cohort proposal and experiment contract.
- `opportunities/` — Marketplace Insights imports and scored opportunity cards.
- `project-pack/` — concise ChatGPT Project instructions and prompt contracts.
- `evidence/` — dated API snapshots, exported reports, and UI-only screenshots.

Raw evidence is preserved separately from derived state. Derived files identify their source paths and generation time.

### Etsy adapter

The first Etsy integration is read-only:

- Require the Open API v3 composite `x-api-key` value (`keystring:shared_secret`).
- Require OAuth 2.0 Authorization Code with PKCE for private shop scopes.
- Request only `shops_r listings_r` initially.
- Store the composite app credential, access token, refresh token, and expiration metadata in macOS Keychain under service `ai-company-os`.
- Never print secret values. Diagnostic output reports only presence, source, and expiry.
- Refresh access tokens deterministically and fail closed if refresh is unavailable.
- Save sanitized API responses as dated evidence.
- Provide no create, update, activate, or publish method in this phase.

The existing `.env` `ETSY_API_KEY` may be used only as a migration input for the public keystring. It is incomplete until paired with the shared secret and must not be treated as proof of API readiness.

### Printify adapter

Reuse the existing Keychain-backed Printify client and existing shop/template configuration. Add only read-only list/get operations needed for reconciliation and shipping evidence. No duplicate, update, publish, or delete action belongs in the reconciliation command.

### Registry and reconciliation

Join records using strong identifiers first:

1. Etsy listing ID and Printify `external.id`/linked-listing metadata.
2. Printify product ID from local receipts.
3. Exact normalized design key plus artwork hash.
4. Title only as a weak diagnostic signal; never auto-merge on title alone.

Each relationship includes provenance, match method, confidence, discrepancies, and next action. Missing historical Printify products become `confirmed_missing` or `unresolved`; they are never recreated automatically.

### Economics

The calculator models:

`contribution = item revenue + shipping charged - product cost - fulfillment shipping - transaction fee - payment fee - listing allocation - ad fee - reserve`

Default launch assumptions:

- U.S. shipping charged: $4.95
- Etsy transaction rate: 6.5%
- Etsy Payments rate: 3% plus $0.25
- listing allocation: $0.20
- Offsite Ads modeled: 0% and 15%
- reserve: configurable, recorded explicitly
- approval floor: contribution > 0 in the 15% scenario and margin >= 30% in the expected scenario

Unknown costs produce `blocked_missing_cost`, not a guessed approval.

### Opportunity scoring

Marketplace Insights evidence enters through a documented CSV/JSON import. The scorecard separates:

- demand evidence
- competition and differentiation
- brand fit
- thumbnail/creative strength
- expected economics
- production feasibility
- seasonal timing

Hard gates run first. A concept cannot outrank a policy, IP, margin, evidence, or production failure through weighted scoring.

### Approval and mutation boundaries

- Read-only account and API inspection: allowed by this phase authorization.
- Turning Offsite Ads off: specifically authorized; record evidence and verify after mutation.
- Public About text, disclosure text, titles, images, price, shipping profiles, and listing edits: prepare drafts, then require action-time founder confirmation because they alter buyer-facing content or economics.
- New Etsy draft creation: out of scope until linked-draft mapping is proven and the founder approves the exact payload.
- Publication or activation: always requires a separate explicit approval tied to the final revision hash.

## Error handling

- Treat timeouts and ambiguous writes as unknown outcomes and reconcile before retrying.
- Redact credentials, authorization codes, tokens, and personally identifying buyer data from logs and committed evidence.
- Keep raw exports containing buyer data outside git; commit only sanitized summaries.
- Do not scrape Etsy seller pages or Marketplace Insights with browser automation.
- Do not recreate the two unresolved Printify products if a live read confirms they are absent.
- Fail closed when live Etsy access is unavailable; produce a precise founder todo rather than filling live fields from historical assumptions.

## Verification and exit conditions

Days 1–7 exits only when each known active listing can be assigned a current owner, live ID status, policy status, margin status, and next action—or is explicitly marked blocked with a founder todo.

Days 8–21 exits only when the proposed next batch and pilot are backed by recorded evidence, hard-gate results, a matched-cohort contract, and an explicit publication boundary.

Unit tests cover credential redaction, OAuth state/PKCE behavior, pagination, reconciliation precedence, ambiguous matches, missing-product handling, economics, hard gates, section classification, and deterministic output. Live smoke tests remain read-only.
