# HomeFromWorking Days 1–21 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish the safe, evidence-backed launch operating system for HomeFromWorking through Day 21 without creating or publishing new Etsy listings.

**Architecture:** Add a narrow HomeFromWorking domain package, a read-only Etsy adapter, and deterministic CLIs that turn historical/local data plus permitted live evidence into versioned operational artifacts. Keep raw evidence separate from derived registry data and enforce mutation/approval boundaries in code and documentation.

**Tech Stack:** Python 3.12, stdlib dataclasses/JSON/CSV/urllib, existing `httpx`, ignored repository-root `.etsy.env` for Etsy credentials, pytest, Etsy Open API v3, existing Printify adapter.

> **Credential policy superseded (2026-09-07):** Any Keychain-first Etsy
> instructions in this historical implementation plan are replaced by the
> root `.etsy.env` contract in
> [`docs/founder/etsy-credentials.md`](../founder/etsy-credentials.md). Do not
> query macOS Keychain, invoke `security`, or fall back to `.env` or process
> environment for Etsy. Printify and approval-signing Keychain use is separate.

---

## Task 1: Launch policy and economics

**Files:**

- Create: `packages/home_from_working/__init__.py`
- Create: `packages/home_from_working/economics.py`
- Create: `scripts/home_from_working_launch.py`
- Create: `tests/python/unit/test_home_from_working_economics.py`
- Create: `state/home-from-working/operations/launch-policy.json`

**Steps:**

1. Write failing tests for the Etsy fee formula, $4.95 buyer-paid shipping, 0%/15% ad scenarios, 30% floor, and missing-cost failure.
2. Run the targeted test and confirm it fails for missing implementation.
3. Implement immutable assumption and result models plus deterministic calculations.
4. Add a CLI that validates and renders the approved launch policy and current shirt economics without mutating external systems.
5. Run the targeted tests and inspect the generated artifact.

## Task 2: Read-only Etsy authentication and client

**Files:**

- Create: `packages/etsy/__init__.py`
- Create: `packages/etsy/auth.py`
- Create: `packages/etsy/client.py`
- Create: `scripts/etsy_readonly.py`
- Create: `tests/python/unit/test_etsy_auth.py`
- Create: `tests/python/unit/test_etsy_client.py`

**Steps:**

1. Write failing tests for composite API-key validation, secret redaction, PKCE generation, state validation, token refresh, pagination, and read-only route construction.
2. Run the tests and confirm they fail.
3. Implement `.etsy.env`-only credential loading; never print credential material or report anything beyond key names and safe status.
4. Implement an OAuth bootstrap command requesting only `shops_r listings_r`, with browser consent and callback exchange separated from pure/testable logic.
5. Implement read-only shop, listing, inventory, shipping-profile, and receipt retrieval. Expose no write method.
6. Add a diagnostics command that reports readiness without exposing secrets.
7. Run tests plus a no-secret diagnostic smoke test.

## Task 3: Canonical registry and live reconciliation

**Files:**

- Create: `packages/home_from_working/registry.py`
- Create: `packages/home_from_working/reconcile.py`
- Create: `scripts/home_from_working_reconcile.py`
- Create: `tests/python/unit/test_home_from_working_registry.py`
- Create: `tests/python/unit/test_home_from_working_reconcile.py`
- Create: `state/home-from-working/operations/registry.json`
- Create: `state/home-from-working/operations/reconciliation-report.json`

**Steps:**

1. Write failing tests for identifier precedence, title-only ambiguity, duplicated receipts, missing Printify products, Etsy-only records, and deterministic serialization.
2. Run the tests and confirm they fail.
3. Normalize the historical catalog and multi-product receipts into canonical relationship records.
4. Add read-only Printify list/get support through the existing credential path.
5. Reconcile local, Printify, and Etsy evidence. Preserve raw snapshots and sanitize buyer/private fields.
6. Explicitly evaluate the two historical unresolved Banana Berries records; never recreate them.
7. Generate the registry/report and summarize blocked fields.

## Task 4: Trust and production-master audit

**Files:**

- Create: `packages/home_from_working/trust.py`
- Create: `packages/home_from_working/assets.py`
- Create: `scripts/home_from_working_audit.py`
- Create: `tests/python/unit/test_home_from_working_trust.py`
- Create: `tests/python/unit/test_home_from_working_assets.py`
- Create: `state/home-from-working/operations/trust-audit.json`
- Create: `state/home-from-working/operations/asset-audit.json`

**Steps:**

1. Write failing tests for required production-partner/AI fields and image file, transparency, dimension, padding, and effective-DPI checks.
2. Run the tests and confirm they fail.
3. Implement deterministic audits that report pass/fail/unknown without rewriting artwork or public copy.
4. Treat AI hero scenes as illustrative mockups and require a no-misrepresentation note in their manifest.
5. Audit current available records/assets and write founder-actionable summaries.

## Task 5: Sections, opportunity cards, and candidate scoring

**Files:**

- Create: `packages/home_from_working/opportunities.py`
- Create: `scripts/home_from_working_opportunities.py`
- Create: `tests/python/unit/test_home_from_working_opportunities.py`
- Create: `state/home-from-working/operations/marketplace-insights-template.csv`
- Create: `state/home-from-working/operations/sections.json`
- Create: `state/home-from-working/operations/opportunities/scored-concepts.json`

**Steps:**

1. Write failing tests for Marketplace Insights import validation, four-section classification, exception handling, hard gates, confidence labels, and stable ranking.
2. Run the tests and confirm they fail.
3. Implement a manual evidence importer; do not automate or scrape Etsy Marketplace Insights.
4. Classify the 70 historical records with primary section, optional secondary section, rationale, and confidence.
5. Score at least 20 existing concepts. Missing Marketplace Insights values remain `provisional`, never fabricated.
6. Generate the opportunity artifact and a concise founder todo for the 15 manual searches.

## Task 6: Pilot contract and ChatGPT Project operating pack

**Files:**

- Create: `packages/home_from_working/pilot.py`
- Create: `tests/python/unit/test_home_from_working_pilot.py`
- Create: `state/home-from-working/operations/pilot.json`
- Create: `state/home-from-working/operations/project-pack/PROJECT_INSTRUCTIONS.md`
- Create: `state/home-from-working/operations/project-pack/CHAT_TEMPLATES.md`
- Create: `state/home-from-working/operations/project-pack/OUTPUT_CONTRACT.json`

**Steps:**

1. Write failing tests for six matched pairs, allowed product formats, one-major-variable isolation, provisional traffic thresholds, and publication approval.
2. Run the tests and confirm they fail.
3. Encode six proposed shirt-only versus three-product pairs, conditional on live Etsy eligibility.
4. Add the concise-title experiment as a separate smaller cohort so it does not contaminate the product-format test.
5. Write compact Project instructions covering the promise, pillars, creative/provenance rules, output contract, and token-efficient model routing.
6. Verify that credentials, mutable approval state, and repository dumps are excluded.

## Task 7: Etsy account evidence and founder todos

**Files:**

- Create: `state/home-from-working/operations/evidence/README.md`
- Create: `state/home-from-working/operations/day-1-21-status.md`
- Create pending todo files under: `todos/`

**Steps:**

1. Use the Etsy UI only for the specifically authorized Offsite Ads opt-out; capture dated evidence and re-check the setting.
2. Inspect developer-app readiness read-only. Ask at action time before revealing/storing a shared secret, creating credentials, or completing OAuth consent.
3. Retrieve Etsy exports or API snapshots if access exists. Otherwise create exact todos for the founder-owned export/consent steps.
4. Do not automate Marketplace Insights scraping. Provide the 15-search worksheet.
5. Create todos only for actions that truly require founder account access, representational approval, or material creative judgment.
6. Record each Day 1–21 deliverable as complete, partial, blocked, or intentionally skipped, with evidence paths.

## Task 8: Integrated verification and documentation

**Files:**

- Modify: `docs/founder/printify-shirt-workflow.md`
- Modify: `docs/plans/INDEX.md`
- Modify: `README.md` only if the architecture entry point materially changes

**Steps:**

1. Run all new focused unit tests.
2. Run the existing POD unit suite to prove no regression.
3. Run read-only live smoke checks where credentials are available.
4. Review generated JSON for deterministic ordering, redaction, source provenance, and approval boundaries.
5. Update the founder workflow to point to the launch policy, registry, and pilot contract while preserving the repeatable shirt workflow.
6. Perform spec-compliance and code-quality review, fix all material findings, and rerun verification before declaring completion.
