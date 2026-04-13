---
title: "Rolling Out Catchbook's Competitive Gap Closure"
category: integration-issues
date: 2026-04-12
tags:
  - catchbook
  - ios
  - swiftdata
  - xcode
  - planning
  - migration
  - history
---

# Rolling Out Catchbook's Competitive Gap Closure

## Problem

Catchbook needed to close a large batch of competitive gaps in one pass:
released-vs-kept logging, richer condition capture, effort stats, flat
catch history and search, multi-photo catches, and direct camera capture.

The implementation itself was manageable, but the risky parts were not the
feature flags. The risk sat in planning clarity, migration safety, manual Xcode
project wiring, and local simulator verification.

## Root Cause

The main failure mode was not one bug. It was a set of cross-cutting rollout
concerns that are easy to miss when a feature bundle spans models, views,
export, migration, and tests at the same time:

- the plan originally left catch-search ownership underspecified
- multi-photo support needed a compatibility contract, not just a new model
- new source and test files were created on disk but not added to the Xcode
  project target
- simulator test verification was fragile enough that a bad destination name
  could look like feature instability

## Solution

We solved the rollout by tightening the plan first, then staging the
implementation so additive data work landed before migration-sensitive media
changes.

### 1. Make logic ownership explicit in the plan

The review finding about catch search was correct: flat catch filtering should
not live as ad hoc view code.

The fix was to choose a dedicated owner up front:

- `CatchHistoryLogic` owns flat catch filtering and search
- `TripHistoryLogic` continues to own trip-grouped history behavior
- the filter model stays intentionally small and shared in shape:
  waterbody, date window, season, lure, and query text

That kept trip history and flat catch history aligned without forcing both
surfaces into one oversized logic type.

### 2. Stage SwiftData media migration behind a compatibility accessor

Multi-photo support was the only part of the rollout that could easily regress
existing behavior.

The safe rollout sequence was:

1. add `CatchPhoto`
2. register it in the app model container and test model containers
3. introduce shared hero-photo reads on `CatchRecord`
4. migrate legacy single-photo catches into `CatchPhoto`
5. update quick catch, catch edit, share/export, and history rows to read the
   shared accessor instead of raw legacy fields

The important lesson is that a new persistence model is not enough. Existing
surfaces need one compatibility contract while the old and new storage formats
coexist.

### 3. Treat Xcode project membership as part of the feature

Two new files compiled conceptually but still failed in the real app build:

- `CatchPhotoMigrationService.swift`
- `CatchHistoryLogic.swift`

The reason was simple: they existed on disk, but they were not added to
`Catchbook.xcodeproj` source phases. The shared UI file then failed to see the
new draft type because the containing source file was not actually part of the
target.

The practical rule is:

- after adding new iOS source or test files, verify both filesystem presence
  and PBX project membership
- if a type “exists” but is mysteriously out of scope during app compilation,
  check `project.pbxproj` before assuming the Swift code is wrong

### 4. Break large SwiftUI view expressions before the compiler asks

After the new catch-history mode was wired into `TripsView`, the remaining
compile failure was a classic SwiftUI type-check blowup rather than a logic
bug.

The fix was to:

- extract toolbar predicates into small computed properties
- rewrite the flat catch `Section` into explicit header/footer form
- reduce one large conditional tree into smaller subexpressions

For view-heavy rollouts, compiler ergonomics are part of delivery quality.

### 5. Separate build verification from simulator verification

The final build succeeded, but focused `xcodebuild test` verification remained
environment-sensitive.

One run failed because the requested simulator name (`iPhone 16`) did not exist
in this Xcode install. A rerun against the known device ID
`57B89E43-0156-4EF3-A819-670E2BE2F37E` got farther and built the app and test
bundle correctly, but the local simulator still stalled after launch without
reporting XCTest results.

That means:

- compile/build success was real
- test-bundle construction was real
- final runtime XCTest completion remained unverified in this environment

The right move was to report that gap clearly instead of claiming a pass.

## What Worked Well

- Reviewing the plan before implementation caught the real rollout risks early.
- Keeping additive schema work separate from media migration kept the changes
  debuggable.
- Adding a dedicated `CatchHistoryLogic` gave the flat catch list a stable home.
- Updating export/backup during the same pass kept new fields from becoming
  local-only data.

## What We Learned

### Plan review should force ownership decisions

“Add catch search” is not a complete plan item. If the repo already has logic
layers, the plan should state where the new behavior lives and what the minimum
shared filter contract is.

### SwiftData migrations need read compatibility, not just write migration

If old UI surfaces still read legacy fields directly, additive migration is only
half done. The safer move is always to centralize reads behind one shared
accessor and migrate views to that abstraction first.

### Xcode project wiring is easy to forget during file-based editing

When working outside Xcode, new Swift files are easy to create and easy to
forget to register. For iOS work, project membership is part of “done.”

### Simulator destinations should be treated as configuration, not memory

Using a remembered simulator name is fragile. Prefer known device IDs or verify
available destinations before running targeted tests.

## Verification

Verified successfully:

- `xcodebuild -project /Users/simons/ai-company-os/products/catchbook-ios/Catchbook.xcodeproj -scheme Catchbook -destination 'generic/platform=iOS Simulator' build`

Partially verified:

- focused XCTest build and test-bundle install succeeded against simulator ID
  `57B89E43-0156-4EF3-A819-670E2BE2F37E`

Verification gap:

- local simulator execution stalled after launch and did not emit final XCTest
  results, so the runtime test pass could not be honestly confirmed in-session

## Prevention

- When adding history/search features, declare the logic owner in the plan.
- When adding SwiftData models, update app containers and test containers in the
  same change.
- When introducing new persistence alongside legacy data, add one shared read
  accessor before migrating every surface.
- After creating any new iOS source or test file, verify `project.pbxproj`
  membership before debugging Swift compiler errors.
- Prefer concrete simulator IDs for targeted `xcodebuild test` runs.

## Related Files

- [/Users/simons/ai-company-os/docs/plans/2026-04-12-feat-catchbook-competitive-gap-plan.md](/Users/simons/ai-company-os/docs/plans/2026-04-12-feat-catchbook-competitive-gap-plan.md)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Trips/CatchHistoryLogic.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Trips/CatchHistoryLogic.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Services/CatchPhotoMigrationService.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Services/CatchPhotoMigrationService.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Models/FishingModels.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Models/FishingModels.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogView.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Trips/TripsView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Trips/TripsView.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Catchbook.xcodeproj/project.pbxproj](/Users/simons/ai-company-os/products/catchbook-ios/Catchbook.xcodeproj/project.pbxproj)
