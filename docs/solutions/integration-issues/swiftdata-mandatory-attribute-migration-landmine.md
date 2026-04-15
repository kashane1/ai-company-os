---
title: "SwiftData @Model Non-Optional Properties Without Property-Level Defaults Brick the Store on Migration"
category: integration-issues
date: 2026-04-14
tags:
  - catchbook
  - ios
  - swiftdata
  - coredata
  - migration
  - lightweight-migration
  - model-container
  - nscocoaerrordomain
  - 134110
  - persistence
  - data-model-evolution
module: Catchbook.Models.FishingModels
symptom: "On a device upgraded from an earlier schema, the app launches but every write silently no-ops — the user can tap 'Add Spot', see the form, dismiss it, and find nothing saved. New installs and the simulator work normally."
root_cause: "Non-optional stored properties on @Model classes were declared without property-level defaults (`var gear: String` instead of `var gear: String = \"\"`). Init defaults only apply to NEW objects; SwiftData lightweight migration needs a property-level default to backfill legacy rows. Without one, migration fails with NSCocoaErrorDomain 134110 'missing attribute values on mandatory destination attribute', the entire ModelContainer fails to load, and the app falls back to a degraded state where writes succeed in-memory but never persist."
---

## Problem

A user reported that on their iPhone, creating a new spot in Catchbook "worked" in the UI — the form appeared, they filled it out, tapped save, and the sheet dismissed — but nothing actually persisted. The spot never appeared on the map or in the list. Trip starts, catch logs, and every other write had the same silent failure.

Reinstalling the app (wiping the store) made everything work again. The iOS Simulator also worked fine — which was the confusing part. The bug was device-only, reproduced only on stores that had been created by an earlier schema version.

The device console log showed the true failure at app launch:

```
CoreData: error: addPersistentStoreWithType:configuration:URL:options:error: returned error NSCocoaErrorDomain (134110)
CoreData: error: reason : Cannot migrate store in-place: Validation error missing attribute values on mandatory destination attribute
CoreData: error: NSUnderlyingError : UserInfo={entity=ConditionSnapshot, attribute=moonPhaseRawValue, reason=Validation error missing attribute values on mandatory destination attribute}
Store failed to load.
Unresolved error loading container
```

This is the same class of failure that commit `af263a1` had already fixed for `CatchRecord.gear` two days prior. We thought it was a one-off. It wasn't.

## Root Cause

When you declare a SwiftData `@Model` class like this:

```swift
@Model
final class ConditionSnapshot {
    var moonPhaseRawValue: String  // ← non-optional, no default

    init(moonPhase: MoonPhase? = nil, capturedAt: Date = .now) {
        self.moonPhaseRawValue = (moonPhase ?? moonPhaseValue(for: capturedAt)).rawValue
    }
}
```

the `@Model` macro synthesizes Core Data attribute metadata for `moonPhaseRawValue` with **no default value**. The init default is a Swift-level construct — it only runs when you create a new object via `ConditionSnapshot(...)`. It is **invisible to Core Data's lightweight migration engine**.

When a device with an older store (one that predates `moonPhaseRawValue`) launches the upgraded app, Core Data walks existing `ConditionSnapshot` rows and tries to set the new mandatory attribute. It has no value to write and no default to fall back on, so it aborts with error 134110 — "missing attribute values on mandatory destination attribute." The entire persistent store fails to load, and the `ModelContainer` is unusable.

SwiftData on iOS 17+ doesn't crash when this happens — it degrades gracefully into an ephemeral, in-memory-only state so the UI still renders. That's what made the bug so confusing: the app runs, the UI appears normal, forms dismiss as if they saved. Writes silently vanish because there's no backing store to write to.

The simulator never hit this because it had a freshly-created store with the current schema — no migration needed. The bug was invisible in dev and only reproducible on user devices that had been through at least one prior schema version.

### Why the init default isn't enough

This is the crucial distinction and it's non-obvious. Consider:

```swift
// ❌ BROKEN — migration can't backfill
var gear: String

init(gear: String = "") {
    self.gear = gear   // only runs for new objects
}
```

```swift
// ✅ SAFE — migration uses the property default
var gear: String = ""

init(gear: String = "") {
    self.gear = gear
}
```

The two look semantically equivalent for object construction, and they ARE for new objects. But only the second form writes a default into the Core Data attribute metadata that lightweight migration consults when backfilling legacy rows.

### Why we hit this twice

Commit `af263a1` (Apr 14) fixed exactly this class of bug for `CatchRecord.gear`. The commit message even called out the mechanism precisely. But the fix only patched the one attribute that had been flagged in that session's error log. Every other non-optional stored property in `FishingModels.swift` — 21 of them across 7 classes — was still a dormant landmine. The next device that upgraded past a schema addition tripped the next landmine (`ConditionSnapshot.moonPhaseRawValue`), and we would have kept playing whack-a-mole indefinitely.

## Solution

Fix: property-level defaults on every non-optional stored property of every `@Model` class. Commit `1f4e280` hardened 21 properties across 7 classes in one sweep; full diff in `products/catchbook-ios/Sources/Models/FishingModels.swift`.

### 1. String defaults

Empty string is almost always the right sentinel. New objects still get their real value via the initializer.

```swift
@Model
final class Spot {
    var title: String = ""
    var notes: String = ""
    // ...
}
```

### 2. Enum rawValue defaults

Use a fully-qualified enum case and its `rawValue`. Pick the most neutral case — the goal is to produce a valid-but-obviously-fallback value for legacy rows that never had one.

```swift
var waterClarityRawValue: String = WaterClarity.notRecorded.rawValue
var moonPhaseRawValue:    String = MoonPhase.newMoon.rawValue
var tideStateRawValue:    String = TideState.notRecorded.rawValue
var captureStatusRawValue: String = ConditionCaptureStatus.fallback.rawValue
var sourceRawValue:       String = ConditionSource.tripFallback.rawValue
var outcomeRawValue:      String = TripOutcome.active.rawValue
var typeRawValue:         String = WaterbodyType.lake.rawValue
```

### 3. Date defaults — use `Date.distantPast`, fully qualified

Two non-obvious rules:

**Use `Date.distantPast` as the sentinel**, not `Date.now`. Rescued legacy rows will have an obviously-fake timestamp (year 0001), so you can distinguish them from real data in queries or backfills.

**The `@Model` macro requires the type to be fully qualified in the default expression.** `.distantPast` alone fails with:

```
error: type 'Any?' has no member 'distantPast'
A default value requires a fully qualified domain named value
```

because the macro synthesizes `SwiftData.Schema.PropertyMetadata(... defaultValue: .distantPast ...)` where `defaultValue` is typed as `Any?` and Swift can't infer `Date` from a leading-dot literal.

```swift
// ❌ won't compile inside @Model
var createdAt: Date = .distantPast

// ✅ correct
var createdAt: Date = Date.distantPast
```

### 4. Bool and Int defaults

Standard primitive fallbacks. Match the init default where one exists:

```swift
var isPrivate: Bool = true
var sortOrder: Int = 0
```

### 5. What to skip

- **Optionals** (`var latitude: Double?`) — no default needed; Core Data treats absence as nil.
- **UUID `@Attribute(.unique)` identifiers** — these have existed since the first schema version in practice, so migration never needs to backfill them. If you add a new unique identifier to an existing model, you need a custom migration anyway (a default would collide on the unique index).
- **Relationships** — SwiftData backfills array relationships as empty and object relationships as nil.

## Prevention

### 1. Property-level default rule for every new @Model attribute

**Every non-optional stored property on a `@Model` class MUST have a property-level default.** No exceptions, no "the init already defaults it" reasoning — that's precisely the trap.

Include this rule in the iOS code review checklist:

> Any new stored property added to an `@Model` class must either be Optional or have a property-level default. Init-time defaults are insufficient and will brick the store for any user upgrading through this schema version.

### 2. Grep pre-commit check

A one-line grep catches the common forms. Add to CI or a pre-commit hook:

```bash
# Find non-optional stored properties on @Model classes that lack a property-level default.
# Run from repo root.
grep -nE '^\s*var\s+[a-zA-Z_][a-zA-Z0-9_]*:\s*(String|Bool|Int|Date|Double)\s*$' \
  products/catchbook-ios/Sources/Models/*.swift
```

Any match is a potential landmine. A clean run should return nothing — every stored primitive should end in either `?` (optional) or `= <default>` (property default). Exceptions need an explicit justifying comment.

### 3. New-property PR checklist

When a PR adds a stored property to an existing `@Model` class, the reviewer must verify:

- [ ] Property is Optional, OR has a property-level default
- [ ] Default is a fully-qualified literal (`Date.distantPast`, `MyEnum.case.rawValue`, `""`, `false`, `0`) — not `.distantPast` or other inferred-type forms
- [ ] PR has been tested by installing over the previous release build, not just on a fresh simulator
- [ ] Tests still pass: `xcodebuild test -project Catchbook.xcodeproj -scheme Catchbook -destination 'platform=iOS Simulator,name=iPhone 17,OS=26.4'`

### 4. Device-install-over-previous test before TestFlight

Simulator testing alone is insufficient to catch this class of bug. Before cutting a TestFlight build, install the previous-released build on a physical device, exercise enough flows to populate `ConditionSnapshot`, `Trip`, and `CatchRecord` rows, then install the new build over it without wiping. If the app's first-launch logs show anything under the `CoreData:` subsystem at error level, treat it as a release blocker.

### 5. Long term: versioned schema + explicit migration plan

Property-level defaults are a safety net for trivial "add a column" changes. They don't handle:

- Renaming properties or entities
- Changing a property's type
- Splitting or merging entities
- Enforcing data transformation during migration

Before the App Store release, stand up a `VersionedSchema` + `SchemaMigrationPlan` so non-trivial evolutions have a real migration path. Treat every future schema edit as "must ship with either a property-level default (trivial) or a migration stage (non-trivial)."

## Related Documentation

- Commit `af263a1` — First instance of this bug, fixed for `CatchRecord.gear` only. The fix was correct but under-scoped; the full audit didn't happen until the second recurrence.
- Commit `1f4e280` — Full audit and hardening pass: 21 properties across 7 @Model classes in `FishingModels.swift` (`Waterbody`, `Spot`, `ConditionSnapshot`, `Trip`, `CatchRecord`, `CatchPhoto`, `PersonalBest`, `SavedLure`).
- [Partial Refactors That Leave the Old Gate in Front of New Auto-Detection](./incomplete-refactor-auto-detection-behind-empty-state-gate.md) — Same shape of lesson (first fix under-scoped, the issue recurs until you audit every instance of the pattern), applied to SwiftUI gating rather than SwiftData migration.
- [Rolling Out Catchbook's Competitive Gap Closure](./catchbook-competitive-gap-rollout.md) — Earlier SwiftData schema evolution work (`CatchPhoto` addition) that didn't hit this because `CatchPhoto` is a new entity rather than a new attribute on an existing one.
- Apple Developer Forums: NSCocoaErrorDomain 134110 ("missing attribute values on mandatory destination attribute") — canonical Core Data lightweight migration failure mode; the underlying mechanism SwiftData inherits.

## Verification

- Full test suite: 307 tests, 0 failures on iPhone 17 / iOS 26.4 simulator after the fix (commit `1f4e280`).
- Build check: the macro-expansion error (`Type 'Any?' has no member 'distantPast'`) surfaced the fully-qualified-type requirement during the first test run and was fixed before committing.
- Device verification: pending — user to reinstall the updated build over their existing store and confirm saves now persist. A successful migration will show no `CoreData:` error-level logs at first launch.
- Known gap: this fix only hardens `FishingModels.swift`. If additional `@Model` classes are added to other files later, the grep prevention check (§2) needs to be generalized to scan `Sources/**/*.swift`.
