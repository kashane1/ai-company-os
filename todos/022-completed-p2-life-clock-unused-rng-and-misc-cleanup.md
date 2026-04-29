---
status: completed
priority: p2
issue_id: "022"
tags: [code-review, life-clock, ios, simplicity, dead-code]
dependencies: []
---

# Problem Statement

Multiple unused or duplicated abstractions accumulated during the skeleton pass. None block correctness, but together they add ~80–120 LOC of YAGNI surface that the next contributor must read past.

## Findings

1. **`EngineClock.random` is unused.** The `random: () -> Double` field, the SplitMix64 PRNG inside `EngineClock.swift`, and the `seed:` parameter on `.fixed(_:seed:)` are never read by `ClockEngine` or `QuestEngine`. (`Sources/Engines/EngineClock.swift:7,40-50`.)

2. **`SplitMix64` is duplicated** across `EngineClock.swift` (private) and `MockHealthKitService.swift` (as `SmallRNG`, with an apologetic comment). If kept, promote one implementation to `Sources/Engines/SeededRNG.swift` and have both consume it.

3. **`HealthPermissionState` model is unused.** Declared in `LifeClockSchemaV1` and the `permissions` dict on the store, never read or written by any feature. (`Sources/Models/LifeClockSchema.swift`, `Sources/App/LifeClockStore.swift:19`.)

4. **`ConfidenceModel.computeCompleteness` and `weightKgIfTracked()`** are never called. `MockHealthKitService` hardcodes `sourceCompleteness = 0.8`. (`Sources/Engines/ConfidenceModel.swift:25-43`.)

5. **`LifeClockConfiguration` mis-render bug:** `ProfileView` does `Text("Life Clock v\(LifeClockConfiguration.appName) 0.1.0")` which renders `"Life Clock vLife Clock 0.1.0"`. Either drop `appName` from the interpolation or rename the constant. (`Sources/Features/Profile/ProfileView.swift:44`.)

6. **Unused `@Bindable var bindable = store` in ProfileView** — declared, never read. (`Sources/Features/Profile/ProfileView.swift:7`.)

7. **`MainTabView` reads `@Environment(LifeClockStore.self)` but never uses it** — only `@State var selection` is consumed. (`Sources/App/LifeClockApp.swift:29`.)

8. **`todayDriversToday` typo** — should be `todayDrivers`. Also duplicates `ledger` at bootstrap (same array, just sorted differently). Pick one. (`Sources/App/LifeClockStore.swift:13`.)

## Proposed Solutions

### Option 1: One cleanup pass (recommended)

Make all eight changes in a single follow-up commit on the same branch. Each is mechanical and low-risk.

Pros:
- One review, one diff. ~120 LOC removed.
- Clears the simplicity reviewer's punch list.

Cons:
- None significant.

Effort: small
Risk: low

### Option 2: Defer to a v1.1 cleanup PR after merge

Land this PR as-is, file a single tracking ticket.

Pros:
- Keeps current PR scope tight.

Cons:
- The "vLife Clock 0.1.0" string is visible in the Profile screen — looks broken.
- The unused fields will get cargo-culted when v2 lands.

Effort: trivial (just create the ticket)
Risk: low

## Recommended Action

(Filled during triage.)

## Technical Details

- Delete: `EngineClock.random`, `seed:` parameter, private `SplitMix64`.
- Consolidate: `SmallRNG` in `MockHealthKitService` to use the consolidated `SeededRNG`, OR keep both and accept the duplication with a TODO.
- Delete: `HealthPermissionState` model + `permissions` dict on store.
- Delete: `ConfidenceModel.computeCompleteness`, `weightKgIfTracked`.
- Fix: `ProfileView` version string → `"Version 0.1.0"`.
- Delete: unused `@Bindable` and unused `@Environment` in `MainTabView`.
- Rename: `todayDriversToday` → `todayDrivers`. Consider deriving `ledger` from drivers + completed quests rather than duplicating.

## Acceptance Criteria

- [ ] Build still succeeds.
- [ ] All existing tests pass.
- [ ] `ProfileView` shows `"Version 0.1.0"` (or equivalent), not `"vLife Clock 0.1.0"`.
- [ ] Diff in this todo removes net LOC, not adds.

## Work Log

- 2026-04-27: Created from PR #14 simplicity + architecture reviews.

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/14
