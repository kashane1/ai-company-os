---
status: open
summary: Preserve native Printify duplicates and use a small API runner for artwork and copy changes.
owner: kashane
last_reviewed: 2026-09-02
---

# Repeatable Printify drafts implementation plan

**Goal:** turn an owner-supplied PNG into a correctly configured shirt draft without rebuilding its mockup selection or writing a new script per shirt.

**Architecture:** use Printify's native Duplicate action once, then a narrow Python runner for preflight, approved artwork upload, partial product update, and read-back verification. Runtime snapshots and receipts stay under `state/home-from-working/`. The runner cannot create, publish, delete, change prices, or approve its own operations.

**Tech stack:** existing Python, httpx, Pillow, macOS Keychain secret helper, shared ApprovalRecord/ApprovalStore and pytest.

## Evidence and choice

- Public API creation is reconstruction, not native duplication. The official API/OpenAPI has no duplicate or writable mockup-selection operation.
- Native Duplicate preserves the setup according to Printify's official help.
- A disposable live test on September 2 preserved all 14 mockups, their order and primary image through native duplication and an API artwork replacement. Browser inspection confirmed the new artwork rendered on the retained mockups. No reselection was needed.
- API-only reconstruction would still require selecting mockups. Full browser creation would repeat unnecessary work. Native Duplicate plus API updates is the selected bounded process.
- Preservation through artwork updates is observed behavior, not a documented guarantee. Verify every run and stop on drift rather than silently reconstructing the listing.

## Implementation steps

1. Add `packages/pod/template.py` and unit tests for native-copy identity, variant/settings preservation, mockup signatures, PNG placement and final verification.
2. Add `packages/policies/pod.py` to require an approved shared record bound to the exact draft manifest revision. Never accept an approval boolean in product input.
3. Add `packages/pod/runner.py` and `scripts/pod_draft.py`. Prepare with GET calls only; keep upload and update separate from approval. Preserve copied SKUs and every unrelated field. Cache upload receipts and reconcile ambiguous failures before retrying.
4. Add an operator runbook and link it from repository entry points. Document the single native-duplicate UI step, API gaps, current template identity and input contract.
5. Run matching tests, a no-write prepare against the saved live-test snapshots, and a read-only check of the configured template. Record the live-test cleanup. No further live product is needed for validation.

## Verification contract

Tests must cover live-target refusal, stale/missing approval, changed artwork, changed variants, missing/reordered mockups, idempotent retry, ambiguous upload recovery and absence of publish/create endpoints. UI automation is restricted to Duplicate and one visual review; routine inspection uses compact API summaries. No worker, queue, research lane or new dashboard is part of this change.

## Local implementation result — September 2

All five steps are implemented locally. The plan remains `open` until the changes are integrated, following the plans index convention.

- Targeted runner/helper/shared-approval suite: **38 passed**.
- Full helper validation and read-only preparation passed against the saved native-copy and artwork-update snapshots, with no further account writes.
- Read-only CLI `inspect` confirmed the current source, 14 selected mockups, eight White S–5XL variants, and current prices.
- The disposable live-test copy was removed; all six original products were unchanged.
- The [operator workflow](../founder/printify-shirt-workflow.md) records API limits, exact commands, shared approval registration, recovery, and visual review.

Review limits are explicit: the public API does not document an atomic draft-only update, so an apply operation requires exclusive use of that draft until verification finishes. Runtime receipts are trusted local state, not signed records against local modification. The CLI loads the shared decision by ID; the Python helpers support injected dependencies for tests.
