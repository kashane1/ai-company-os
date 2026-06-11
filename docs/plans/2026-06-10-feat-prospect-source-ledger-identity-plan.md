# Prospect Source Ledger And Identity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent duplicate prospects and duplicate source queries before expanding beyond the current Google Places warehouse.

**Architecture:** Existing Google Places records remain the canonical warehouse. New source candidates must pass through an identity index before save, and every source/city/genre/query sweep is recorded in a source-run ledger. A next-qualification planner chooses current warehouse verification before recommending new data collection.

**Tech Stack:** Python dataclasses, JSON state under `state/prospects/`, existing prospect schema/storage, `pytest`.

---

### Task 1: Identity Index

**Files:**
- Create: `packages/prospecting/identity.py`
- Test: `tests/python/unit/test_prospecting_identity.py`

**Steps:**
1. Write failing tests for phone match, normalized name/address match, and no-match behavior.
2. Implement `ProspectCandidate`, `IdentityMatch`, and `IdentityIndex.from_records`.
3. Normalize phone, URL, business name, and street address.
4. Run the identity tests.

### Task 2: Source-Run Ledger

**Files:**
- Create: `packages/prospecting/source_runs.py`
- Test: `tests/python/unit/test_prospecting_source_runs.py`

**Steps:**
1. Write failing tests for stable query keys and completed-run detection.
2. Implement `SourceRunRecord` and `SourceRunStore`.
3. Store records under `state/prospects/source-runs/<source>/`.
4. Run the source-run tests.

### Task 3: Next Qualification Planner

**Files:**
- Create: `packages/prospecting/qualification.py`
- Modify: `scripts/prospect_scan.py`
- Test: `tests/python/unit/test_prospecting_qualification.py`
- Test: `tests/python/unit/test_prospecting_run.py`

**Steps:**
1. Write failing tests for choosing the next unverified warehouse cohort before new collection.
2. Implement `next_qualification_plan`.
3. Add `prospect_scan.py next-qualification`.
4. Run the focused tests and then the prospecting test slice.
