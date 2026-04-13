---
title: "Rolling Out Catchbook's Angler UX Parity"
category: integration-issues
date: 2026-04-13
tags:
  - catchbook
  - ios
  - swiftui
  - maps
  - logging
  - parity
  - planning
---

# Rolling Out Catchbook's Angler UX Parity

## Problem

Catchbook needed to close the most visible fishing-log parity gaps without
turning the app into a bloated feature dump. The target was a phased rollout
that made daily logging feel faster, smarter, and more complete than before.

The hard part was not one isolated bug. The challenge was shipping several
related UX improvements across models, quick-catch flows, trip editing, maps,
photos, and browsing surfaces while keeping the implementation coherent.

## Root Cause

The risk in this rollout came from cross-cutting product work:

- parity features touched multiple entry points, not one screen
- several wins depended on shared primitives like suggestions, map preferences,
  and photo metadata
- some features looked small in product terms but still required model and test
  updates
- iOS simulator verification remained less reliable than plain build
  verification

Without a phased plan, the work would have drifted into overlapping one-off
changes and inconsistent behavior between quick catch and full catch editing.

## Solution

We solved the rollout by treating it as one parity track with shared building
blocks, then shipping it in phases instead of as unrelated tickets.

### 1. Ship the obvious daily-use wins first

Phase 1 focused on the most visible friction:

- history-backed species and lure suggestions
- duplicate catch from trip detail
- EXIF GPS photo spot matching
- persistent map style toggle

That gave Catchbook immediate "this app does the work for me" improvements
without opening broader product scope.

### 2. Reuse the same primitives for browse parity

Phase 2 built on the same foundations instead of inventing new systems:

- catch markers on trip and spot maps
- calendar browsing for fishing days
- photo gallery / trophy wall

The important pattern was to reuse honest location confidence and shared trip
history logic rather than bolt on parallel browse-only data paths.

### 3. Add power-user flexibility without making the default flow heavier

Phase 3 handled parity features that can easily make logging feel cluttered if
they are forced on everyone:

- persistent field visibility preferences
- tally mode for high-volume trips
- lightweight `gear` tracking with history suggestions

The key implementation rule was to keep preferences shared between quick catch
and catch editing so users do not see one logging surface respect settings
while another ignores them.

### 4. Treat map, photo, and suggestion behavior as shared contracts

Several features only stayed simple because they were implemented as reusable
contracts:

- one map-style preference applied across all map surfaces
- one suggestion/ranking path powered repeated-value fields
- one EXIF metadata service owned photo coordinate extraction
- one duplicate-catch flow created a prefilled draft instead of silently
  cloning data

That prevented the parity work from becoming a pile of screen-specific
exceptions.

### 5. Be explicit about what was verified versus what was only partially verified

The build and test-bundle compilation were real and repeatable:

- `xcodegen generate` succeeded
- `xcodebuild build -scheme Catchbook -project Catchbook.xcodeproj -destination 'platform=iOS Simulator,name=iPhone 17,OS=26.4'` succeeded
- focused XCTest targets compiled and linked successfully

The remaining gap was simulator execution. Multiple targeted `xcodebuild test`
runs stalled after handoff to the simulator, so the honest result was partial
verification rather than a claimed green test run.

## What Worked Well

- Reviewing and refining the plan before coding removed the biggest product
  ambiguities early.
- Shipping in phases kept each parity slice understandable.
- Reusing shared logic prevented quick catch and catch edit from drifting apart.
- Adding tests alongside each logic-bearing phase kept the work aligned with
  the repo's lane-matching test contract.

## What We Learned

### Parity work should be grouped by shared primitive, not by screen

Map improvements, photo intelligence, and repeated-value suggestions become
much easier to ship when the plan names the shared abstraction first.

### "Easy win" features still need product defaults locked early

Duplicate catch was only implementation-ready once the timestamp behavior was
 explicitly chosen: open a prefilled editor and default the new catch time to
 `now`.

### Configurability should simplify the product, not fragment it

Persistent field visibility worked because it reduced noise while staying
consistent across the main logging surfaces.

### Build success and simulator success are different signals

For iOS work, a clean simulator build and linked test bundle are meaningful,
but they are not the same as completed XCTest execution. The gap should be
reported clearly.

## Verification

Verified successfully:

- `xcodegen generate`
- `xcodebuild build -scheme Catchbook -project Catchbook.xcodeproj -destination 'platform=iOS Simulator,name=iPhone 17,OS=26.4'`

Partially verified:

- focused XCTest targets for the new parity logic compiled and linked

Verification gap:

- simulator test execution stalled after launch handoff, so final runtime test
  completion could not be honestly confirmed in-session

## Prevention

- For parity tracks, define the rollout in phases before implementation starts.
- Lock user-facing defaults during plan review so "easy wins" do not carry open
  product questions into coding.
- Prefer one shared preference or service over separate per-screen behavior.
- Add lane-matching tests as each phase lands instead of saving test work for
  the end.
- Treat simulator runtime verification as a separate risk from project build
  verification.

## Related Files

- [/Users/simons/ai-company-os/docs/plans/2026-04-12-feat-catchbook-angler-ux-parity-plan.md](/Users/simons/ai-company-os/docs/plans/2026-04-12-feat-catchbook-angler-ux-parity-plan.md)
- [/Users/simons/ai-company-os/docs/products/catchbook/anglers-log-deep-comparison-2026-04-12.md](/Users/simons/ai-company-os/docs/products/catchbook/anglers-log-deep-comparison-2026-04-12.md)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogView.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Trips/TripsView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Trips/TripsView.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogFeatureLogic.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogFeatureLogic.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Shared/UI/CatchbookMapView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Shared/UI/CatchbookMapView.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Shared/UI/CatchLoggingPreferences.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Shared/UI/CatchLoggingPreferences.swift)
