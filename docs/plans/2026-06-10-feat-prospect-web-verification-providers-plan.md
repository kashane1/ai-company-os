# Prospect Web Verification Providers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add first-class automated web-presence verification for local SMB prospects using Brave Search or DataForSEO, behind one provider-neutral prospecting contract.

**Architecture:** Candidate collection remains separate from outreach. A verifier turns a prospect into a search query, normalizes provider results into one local `SearchResult` shape, classifies the web presence as `owned_site`, `marketplace_only`, `social_only`, `none_found`, or `ambiguous`, and writes `web_verify_*` fields back to the prospect record. Provider clients handle only search transport; classification is local and tested offline.

**Tech Stack:** Python dataclasses, `httpx`, existing JSON prospect storage, `pytest`, `httpx.MockTransport`.

---

### Task 1: Schema And Classifier

**Files:**
- Modify: `packages/schemas/prospect.py`
- Create: `packages/prospecting/web_presence.py`
- Test: `tests/python/unit/test_prospecting_web_presence.py`

**Steps:**
1. Write failing schema/classifier tests for round-tripping `web_verify_*` fields and classifying owned, social, marketplace, none-found, and ambiguous result sets.
2. Run the new test file and confirm it fails because the module/fields do not exist.
3. Add `WebVerifyVerdict` plus `web_verify_class`, `web_verify_verdict`, `web_verify_url`, `web_verify_confidence`, `web_verify_note`, `web_verified_at`, and `web_verify_method` to `ProspectRecord`.
4. Implement provider-neutral search result models and conservative classifier helpers in `web_presence.py`.
5. Run the new test file and confirm it passes.

### Task 2: Provider Clients

**Files:**
- Modify: `packages/prospecting/web_presence.py`
- Test: `tests/python/unit/test_prospecting_web_presence.py`

**Steps:**
1. Add failing tests for Brave request headers/response parsing and DataForSEO standard POST/GET response parsing.
2. Run the targeted tests and confirm they fail because provider clients are missing.
3. Implement `BraveSearchVerifier` and `DataForSEOSearchVerifier` with explicit env var constants and no live network in tests.
4. Run the targeted tests and confirm they pass.

### Task 3: CLI Wiring

**Files:**
- Modify: `scripts/prospect_scan.py`
- Test: `tests/python/unit/test_prospecting_run.py`

**Steps:**
1. Add a failing CLI test for `prospect_scan verify-web --provider stub --cohort A_gold --limit 1`.
2. Implement a provider factory for `brave`, `dataforseo`, and test-only `stub`, then update records through the existing `ProspectRepository`.
3. Print a concise run summary with verdict counts and provider method.
4. Run prospecting tests and the new web-presence test file.

### Task 4: Verification

**Files:**
- Test-only.

**Steps:**
1. Run `python3 -m pytest tests/python/unit/test_prospecting_web_presence.py tests/python/unit/test_prospecting_schemas.py tests/python/unit/test_prospecting_run.py tests/python/unit/test_prospecting_google_places.py`.
2. If failures are unrelated to this change, isolate and report them; otherwise fix and rerun.
