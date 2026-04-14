---
title: "Partial Refactors That Leave the Old Gate in Front of New Auto-Detection"
category: integration-issues
date: 2026-04-13
tags:
  - catchbook
  - ios
  - swiftui
  - swiftdata
  - refactor
  - partial-refactor
  - auto-detection
  - defer-commit
  - task-cancellation
  - optional-relationship
module: Catchbook.Forms, Catchbook.Location, Catchbook.Trips
symptom: "On fresh install, user sees 'No waterbodies yet — add a waterbody first' instead of the auto-detected waterbody the new code was supposed to populate."
root_cause: "A prior PR added waterbody auto-detection inside NewSpotForm but kept the existing `waterbodies.isEmpty` empty-state gate in front of it. The auto-detection was unreachable because the form body was short-circuited before its `.task` could run. Same chicken-and-egg in TripStartSheet."
---

# Partial Refactors That Leave the Old Gate in Front of New Auto-Detection

## Problem

Users on a fresh install of Catchbook opened the Spots tab, tapped **Add Spot Here**, and saw "No waterbodies yet — add a waterbody first, then save this spot." They also saw "Add your first water — create a waterbody to start logging trips and catches." when tapping Start Trip from Home. Both flows had auto-detection logic that was supposed to populate the waterbody from the user's location on pin drop — but the auto-detection never ran, because the form body was short-circuited by `waterbodies.isEmpty` before the `.task(id:)` modifier had a chance to fire.

The root source was commit `194078d` (feat(catchbook): make spots map-first with crosshair pin placement and waterbody auto-detection), which added a 3-layer waterbody detector (`CLGeocoder.reverseGeocodeLocation` → `MKLocalSearch("lake"/"river"/"reservoir")` → manual fallback) to `NewSpotForm` but did not remove the pre-existing `if waterbodies.isEmpty { SectionEmptyState(...) }` branch. The new functionality lived inside the `else` clause of a gate that, on a fresh install, always took the `if`.

A pattern audit during the fix surfaced four additional hard dependencies on non-nil waterbody that the same commit left in place: `TripEditingLogic.canSave` still required `selectedWaterbodyID != nil`, `LogFeatureLogic.shouldOfferCreateSpot` required `trip.waterbody != nil`, the trip history map's `TripHistoryLogic.waterbodySummaries()` silently `compactMap`'d out nil-waterbody trips, and all three waterbody pickers used `"Select water"` as a placeholder that implied requirement.

## Root Cause

This is a partial-refactor failure mode with a specific, nameable shape: **the new capability is gated behind the old requirement it was supposed to eliminate**. The original flow had one rule — "waterbody must exist before you can save a spot" — enforced by `canSave` and the empty-state branch. The refactor added auto-detection to provide the waterbody automatically, but kept the `isEmpty` branch as a defensive fallback. The author reasoned that the branch would still apply when detection failed. What they missed: on a fresh install, the `waterbodies` `@Query` is always empty, so the form never reaches the `else` branch where the `.task(id:)` modifier is declared. The auto-detect could *never run* in the one scenario where it mattered most.

This is worse than the original bug. With the original rule, users knew what to do (tap "Add Waterbody"). With the partial refactor, users saw an "Add Waterbody" button after a promise of auto-detection — a broken feature is worse than no feature, because it hides the failure from the code review (the new file does work in unit tests) and from the author (they always test with a populated database).

The second-order failure was spec drift. The 2026-04-11 Catchbook location-model brainstorm established the principle **"Catchbook should do the work first"** — aggressively prefill likely values instead of asking the user to build every record from scratch. The partial refactor implemented half of this principle (detection) but left the other half (no-gate) as an implicit "we'll get to it." The brainstorm and the code drifted apart with no paper trail. The complete fix required an ADR ([docs/decisions/2026-04-13-waterbody-is-never-a-gate.md](../../decisions/2026-04-13-waterbody-is-never-a-gate.md)) because the full resolution — relaxing `TripEditingLogic.canSave` and `shouldOfferCreateSpot` and making waterbody a non-anchor tag — is a small but real extension of the brainstorm's stance, not a gap-closure.

## Solution

The fix shipped in two commits on `main` (9070102 main refactor, 658c787 drive-by test fixes) via branch `feat/catchbook-optional-waterbody`. Five patterns are worth lifting out.

### 1. Pure/impure service split

The prior inline helpers in `NewSpotForm.swift` both detected AND inserted a `Waterbody` row — which is what made cancelling the form leak a phantom record. Split into a pure detector and an impure persister so the caller controls the commit boundary:

```swift
// Sources/Services/WaterbodyAutoDetectionService.swift
enum WaterbodyAutoDetectionService {
    struct Detected: Equatable { let name: String; let type: WaterbodyType; let coordinate: CLLocationCoordinate2D }

    /// Pure. CLGeocoder → single combined MKLocalSearch. 6s TaskGroup timeout.
    /// Silent on failure. Does NOT touch SwiftData.
    static func detect(at coordinate: CLLocationCoordinate2D) async -> Detected?

    /// Impure. Case-insensitive name dedupe via internal FetchDescriptor.
    /// Does NOT call context.save() — caller commits inside its own
    /// PersistenceWriteCoordinator block.
    @MainActor
    static func findOrCreate(_ detected: Detected, in context: ModelContext) throws -> Waterbody
}
```

The contract that `findOrCreate` does NOT call `save()` is what makes defer-commit work. It matches the existing `PersonalBestService.refresh(with:in:)` convention in the same `Sources/Services/` directory.

### 2. Defer-commit in `NewSpotForm.save()`

Detection stores a `pendingDetected: Detected?` in view state. The actual `Waterbody` insert happens only inside the existing write-coordinator commit closure, so cancelling the form leaves zero phantom records:

```swift
// Sources/Features/Forms/NewSpotForm.swift
private func save() {
    PersistenceWriteCoordinator.perform(
        commit: {
            let resolvedWaterbody: Waterbody?
            if let userPicked = selectedWaterbody {
                resolvedWaterbody = userPicked
            } else if let pendingDetected {
                // Defer-commit: the auto-detected waterbody is only inserted
                // now, inside the save transaction. Cancelling the form
                // leaves no phantom records.
                resolvedWaterbody = try WaterbodyAutoDetectionService.findOrCreate(
                    pendingDetected, in: modelContext
                )
            } else {
                resolvedWaterbody = nil
            }
            let spot = Spot(title: draft.title, waterbody: resolvedWaterbody, ...)
            modelContext.insert(spot)
            try modelContext.save()
        },
        ...
    )
}
```

### 3. `.task { }` vs `Task { } in .onAppear`

`TripStartSheet` originally ran waterbody prefill in `Task { ... }` inside `.onAppear`. That task is **not cancelled on view dismiss** — it keeps running after the sheet is gone and can call `findOrCreate` / mutate `modelContext` on a torn-down view, which silently leaves orphan state and produces intermittent "detected waterbody from last screen" bugs.

```swift
// Wrong:
.onAppear {
    locationRecorder.requestIfNeeded()
    Task { await prefillWaterbodyFromLocation() }
}

// Right:
.onAppear {
    // Permission prompt stays here — it's a side-effect, not async work.
    locationRecorder.requestIfNeeded()
}
.task {
    // SwiftUI cancels this automatically on disappear.
    if let spot = context.preselectedSpot { ... ; return }
    if let waterbody = context.preselectedWaterbody { ... ; return }
    await prefillWaterbodyFromLocation()
}
```

Rule: any async work that touches `ModelContext` must be inside `.task { }`, never `Task { } in .onAppear`.

### 4. `@AppStorage` prefill cache for network gating

The prefill was hitting CLGeocoder + MKLocalSearch on every trip start. Cache the last successful detection in `@AppStorage` with a 500m / 24h freshness gate — kills ~80% of network calls for users who fish the same waters repeatedly, and matches the brainstorm's "do the work first" principle without burning API quota:

```swift
private struct TripStartDetectionCache: Codable {
    let name: String; let typeRawValue: String
    let latitude: Double; let longitude: Double
    let timestamp: Date

    static let freshnessWindow: TimeInterval = 60 * 60 * 24
    static let freshnessRadiusMeters: Double = 500

    func isFresh(for coordinate: CLLocationCoordinate2D) -> Bool {
        let age = Date().timeIntervalSince(timestamp)
        guard age >= 0, age < Self.freshnessWindow else { return false }
        let cached = CLLocation(latitude: latitude, longitude: longitude)
        let current = CLLocation(latitude: coordinate.latitude, longitude: coordinate.longitude)
        return cached.distance(from: current) <= Self.freshnessRadiusMeters
    }
}
```

### 5. Synthetic "General area" cluster to preserve nil rows on a grouped map

`TripHistoryLogic.waterbodySummaries()` grouped trips by `$0.waterbody?.id` and then `compactMap`ped out the `nil` group — which silently dropped every nil-waterbody trip from the Trips map. The fix keeps the same grouping but emits a synthetic summary for the nil bucket, keyed by a **deterministic** UUID so the sheet-selection state doesn't thrash across renders:

```swift
// Sources/Features/Trips/TripHistoryLogic.swift
private let generalAreaSyntheticID = UUID(uuidString: "00000000-0000-0000-0000-0000CA7C4600")!

private static func generalAreaSummary(
    nilWaterbodyTrips: [Trip],
    catches: [CatchRecord],
    tripIDs: Set<UUID>
) -> WaterbodySummary? {
    guard !nilWaterbodyTrips.isEmpty else { return nil }
    let coordinates = nilWaterbodyTrips.compactMap(\.resolvedCoordinate)
    guard !coordinates.isEmpty else { return nil }  // nothing to place on map

    let avgLatitude = coordinates.map(\.latitude).reduce(0, +) / Double(coordinates.count)
    let avgLongitude = coordinates.map(\.longitude).reduce(0, +) / Double(coordinates.count)

    return WaterbodySummary(
        waterbodyID: generalAreaSyntheticID,
        waterbodyName: "General area",
        waterbodyType: .lake,
        coordinate: CLLocationCoordinate2D(latitude: avgLatitude, longitude: avgLongitude),
        coordinateSource: .generalAreaCentroid,  // new enum case
        tripCount: nilWaterbodyTrips.count,
        ...
    )
}
```

The new `WaterbodySummaryCoordinateSource.generalAreaCentroid` case required updating the one `switch` that reads `detailText`; there are no other exhaustive switches on that enum, so the blast radius was minimal.

## Prevention

Three concrete rules. Each has an actionable check — not "write better tests."

### 1. Partial-refactor rule: "remove the old gate in the same PR"

When a PR adds a new capability that is supposed to supersede an existing requirement, the PR **must delete the old requirement in the same commit**. Otherwise the new capability is dead code behind the old gate, and the failure is invisible to tests that seed the database.

Concrete reviewer check: if a PR adds auto-detection, inference, or prefill for a field X, grep the diff and the surrounding file for:

```bash
# In the same file(s) as the new capability, search for dead gates:
rg 'X\.isEmpty|X\s*==\s*nil|\.disabled\(.*X' path/to/changed/file
```

Ask: "Which of these gates is now redundant?" If any remains, either delete it in the same PR or write a one-line comment explaining why it must stay (and link the follow-up issue that removes it). The chicken-and-egg shape looks like this:

```swift
// Bad: new .task is unreachable on fresh state
if waterbodies.isEmpty {
    EmptyStateView()  // <- fresh install always lands here
} else {
    Form { ... }
        .task { await autoDetectAndPopulate() }  // never runs on fresh install
}
```

### 2. SwiftUI task-in-onAppear anti-pattern

**Rule:** any async work that touches `ModelContext`, performs network I/O, or mutates `@State` **must live in `.task { }`, not `Task { } in .onAppear`**. `.task { }` is cancelled automatically by SwiftUI on view disappear. `Task { } in .onAppear` is not — it outlives dismissal and can write to a torn-down view's state or commit to `ModelContext` after the user already dismissed.

Reviewer grep:

```bash
rg -A2 '\.onAppear\s*\{[^}]*Task\s*\{' products/your-app/Sources
```

Any hit is suspicious. Move async work into a sibling `.task { }` and keep `.onAppear` for genuinely synchronous side effects like `locationRecorder.requestIfNeeded()` or `firstAppearance = true` flags.

This is also the fix for the class of bugs that look like "my modal persisted a phantom row even though I cancelled" — the row was written by the trailing `Task` after dismiss.

### 3. Audit checklist for optional-relationship refactors

When making a previously-required SwiftData `@Model` relationship optional, run this grep battery **before declaring the refactor done**:

```bash
# 1. compactMap that drops the nil group from a grouping — silent data loss
rg 'compactMap.*waterbody\?\.id|Dictionary\(grouping:.*waterbody\?\.id' Sources/

# 2. SortDescriptors that traverse optional relationships (unsupported in SwiftData)
rg 'SortDescriptor.*\.waterbody\?' Sources/

# 3. canSave / isValid / .disabled still referencing the old required field
rg 'canSave.*waterbodyID|selectedWaterbodyID\s*!=\s*nil|\.disabled.*waterbody' Sources/

# 4. UI copy implying required: picker placeholders, empty-state banners
rg 'Select water|No waterbodies yet|Add your first water|Add a waterbody first' Sources/

# 5. Tests asserting nil returns false from canSave — these will silently pass
#    and mask the intended fix
rg 'XCTAssertFalse.*canSave.*nil|canSave.*selectedWaterbodyID.*nil' Tests/
```

Each hit is either a required change or a deliberate exception with a code comment. `TripHistoryLogic.waterbodySummaries` was caught by grep #1, `TripEditingLogic.canSave` was caught by grep #3, and the "Select water" picker placeholder in three files was caught by grep #4 — all missed by the initial plan until the pattern audit ran the same checks.

Also worth adding to any future iOS CLAUDE.md:

> **Rule (Catchbook):** Waterbody is an optional tag at every entry point. Never add a `waterbody != nil` gate in any new flow. See [ADR 2026-04-13](../../decisions/2026-04-13-waterbody-is-never-a-gate.md).

## Related Documentation

### Prior Learnings

- [Rolling Out Catchbook's Layered Location Model](../integration-issues/catchbook-layered-location-model-rollout.md) — established the pattern of locking the product contract before coding. This learning reinforced the need for an ADR to capture the spec shift when the current fix extended the brainstorm's "canonical anchor" into "never-a-gate." Key insight carried forward: *"form changes are easiest to validate when logic is extracted first"* — which is exactly why the `WaterbodyAutoDetectionService` pure/impure split preceded the gate removal.
- [Rolling Out Catchbook's Angler UX Parity](../integration-issues/catchbook-angler-ux-parity-rollout.md) — warned that cross-cutting changes must be grouped by **shared primitive**, not by screen. Applied here by treating `NewSpotForm` and `TripStartSheet` as two call sites of one service, not two separate refactors — which is what prevented drift between their detection paths.
- [Rolling Out Catchbook's Competitive Gap Closure](../integration-issues/catchbook-competitive-gap-rollout.md) — flagged the known Xcode project target-membership gotcha. New `.swift` files must be added to the target's PBX build phase explicitly or they silently fail to link (no "Cannot find type" error until a real `xcodebuild` run). This gotcha was hit verbatim when creating `WaterbodyAutoDetectionService.swift` and was resolved by four manual edits to `project.pbxproj` (PBXBuildFile, PBXFileReference, PBXGroup children, PBXSourcesBuildPhase files).

### Planning Artifacts

- **Origin brainstorm:** [docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md](../../brainstorms/2026-04-11-catchbook-location-model-brainstorm.md) — established "Catchbook should do the work first" and "Waterbody should have one canonical coordinate." This fix extends the second rule by clarifying "canonical when attached, but never mandatory."
- **Full plan:** [docs/plans/2026-04-13-refactor-catchbook-optional-waterbody-plan.md](../../plans/2026-04-13-refactor-catchbook-optional-waterbody-plan.md) — the deepened plan with phases, research insights, and acceptance criteria.
- **ADR:** [docs/decisions/2026-04-13-waterbody-is-never-a-gate.md](../../decisions/2026-04-13-waterbody-is-never-a-gate.md) — records the spec shift so the next planner reading the brainstorm finds the amendment via a link-forward pointer at the top of the brainstorm.

### Commits

- **Partial refactor that introduced the bug:** `194078d` — *feat(catchbook): make spots map-first with crosshair pin placement and waterbody auto-detection* (added the detector, kept the gate).
- **Main fix:** `9070102` — *refactor(catchbook): make waterbody fully optional across all flows* (15 files, +1,290 / −291). Service extraction, defer-commit, `.task { }` cancellation, AppStorage cache, synthetic "General area" cluster, HIG-aligned picker convention, ADR, brainstorm link-forward.
- **Drive-by test fix:** `658c787` — *test(catchbook): fix pre-existing test failures from navigation restructure* (`AppTabTests` referenced `AppTab.log` removed in `d08cf6e`, `StartTripViewTests` referenced `StartTripView.lastTimeHereCard` also removed in that restructure). Unblocked the test run so the refactor could be verified.
