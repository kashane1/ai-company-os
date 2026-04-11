# App Store Worker Lane

This document defines the operational scope, inputs, outputs, and workflow of the App Store worker.

It complements `ios-lane.md`, which covers the iOS implementation side. The two lanes are intentionally separate per `AGENTS.md`.

## Purpose

The App Store worker handles everything between "we have a release-ready build" and "the app is live on the App Store." It does not write application code, run Xcode builds, or fix bugs. It prepares, validates, and executes the release pipeline — with human approval gates on irreversible actions.

## Scope

The App Store worker owns:

- metadata drafting and validation (app name, description, keywords, promotional text, what's new, category, age rating)
- screenshot management (organizing, naming, associating with device classes and locales)
- release notes drafting
- privacy policy and support URL readiness verification
- TestFlight build selection and internal test group coordination
- App Store Connect submission state tracking
- App Review response drafting
- submission prerequisite checklist enforcement
- requesting human approval before submit/release actions

The App Store worker does not own:

- writing or modifying application source code
- running Xcode builds or tests
- creating build artifacts or IPA files
- signing configuration
- icon or asset design (it validates that assets exist, it does not create them)
- product strategy or feature decisions

## Inputs

The App Store worker expects to receive:

- a release-ready build artifact (from the iOS worker lane)
- a populated metadata draft (created by the worker or validated against a template)
- a completed submission checklist (see `docs/products/<product-id>/submission-checklist.md`)
- a human-approved app name (if not yet finalized)
- screenshot assets organized by device class and locale
- a privacy policy URL and support URL

## Outputs

The App Store worker produces:

- updated release state in `state/checkpoints/platform/releases/`
- metadata draft artifacts in product docs
- submission checklist status updates
- approval requests for irreversible actions
- structured task results with next-action signals

## Workflow

A healthy App Store submission flow:

1. iOS worker completes implementation and validation.
2. iOS worker prepares a release-candidate build artifact.
3. App Store worker receives a submission or release task.
4. App Store worker validates the submission checklist:
   - metadata complete?
   - screenshots present for required device classes?
   - privacy policy URL accessible?
   - support URL accessible?
   - app icon present in build?
   - version string consistent?
5. If checklist passes, worker prepares TestFlight state.
6. Worker requests human approval before uploading to TestFlight.
7. After TestFlight testing, worker prepares App Store submission state.
8. Worker requests human approval before submitting for review.
9. Worker tracks review status and reports outcomes.
10. Worker requests human approval before releasing to the public.

## Approval Gates

Per `AGENTS.md` and `docs/approval-policy.md`, these actions require human approval:

- uploading a build to TestFlight (submit_testflight)
- submitting to App Store review (submit_appstore)
- releasing to the public store (release_to_store)

These actions are safe to automate:

- preparing TestFlight state (prepare_testflight)
- drafting metadata
- validating checklist completeness
- drafting release notes
- drafting review responses

## Checklist Enforcement

Before any submission action, the App Store worker should validate the product's submission checklist. If any required item is incomplete, the worker should report a structured failure rather than proceeding.

The checklist artifact lives at `docs/products/<product-id>/submission-checklist.md` and is also tracked in release state checkpoints.

## State Tracking

Release state lives in `state/checkpoints/platform/releases/`:

- `release_records/` — per-version release state
- `build_candidates/` — tracked builds
- `metadata_drafts/` — locale-specific metadata state
- `screenshot_sets/` — device-class screenshot tracking

## Relationship to iOS Worker

The handoff boundary is clear:

- iOS worker produces a build artifact and declares it release-ready
- App Store worker takes over from that point
- App Store worker never modifies application code
- iOS worker never interacts with App Store Connect

If a review rejection requires a code change, the App Store worker creates a new iOS task — it does not fix the code itself.

## Implementation Reference

The current App Store worker implementation lives at `apps/worker-appstore/main.py`. It integrates with:

- `packages/policies/approvals.py` for approval checks
- `packages/db/` for release and approval state persistence
- `packages/schemas/` for typed release and task contracts

## Related Docs

- `docs/ios-lane.md` — iOS implementation lane
- `docs/approval-policy.md` — approval boundaries
- `docs/products/catchbook/submission-checklist.md` — first product checklist
- `docs/products/catchbook/appstore-readiness-audit.md` — current readiness assessment
