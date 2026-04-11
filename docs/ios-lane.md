# iOS Lane

This document defines the boundary between the iOS worker and the App Store worker.

## iOS Worker Scope

The iOS lane owns implementation and build preparation:

- iOS bugfixes
- iOS features
- Xcode builds
- simulator runs
- test execution
- build artifact preparation
- release-candidate handoff

Logic-bearing iOS changes under `products/catchbook-ios/Sources/` must ship with created or modified tests under `products/catchbook-ios/Tests/`, unless a machine-readable no-test exception is valid under shared policy.

This lane should feel like an Apple-specific engineering lane, not a release operations lane.

## App Store Worker Scope

The App Store lane owns shipping and distribution:

- TestFlight preparation
- metadata management
- screenshot handling
- localization handling
- release notes drafting
- App Store Connect workflows
- review response drafting
- submission state tracking

Final submission and public release actions remain approval-gated.

## Why The Split Matters

This separation prevents one worker from silently spanning both engineering and release authority.

That matters because:

- build problems and release problems are different classes of work
- approval boundaries are easier to enforce
- Apple tooling is easier to reason about when responsibilities are split

## Expected Handoff

A healthy Apple flow looks like this:

1. supervisor creates an iOS task or release task
2. iOS worker performs implementation and validation
3. iOS worker produces release-ready artifacts
4. App Store worker prepares TestFlight and metadata state
5. App Store worker pauses for approval before irreversible release actions

That handoff is one of the sacred boundaries in this repo.

## Shared Validation Contract

The iOS lane uses the same structured tests-with-code contract as the engineering lane.

That means:

- task packets carry testing requirements in structured fields
- validators persist `testing_policy` and specific failure codes
- missing tests remain a `VALIDATION_FAILED` result, not a silent review note
- project wiring must continue to treat `products/catchbook-ios/project.yml` as the canonical project-definition source when test files or targets change

## Related Docs

- `docs/appstore-lane.md` — dedicated App Store worker lane doc (operational scope, workflow, approval gates)
- `docs/approval-policy.md` — approval boundaries for both lanes
- `docs/products/catchbook/appstore-readiness-audit.md` — current readiness assessment
- `docs/products/catchbook/submission-checklist.md` — structured submission checklist
