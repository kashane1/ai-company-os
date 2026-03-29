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
