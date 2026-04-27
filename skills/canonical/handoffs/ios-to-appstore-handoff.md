---
id: ios-to-appstore-handoff
name: iOS to App Store Handoff
purpose: Prepare and validate the handoff from iOS implementation to App Store release operations.
owner_agent: ios
target_runtimes: [claude, codex]
stage: active
inputs:
  - product_id (e.g. fishing-logbook)
  - build version and build number
  - list of features and fixes included in this build
  - path to the release-ready build artifact or confirmation of successful archive
outputs:
  - a handoff checklist confirming release readiness
  - a release candidate record for the App Store worker
  - metadata inputs derived from the product artifact chain
allowed_edit_boundaries:
  - state/artifacts/ios/
  - state/artifacts/appstore/
  - state/checkpoints/platform/releases/
forbidden_areas:
  - products/ (source code should not change during handoff)
  - packages/policies/ (policy is read-only input)
  - infra/
dependencies:
  - app-store-positioning.md must exist at docs/products/<product-id>/
  - mvp-spec.md must exist at docs/products/<product-id>/
  - build must have passed validation (tests, lint, archive success)
validation_steps:
  - all checklist items are confirmed or explicitly waived with reason
  - release candidate record exists in state/checkpoints/platform/releases/
  - metadata draft references app-store-positioning.md
  - no source code was modified during the handoff
handoff_contract:
  what_is_handed_off: release candidate record, metadata draft, screenshot list
  handed_to: appstore worker for TestFlight and submission preparation
claude_adaptation_notes: |
  Claude can run this skill by reading the product artifacts, checking the
  build state, and walking through the checklist interactively with the user.
codex_adaptation_notes: |
  Codex should not run this skill directly. The App Store worker orchestrates
  the receiving side. Codex may assist with metadata text drafting as a
  sub-task if needed.
---

## Instructions

### 1. Verify build readiness

Confirm the following before proceeding:

- [ ] Build compiles without errors
- [ ] All tests pass
- [ ] Xcode archive succeeds
- [ ] Build version and build number are set correctly
- [ ] No debug flags or test configurations are active in the release scheme

### 2. Prepare the feature manifest

Create a feature manifest listing:

- new features in this build (reference backlog items or task IDs)
- bug fixes included
- known issues or limitations
- any features deferred from the original plan

### 3. Draft metadata inputs

Read `docs/products/<product-id>/app-store-positioning.md` and draft:

- release notes for this version
- any updates to the app description if new features change positioning
- screenshot requirements (new screens or changed screens that need updated screenshots)

Write metadata draft to `state/artifacts/appstore/<product-id>-<version>-metadata-draft.md`.

### 4. Create the release candidate record

Write a release candidate record containing:

```yaml
product_id: <product-id>
version: <version>
build_number: <build-number>
features: [list of feature summaries]
fixes: [list of fix summaries]
known_issues: [list or empty]
metadata_draft_path: state/artifacts/appstore/<product-id>-<version>-metadata-draft.md
build_validated: true
handoff_timestamp: <ISO 8601>
status: pending_appstore_review
```

Write to `state/checkpoints/platform/releases/<product-id>-<version>.json`.

### 5. Confirm the handoff

The iOS lane's job is done when:

- the build is validated
- the release candidate record exists
- the metadata draft is ready for the App Store worker
- no source code was modified during this process

The App Store worker picks up from here using the release candidate record.

## Required release-candidate-record fields

The YAML record at `state/checkpoints/platform/releases/<product-id>-<version>.json`
MUST include every field below. Missing any field blocks the App Store
worker; validation reports the missing field by name.

| Field | Type | Description |
|-------|------|-------------|
| `product_id` | string | Matches an entry in `infra/products.json`. |
| `version` | string | Marketing version (e.g. `1.0.0`). |
| `build_number` | int or string | CFBundleVersion. Must increase monotonically against the last submitted build. |
| `features` | list of string | One-line summaries; reference task IDs where available. |
| `fixes` | list of string | Bug-fix summaries. May be empty. |
| `known_issues` | list of string | Empty list is allowed; missing key is not. |
| `metadata_draft_path` | string | Resolves to a real file under `state/artifacts/appstore/`. |
| `build_validated` | bool | Must be `true`. A `false` value should never reach this record — fail the handoff before writing instead. |
| `handoff_timestamp` | ISO 8601 string | UTC. |
| `status` | enum | One of `pending_appstore_review`, `submitted`, `in_review`, `approved`, `rejected`. Initial value is `pending_appstore_review`. |

## Screenshot readiness check

Before writing the release-candidate record, scan the App Store
screenshot set declared by `app-store-positioning.md`:

- Every required device size has a screenshot (per current Apple
  requirements: 6.7" iPhone, 6.5" iPhone, 5.5" iPhone, plus iPad sizes
  if iPad is supported).
- Screenshots reflect the current build (no UI elements that have been
  removed; no missing UI elements that this release adds).
- If any screenshot is missing or stale, surface as a blocking
  finding under "Screenshot gaps" in the metadata draft and pause
  the handoff.

## TestFlight transition note

This skill produces a release candidate record in
`pending_appstore_review` state. The App Store worker is responsible
for the TestFlight build upload, internal-tester distribution, and
the eventual `submitted` → `in_review` → `approved`/`rejected`
transitions. The iOS lane MUST NOT advance the status field beyond
`pending_appstore_review`.

## Failure modes

- **Build validation incomplete.** If any of (compile, tests, archive)
  failed, do NOT create the release candidate record. Emit a blocking
  message naming which gate failed.
- **Metadata reference broken.** If `app-store-positioning.md` is
  missing or has not been updated since the last submitted version,
  the metadata draft must include `## Positioning gap` flagging this;
  the handoff continues but the App Store worker will pause until the
  gap is addressed.
- **Build number regression.** If `build_number` is ≤ the last submitted
  build, halt — Apple will reject the upload. Bump the build number
  and re-archive before proceeding.
- **Source modification during handoff.** Re-running `git status` after
  step 4 must show zero uncommitted changes under `products/`. If it
  does, abort and ask the operator which changes are intentional.

## Worked example

For Catchbook v1.0.0, build 42, release-candidate record:

```yaml
product_id: catchbook
version: 1.0.0
build_number: 42
features:
  - "Spot detection from waterbody name + GPS (mvp-spec §3.2)"
  - "Catch list with weight, length, species (mvp-spec §3.4)"
fixes:
  - "SwiftData migration adds optional `species` to `Catch` (issue #38)"
known_issues: []
metadata_draft_path: state/artifacts/appstore/catchbook-1.0.0-metadata-draft.md
build_validated: true
handoff_timestamp: 2026-04-27T16:00:00Z
status: pending_appstore_review
```

## References

- Apple App Store screenshot specs: https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications
- Build number guidance: https://developer.apple.com/library/archive/qa/qa1827/_index.html
- Positioning input: `skills/canonical/shared/app-store-positioning-pack.md`
- Sibling polish skill: `skills/canonical/products/catchbook/ios-ui-polish-review.md`
