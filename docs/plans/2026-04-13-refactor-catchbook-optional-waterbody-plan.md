---
title: Make Waterbody Fully Optional Across Catchbook
type: refactor
status: completed
date: 2026-04-13
origin: docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md
---

# Make Waterbody Fully Optional Across Catchbook

## Enhancement Summary

**Deepened on:** 2026-04-13
**Sections enhanced:** Design shape, Architecture, Phase 1, State Lifecycle Risks, Acceptance Criteria, Performance, Documentation Plan
**Research agents used:** best-practices-researcher (SwiftUI/HIG), framework-docs-researcher (SwiftData in-memory tests), code-simplicity-reviewer, pattern-recognition-specialist, learnings-researcher, architecture-strategist, performance-oracle

### Key Improvements

1. **Defer-commit pattern for NewSpotForm.** Auto-detection now returns a pure `Detected` value; the actual `Waterbody` insert is deferred to inside `save()`'s `PersistenceWriteCoordinator` block. Dismissing the form without saving no longer leaks a phantom waterbody. (Architecture + SwiftUI reviewers)
2. **`.task { }` not `Task { } in .onAppear` in TripStartSheet.** Prevents the cancellation bug where a dismissed sheet's detection task still fires `findOrCreate` and writes to the model context. (SwiftUI reviewer)
3. **`findOrCreate` signature simplified** — drops `existing: [Waterbody]`, uses an internal `FetchDescriptor` with a case-insensitive name predicate. Matches the `PersonalBestService.refresh(with:in:)` convention already used in `Sources/Services/`. (Architecture reviewer)
4. **Picker convention switched to "None" with a `Divider`** — HIG-aligned, matches Reminders/Notes/Health/Calendar. Unobtrusive "Detected from location" caption appears when the value came from auto-detect. (SwiftUI/HIG reviewer)
5. **MKLocalSearch collapsed from 3 sequential requests to 1 combined query**, with a 6-second timeout on the whole `detect(at:)` call and a debounce on pin-drag detection. (Performance reviewer)
6. **TripStartSheet prefill gated** on a cached last-detection (coordinate + result + timestamp via `@AppStorage`) to avoid hitting the network on every trip start. (Performance reviewer)
7. **`TripHistoryLogic.waterbodySummaries()` added to scope.** The pattern audit caught that nil-waterbody trips are silently dropped from the Trips map cluster view — a real blocker the original plan missed.
8. **SwiftData pre-flight added to Phase 1** — grep for `SortDescriptor` traversing `waterbody` (unsupported, crashes silently), confirm inverse relationships, verify Xcode project target membership for the new service file.
9. **Brainstorm amendment / ADR required before Phase 3.** Relaxing `TripEditingLogic.canSave` and `shouldOfferCreateSpot` is a spec shift from the brainstorm's "Waterbody is the canonical anchor" — needs a paper trail in `docs/decisions/` so the next planner can find it from the brainstorm. (Architecture reviewer)
10. **Alternatives Considered and Future Considerations trimmed.** Simplicity reviewer flagged them as plan-padding for a scoped refactor. Cut.

### New Considerations Discovered

- **Phantom waterbody risk has a real fix**, not just "accept as harmless." The split pure/impure service shape makes defer-commit free.
- **Trips map invisibility bug.** Without the `waterbodySummaries` fix, users with nil-waterbody trips would see them everywhere in the app except the one place where they'd expect to see them — the Trips map.
- **CLGeocoder rate limits are real** (~1 req/sec sustained). Without debouncing, a user dragging a spot pin could silently burn through the quota and get `CLError.network` on subsequent legitimate detects.
- **Xcode project target membership** is a known Catchbook gotcha from prior rollouts — new `.swift` files must be explicitly added to the Xcode project target or they fail to link.

## Overview

A user can install Catchbook, tap "Add Spot Here" on the map, and save a spot without ever seeing, picking, or creating a waterbody. The same holds for starting a trip, editing a trip, and every other logging flow. Waterbody becomes a purely complementary tag — auto-attached when the app can confidently infer it, editable when the user wants it, but never a precondition for anything.

This closes a gap left by the partial refactor in commit `194078d` (feat(catchbook): make spots map-first with crosshair pin placement and waterbody auto-detection), which added 3-layer auto-detection inside `NewSpotForm` but kept the old "no waterbodies → can't proceed" empty-state gate in front of it. The result is a chicken-and-egg: the auto-detect can't run until the user manually creates a waterbody first, which is exactly what the refactor was supposed to eliminate.

## Problem Statement

On a freshly installed app, the user sees:

1. **Spots tab → Add Spot Here** → `NewSpotForm` shows a full-screen "No waterbodies yet — add a waterbody first, then save this spot" empty state. The auto-detection logic inside the form is unreachable because the form body is short-circuited by `waterbodies.isEmpty`. (`Sources/Features/Forms/NewSpotForm.swift:46-62`)
2. **Start Trip** → `TripStartSheet` shows "Add your first water — create a waterbody to start logging trips and catches." (`Sources/Features/Home/TripStartSheet.swift:54-70`)
3. Even once a waterbody exists, the **Start Trip** button is hard-disabled until a waterbody is picked from the dropdown, with a "Select a waterbody to get started" helper (`Sources/Features/Home/TripStartSheet.swift:162, 166-171`).
4. The trip editor has the same hard requirement at the logic level (`Sources/Features/Trips/TripEditingLogic.swift:54`: `selectedWaterbodyID != nil && ...`), and `TripsView` wires it into the editor's `canSave` (`Sources/Features/Trips/TripsView.swift:1605`).
5. `SpotFormLogic.canSave` still requires `selectedWaterbodyID != nil` (`Sources/Features/Forms/FormLogic.swift:19-21`), so even if the empty-state gate is removed, Save stays greyed out.
6. The "create a spot from this trip" post-trip suggestion in `LogFeatureLogic.shouldOfferCreateSpot` only fires when `trip.waterbody != nil` (`Sources/Features/Log/LogFeatureLogic.swift:276-278`), so trips with nil waterbody silently lose that follow-up.
7. Waterbody auto-detection lives only inside `NewSpotForm`. `TripStartSheet` has no equivalent, so there is no path by which a trip flow can infer a waterbody from the user's current location.

The models already permit this change — `Spot.waterbody` and `Trip.waterbody` are both declared as `Waterbody?` in `Sources/Models/FishingModels.swift:206, 452`. The entire problem is at the form/logic/UI layer.

## Proposed Solution

Relax every hard requirement on waterbody at the form and logic layer, extract the auto-detection into a reusable service, and treat waterbody as a prefill-and-attach convenience everywhere.

Guiding rules (carried forward from `docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md`):

- **Catchbook should do the work first.** Reduce logging friction with smart defaults and inference. Waterbody should auto-populate when confident and stay silent when not. (see brainstorm: "Catchbook should do the work first.")
- **Confidence shapes UI, not provenance.** Don't say "inferred waterbody" — just show the detected name quietly and make it easy to clear or change. (see brainstorm: "Confidence should shape the UI more than provenance should.")
- **Waterbody is a tag, not a gate.** This plan extends the brainstorm's intent by making waterbody strictly optional at every entry point. The brainstorm kept waterbody as the canonical place anchor; this refactor says the anchor is still welcome but never mandatory — a trip or spot with no waterbody is a valid first-class record.
- **Plain-language location cues.** Keep "At"/"Near" semantics; they already work with nil waterbody. (see brainstorm: "Use 'At' when the app has a precise user-selected or recorded location.")

### Design shape

- **New file:** `Sources/Services/WaterbodyAutoDetectionService.swift` — a stateless `enum` matching the `ConditionCaptureService` / `PersonalBestService` convention. Split into a **pure** detection step and an **impure** persistence step so callers can defer the SwiftData write until their own save path fires:
  - `detect(at coordinate: CLLocationCoordinate2D) async -> Detected?` — pure. Runs CLGeocoder reverse geocode, then a single combined MKLocalSearch (`"lake river reservoir"`) as fallback, wrapped in a 6-second timeout. Returns a `Detected { name, type, coordinate }` value type with no SwiftData side effects. Silent on failure.
  - `findOrCreate(_ detected: Detected, in context: ModelContext) throws -> Waterbody` — impure. Runs a `FetchDescriptor<Waterbody>` with a case-insensitive name predicate against the context, returns the match or inserts a new one. Does **not** call `context.save()` — caller commits. Signature matches `PersonalBestService.refresh(with:in:)`.
  - `inferType(from name: String) -> WaterbodyType` — pure helper, lifted from the existing private enum in `NewSpotForm.swift`. Exposed for tests.
- **NewSpotForm**: delete the `waterbodies.isEmpty` branch entirely. Always render the form. On appear with a coordinate, kick off `WaterbodyAutoDetectionService.detect(at:)` via `.task(id:)` (already the current pattern; keep it), store the result in `@State var pendingDetected: Detected?`, and reflect it in the picker UI as a selected value. Do NOT commit the waterbody yet. On `save()`, inside the existing `PersistenceWriteCoordinator.perform` block, call `findOrCreate(pendingDetected, in: modelContext)` and attach the returned waterbody to the new `Spot` in the same transaction. Dismissing the form without saving leaves zero phantom records.
- **TripStartSheet**: delete the `waterbodies.isEmpty` empty-state branch. Remove the `.disabled(selectedWaterbody == nil)` on Start Trip and the "Select a waterbody to get started" helper. Add a `.task { }` (NOT `Task { } in .onAppear` — the latter is not cancelled on dismiss and will fire `findOrCreate` on a gone view) that, when no spot/waterbody is preselected, runs `prefillWaterbodyFromLocation()`. Gate the prefill on a cached `@AppStorage` last-detection entry (coordinate + result + timestamp): skip the network call if the user's current location is within 500m of the last cached hit and the cache is < 24 h old. Trip start is itself a commit boundary, so this path calls `findOrCreate` immediately when detection succeeds — the trip will persist within seconds either way.
- **Picker UI convention (HIG-aligned):** the "no value" option is `Text("None")` at the **top** of the list, followed by a `Divider()`, followed by the real waterbodies. Matches Reminders "No List", Notes folder picker, Health sources. This applies to all three picker call-sites: `NewSpotForm.swift:70`, `TripStartSheet.swift:74`, `TripsView.swift:1629`. (Supersedes the original "No waterbody" rename proposal.)
- **Auto-detect caption (quiet, not loud):** when the picker value came from auto-detection rather than user selection, render a `.font(.caption2).foregroundStyle(.secondary)` one-liner under the picker: `"Detected from your location"`. Clear on user interaction. This satisfies HIG's "make every default value easy to change" without drifting into the provenance-labelling anti-pattern the brainstorm warned against ("inferred (75%)" is bad; a quiet "detected" caption is fine).
- **FormLogic & TripEditingLogic**: drop `selectedWaterbodyID != nil` from both `canSave` functions. `canSave` reduces to title-non-empty (spot form) and date-ordering (trip editor).
- **LogFeatureLogic.shouldOfferCreateSpot**: remove the `trip.waterbody != nil` clause — offer the "create spot from this trip" suggestion whenever the trip has a resolvable coordinate and no spot, whether or not it has a waterbody.
- **TripHistoryLogic.waterbodySummaries()** (new to this plan, caught by pattern audit): nil-waterbody trips must not be silently dropped from the Trips map cluster view. Add a synthetic "General area" bucket (or cluster by resolved coordinate) so trips without a waterbody still appear on the Trips map. See Phase 3 for the exact change.
- **UI copy sweep**: rename "Select water" → "None" across all three picker placeholders. Footer text in both sheets updates to explain the value without implying requirement.
- **Tests**: update `FormLogicTests.testSpotFormLogicRequiresTrimmedTitleAndSelectedWaterbody` to match the relaxed contract. Add `WaterbodyAutoDetectionServiceTests` using the project's `ModelTestSupport.makeStore()` pattern for `inferType` (pure) and `findOrCreate` (existing-match + new-insert branches). The MapKit-dependent `detect(at:)` layer stays out of unit tests; covered by on-device manual QA.

### What stays the same

- `Waterbody` model, `NewWaterbodyForm`, and explicit waterbody creation are untouched — users who want to tag a specific water can still do so.
- Filter-state uses of `selectedWaterbodyID != nil` in `TripHistoryLogic.hasActiveFilters` and `CatchHistoryLogic.hasActiveFilters` stay as-is: those are "is a waterbody filter active?" booleans, not save gates.
- Map empty-state copy like "No waters with saved coordinates yet." in `TripsView.swift:566` stays — that's a legitimate empty state, not a blocker.
- Suggestion ranking that prefers spot → waterbody → global still works when waterbody is nil (the `waterbodyValues` array just goes empty).
- All navigation, routing, preselection plumbing (`TripStartContext.preselectedWaterbody`, `NewSpotForm.preselectedWaterbodyID`, `AppRouter.requestTripStart(spot:waterbody:)`) is kept — it's still useful when the caller does have a waterbody to pass through.

## Technical Approach

### Architecture

The auto-detection logic moves from a private helper inside `NewSpotForm.swift` into a proper service with this shape:

```swift
// Sources/Services/WaterbodyAutoDetectionService.swift

import CoreLocation
import MapKit
import SwiftData

enum WaterbodyAutoDetectionService {
    struct Detected: Equatable {
        let name: String
        let type: WaterbodyType
        let coordinate: CLLocationCoordinate2D
    }

    /// Pure. Runs CLGeocoder.reverseGeocodeLocation (inlandWater/ocean), then
    /// falls back to a single combined MKLocalSearch("lake river reservoir").
    /// Wrapped in a 6-second timeout. Silent on failure — returns nil.
    /// Does NOT touch SwiftData.
    static func detect(at coordinate: CLLocationCoordinate2D) async -> Detected?

    /// Impure. Finds an existing Waterbody by case-insensitive name match via
    /// FetchDescriptor, or inserts a new one. Does NOT call context.save() —
    /// the caller is responsible for committing inside its own write coordinator.
    /// Matches PersonalBestService.refresh(with:in:) convention.
    @MainActor
    static func findOrCreate(
        _ detected: Detected,
        in context: ModelContext
    ) throws -> Waterbody

    /// Pure helper, exposed for tests.
    static func inferType(from name: String) -> WaterbodyType
}
```

**Usage pattern differs by caller** (architecture reviewer's defer-commit policy):

- **`NewSpotForm`** calls `detect(at:)` during a `.task(id:)`, stores the result in `@State var pendingDetected: Detected?`, and reflects it in the picker. The actual `findOrCreate` call happens **inside the existing `PersistenceWriteCoordinator.perform` block in `save()`**, alongside the `Spot` insert. This gives the form true all-or-nothing semantics — cancel leaves no trace.
- **`TripStartSheet`** calls `detect(at:)` inside a `.task { }` (NOT `Task { } in .onAppear`) and calls `findOrCreate` + `modelContext.save()` immediately when detection returns, because trip start is itself a commit boundary that fires within seconds.

The asymmetry is intentional and documented inline. `findOrCreate`'s internal dedupe via `FetchDescriptor` case-insensitive name predicate handles the unlikely case of a two-form race.

### Concurrency / cancellation contract

- `.task { }` (SwiftUI) cancels automatically on view disappear. This is the only safe way to run the prefill: `Task { } in .onAppear` leaks and can mutate `modelContext` after the view is gone.
- Inside `detect(at:)`, the 6-second timeout uses a `TaskGroup` race between the real detection and `Task.sleep`. Late results past the timeout are discarded.
- `findOrCreate` is `@MainActor` because `ModelContext` mutations from SwiftUI must be main-actor-bound. The caller's `.task { }` is already main-actor by default when called from a view, so no `MainActor.run` wrapper is needed.

### Performance considerations (performance reviewer)

- **Sequential → combined MKLocalSearch.** The original plan ran three sequential `MKLocalSearch` requests with `naturalLanguageQuery = "lake"`, then `"river"`, then `"reservoir"`. That's 3 round-trips worst-case. Replace with a single request using `"lake river reservoir"` and filter/rank results client-side. Cuts worst-case latency from ~1.4–5.1 s to ~0.5–1.8 s and reduces rate-limit pressure.
- **CLGeocoder rate limit.** Apple throttles CLGeocoder to ~1 req/sec sustained. Back-to-back detects (e.g. user dragging a pin in `NewSpotForm`) silently return `CLError.network`. Debounce pin-drag detection with a 500ms `Task.sleep` + `Task.isCancelled` check; cancel prior task on each new pin drop.
- **TripStartSheet prefill cache.** Store the last successful detection in `@AppStorage` as `{ latitude, longitude, waterbodyName, waterbodyType, timestamp }`. Before running `detect(at:)`, check if the current location is within 500m of the cached coordinate AND the cache is < 24h old. If so, use the cached result. This kills ~80% of trip-start network calls for regular users.
- **Waterbody row growth.** Negligible. 500 rows over time is trivial for SQLite. Skip cleanup. The dedupe mechanism is `findOrCreate`'s case-insensitive name match; that's sufficient.

### Call-site changes

#### `Sources/Features/Forms/NewSpotForm.swift`

- **Delete** the `if waterbodies.isEmpty { ... }` branch (lines 46-62) and its `else`. Always render the form body.
- **Rename** the picker placeholder on line 70 from `"Select water"` to `"No waterbody"`.
- **Keep** the auto-detect `.task(id:)` (lines 158-161), but it now calls `WaterbodyAutoDetectionService.detect(at:)` instead of the in-file helper.
- **Delete** the private `detectWaterbody()` method (lines 250-293), `applyDetectedWaterbody()` (lines 295-330), and the `WaterbodyAutoDetection` private enum (lines 335-349). They move into the service.
- **Update** the footer text on line 131 to reflect the optional-water reality: `"Private by default. Drop a pin and we'll guess the waterbody from Apple Maps. You can skip or change it any time."`

#### `Sources/Features/Forms/FormLogic.swift`

```diff
 enum SpotFormLogic {
-    static func canSave(title: String, selectedWaterbodyID: UUID?) -> Bool {
-        !TripEditingLogic.normalizedText(title).isEmpty && selectedWaterbodyID != nil
+    static func canSave(title: String) -> Bool {
+        !TripEditingLogic.normalizedText(title).isEmpty
     }
 }
```

Every caller (only `NewSpotForm` currently) updates to drop the ID argument.

#### `Sources/Features/Home/TripStartSheet.swift`

- **Delete** the `if waterbodies.isEmpty { ... }` empty-state block (lines 54-70).
- **Unwrap** the `else { ... }` so the "Where" section always renders.
- **Rename** the picker placeholder on line 74 from `"Select water"` to `"No waterbody"`.
- **Remove** `.disabled(selectedWaterbody == nil)` on the Start Trip button (line 162). Replace with `.disabled(false)` or just drop the modifier.
- **Delete** the helper text block at lines 166-171 (`"Select a waterbody to get started."`).
- **Add** waterbody auto-detection to `.onAppear` (lines 189-198):

```swift
.onAppear {
    locationRecorder.requestIfNeeded()
    if let spot = context.preselectedSpot {
        selectedSpotID = spot.id
        selectedWaterbodyID = spot.waterbody?.id
    } else if let waterbody = context.preselectedWaterbody {
        selectedWaterbodyID = waterbody.id
    } else {
        Task { await prefillWaterbodyFromLocation() }
    }
}
```

And a new private method:

```swift
private func prefillWaterbodyFromLocation() async {
    guard selectedWaterbodyID == nil,
          let coordinate = locationRecorder.lastLocation?.coordinate,
          let detected = await WaterbodyAutoDetectionService.detect(at: coordinate) else { return }

    await MainActor.run {
        let waterbody = WaterbodyAutoDetectionService.findOrCreate(
            detected,
            in: modelContext,
            existing: waterbodies
        )
        // Silent persist — non-critical, user can clear.
        try? modelContext.save()
        selectedWaterbodyID = waterbody.id
    }
}
```

- **Update** the "Where" section footer / section header copy if it implies waterbody is required. Currently the header is just `"Where"` — fine.

#### `Sources/Features/Trips/TripEditingLogic.swift`

```diff
 static func canSave(
-    selectedWaterbodyID: UUID?,
     isTripActive: Bool,
     startAt: Date,
     endAt: Date
 ) -> Bool {
-    selectedWaterbodyID != nil && (isTripActive || endAt >= startAt)
+    isTripActive || endAt >= startAt
 }
```

Caller: `TripsView.swift:1605` drops the `selectedWaterbodyID:` argument.

#### `Sources/Features/Log/LogFeatureLogic.swift`

```diff
 static func shouldOfferCreateSpot(from trip: Trip) -> Bool {
-    trip.spot == nil && trip.waterbody != nil && trip.resolvedCoordinate != nil
+    trip.spot == nil && trip.resolvedCoordinate != nil
 }
```

Trips with no waterbody now get the "create spot from this trip" prompt as long as they have a real coordinate, matching the product promise that waterbody is optional end-to-end.

#### `Sources/Features/Trips/TripsView.swift`

- **Line 1629** picker placeholder: `"Select water"` → `"No waterbody"`.
- **Line 1605** `TripEditingLogic.canSave(...)` call: drop the `selectedWaterbodyID:` argument.

#### UI copy sweep (non-blocking, but should match the new contract)

- `NewWaterbodyForm.swift` — no copy change; it's the explicit "I want to create one" path and stays a first-class flow.
- `TripStartSheet` section header stays `"Where"`. Footer on line 121 still reads well.
- Any Home-screen prompts that say "add a waterbody to start" — audit during implementation (unlikely; already searched).

### Implementation Phases

#### Phase 1: Extract auto-detection service (foundation)

**Goal:** Move auto-detection out of `NewSpotForm` with a pure/impure split and a 6-second timeout. No user-visible behavior change yet (except faster failure mode).

**SwiftData pre-flight checks (run BEFORE writing any code):**
- `rg "SortDescriptor.*waterbody" products/catchbook-ios/Sources` — must return nothing. SwiftData sort descriptors cannot traverse optional relationships, and any such descriptor is already broken. If found, fix or route around before proceeding.
- Confirm `Waterbody` has an `@Relationship(inverse: \Spot.waterbody)` declaration in `Sources/Models/FishingModels.swift`. Missing inverse → silently orphaned collections when optionality changes.
- If the project uses CloudKit for SwiftData (`.cloudKitDatabase(...)` in the container config), confirm all relationships are already optional or have defaults — CloudKit requires it, and this refactor is strictly safer for CK sync.

**Implementation:**
- Create `Sources/Services/WaterbodyAutoDetectionService.swift` with the split shape from Technical Approach. `detect(at:)` is pure and returns `Detected?`. `findOrCreate(_:in:)` is `@MainActor`, takes only a `ModelContext`, uses an internal `FetchDescriptor<Waterbody>` with a `#Predicate` on lowercased name.
- Collapse the sequential lake/river/reservoir `MKLocalSearch` into one combined `naturalLanguageQuery = "lake river reservoir"` call.
- Wrap `detect(at:)` in a 6-second timeout via `TaskGroup` race with `Task.sleep(for: .seconds(6))`.
- **Add the new file to the `Catchbook` Xcode project target membership immediately.** Known gotcha from `docs/solutions/integration-issues/catchbook-competitive-gap-rollout.md`: new `.swift` files on disk but not in the Xcode target fail to link without a clear error.
- Update `NewSpotForm` to call the service. Because of the defer-commit pattern, `NewSpotForm` stops calling `findOrCreate` during detection — it only stores the `Detected` struct in `@State var pendingDetected: Detected?`. No behavior change yet because Phase 2 will wire this into `save()`.
- Delete the private `detectWaterbody()`, `applyDetectedWaterbody()`, and `WaterbodyAutoDetection` helpers in `NewSpotForm.swift` (lines 250–349).
- Add `Tests/Services/WaterbodyAutoDetectionServiceTests.swift` using `ModelTestSupport.makeStore()` (pattern from `Tests/Services/PersonalBestServiceTests.swift:5-28`). Cover:
  - `inferType(from:)` — river/creek/stream → `.river`, pond → `.pond`, ocean/sea/gulf/bay → `.coastal`, fallback → `.lake`.
  - `findOrCreate` returns existing match by case-insensitive name and does not insert a duplicate (`fetchCount == 1`).
  - `findOrCreate` inserts a new `Waterbody` when no match exists and returns it.
- MapKit-dependent layers (`detect(at:)`'s CLGeocoder + MKLocalSearch calls) are NOT unit-tested — covered by on-device QA in Phase 4.

**Success criteria:**
- All three pre-flight checks pass.
- `Sources/Services/WaterbodyAutoDetectionService.swift` exists, is in Xcode target membership, and compiles.
- `NewSpotForm` still shows auto-detected waterbodies in the picker on pin drop (verified on device). Save still requires a user to tap Save; cancelling the form leaves no phantom waterbody in `SpotsView`'s picker the next time.
- New test file passes. No dead code left in `NewSpotForm`.

#### Phase 2: Unblock spot creation and trip start

**Goal:** A user on a fresh install can create a spot and start a trip with zero waterbody interaction.

**`NewSpotForm` changes:**
- Delete the `if waterbodies.isEmpty { ... }` branch at `NewSpotForm.swift:46-62`.
- Rename the picker placeholder at `:70` to `Text("None").tag(Optional<UUID>.none)` and add a `Divider()` before the `ForEach(waterbodies)`.
- Add `@State private var pendingDetected: Detected?` and `@State private var waterbodyWasAutoDetected = false`.
- Update the `.task(id:)` at `:158-161` to call `WaterbodyAutoDetectionService.detect(at:)`, store the result in `pendingDetected`, and set `selectedWaterbodyID` optimistically by running an in-memory case-insensitive match against `waterbodies` (the `@Query` already available). If no existing match, leave `selectedWaterbodyID` nil but keep `pendingDetected` — the commit will happen in `save()`.
- Under the picker, conditionally render `Text("Detected from your location").font(.caption2).foregroundStyle(.secondary)` when `waterbodyWasAutoDetected == true`. Clear the flag on `.onChange(of: selectedWaterbodyID)`.
- Inside `save()`, inside the existing `PersistenceWriteCoordinator.perform` `commit:` closure, add:
  ```swift
  let resolvedWaterbody: Waterbody?
  if let userPicked = selectedWaterbody {
      resolvedWaterbody = userPicked
  } else if let pendingDetected {
      resolvedWaterbody = try WaterbodyAutoDetectionService.findOrCreate(pendingDetected, in: modelContext)
  } else {
      resolvedWaterbody = nil
  }
  // then use resolvedWaterbody instead of selectedWaterbody for the Spot(waterbody:) init
  ```
- Update footer copy at `:131` to `"Private by default. Drop a pin and we'll guess the waterbody from Apple Maps. You can skip or change it any time."`

**`FormLogic.SpotFormLogic.canSave` change:**
- Drop the `selectedWaterbodyID` parameter. Reduces to `!TripEditingLogic.normalizedText(title).isEmpty`.

**`TripStartSheet` changes:**
- Delete the `if waterbodies.isEmpty { ... }` branch at `:54-70`.
- Remove `.disabled(selectedWaterbody == nil)` at `:162`.
- Delete the helper text block at `:166-171`.
- Rename picker placeholder at `:74` to `Text("None").tag(Optional<UUID>.none)` + `Divider()`.
- Replace the `.onAppear { ... }` block at `:189-198` with a `.task { }`:
  ```swift
  .task {
      if let spot = context.preselectedSpot {
          selectedSpotID = spot.id
          selectedWaterbodyID = spot.waterbody?.id
          return
      }
      if let waterbody = context.preselectedWaterbody {
          selectedWaterbodyID = waterbody.id
          return
      }
      await prefillWaterbodyFromLocation()
  }
  .onAppear {
      locationRecorder.requestIfNeeded() // permission prompt — keep in onAppear
  }
  ```
- Add `@MainActor private func prefillWaterbodyFromLocation() async` that:
  1. Reads `@AppStorage` last-detection cache.
  2. If cached result is within 500m of `locationRecorder.lastLocation?.coordinate` AND < 24h old, try to match it against the current `waterbodies` list and set `selectedWaterbodyID` without hitting the network.
  3. Otherwise, call `WaterbodyAutoDetectionService.detect(at:)`, on success write the cache and call `findOrCreate` + `modelContext.save()` inside a `PersistenceWriteCoordinator.perform` block. Set `selectedWaterbodyID` to the returned waterbody's ID.
  4. On `Task.isCancelled` at any await boundary, return early without touching the context.

**Test update:**
- Rename `FormLogicTests.testSpotFormLogicRequiresTrimmedTitleAndSelectedWaterbody` → `testSpotFormLogicRequiresOnlyTrimmedTitle`:
  ```swift
  XCTAssertFalse(SpotFormLogic.canSave(title: "   "))
  XCTAssertTrue(SpotFormLogic.canSave(title: " Dock "))
  ```

**Success criteria:**
- Fresh simulator install: Spots tab → Add Spot Here → name "Test Spot" → Save works, creates a Spot with nil waterbody (or an auto-detected one if the simulator location is over a lake).
- Fresh simulator install: Home → Start Trip → fill species → Start Trip works. Trip persists with whatever auto-detect returned (possibly nil).
- Dismissing `NewSpotForm` without saving leaves zero new `Waterbody` rows (verify by opening the picker in a second attempt).
- Dismissing `TripStartSheet` mid-detection does not produce a spurious "Where is my context?" console warning (proof that `.task { }` cancellation worked).
- Spot detail view shows "Unknown" for water when nil — already handled by `SpotsView.swift:325`.

#### Phase 3: Trip editor, post-trip suggestion, map visibility, and copy cleanup

**Goal:** Close the remaining waterbody requirements in secondary flows. **This phase contains the spec shift from the brainstorm** — do the ADR step first.

**ADR / brainstorm amendment (do FIRST, before code changes):**
- Write a short ADR at `docs/decisions/2026-04-13-waterbody-is-never-a-gate.md` (create `docs/decisions/` if needed) that records:
  - The rule: "Waterbody is an optional tag at every entry point. Its canonical-anchor role from the location model brainstorm remains, but it is never a precondition for creating spots, starting or editing trips, or offering post-trip follow-ups."
  - The rationale: users on fresh installs should never hit a waterbody wall.
  - The scope: this overrides the brainstorm's implicit assumption that waterbody is the canonical anchor for every record. Canonical-anchor semantics still apply **when** a waterbody is attached, just not as a requirement.
- Add a "see ADR" pointer at the top of `docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md` so the next planner finds the amendment from the origin document.

**Code changes:**
- `TripEditingLogic.canSave` at `TripEditingLogic.swift:48-55`: drop the `selectedWaterbodyID` parameter. Update the one caller in `TripsView.swift:1605`.
- `TripsView.swift:1629` picker placeholder: "Select water" → "None" with a `Divider`, matching Phase 2.
- `LogFeatureLogic.shouldOfferCreateSpot` at `LogFeatureLogic.swift:276-278`: drop the `trip.waterbody != nil` clause.
- **Trips map fix (caught by pattern audit — new to this plan).** `TripHistoryLogic.waterbodySummaries()` at `TripHistoryLogic.swift:102-106` currently `compactMap`s out nil-waterbody groups. Nil-waterbody trips disappear from the Trips map cluster view. Fix by:
  - Grouping trips by `waterbody?.id` (including the `nil` key).
  - For the `nil` group, synthesize a `WaterbodySummary` with `name = "General area"` (or cluster by average coordinate when trips have resolved coordinates) and a synthetic `id = UUID()` so the annotation renders without a real waterbody backing it.
  - Update `WaterbodyMapAnnotation` / any downstream consumer to handle the synthetic ID path (short-circuit any `waterbody.lookup(by: id)` calls).
  - If the synthetic cluster is noisy, only emit it when `trips.count(where: { $0.waterbody == nil }) > 0`.
- **Trip row visual consistency.** `TripsView.swift:701` currently shows the waterbody label only when `trip.waterbody?.name` is non-nil. Add a fallback: if waterbody is nil but `trip.spot?.title` is non-nil, show the spot title; otherwise show a muted `"General area"`. One-line change.
- **Suggestion ranker comment.** In `ActiveTripView.swift:49-51`'s `catchesForWaterbody`, add a comment: `// Returns [] when trip.waterbody is nil; the suggestion ranker falls through to spot-level and global tiers.` Prevents a future reviewer from treating the empty-on-nil path as a bug.
- Final grep: `rg "Select water|No waterbodies|Add your first water|Add a waterbody first" products/catchbook-ios/Sources` — must return empty.

**Success criteria:**
- ADR file exists and is linked from the brainstorm.
- Editing an existing trip and clearing its waterbody saves successfully.
- Ending a trip that has a resolved coordinate but no waterbody shows the "Create Spot from This Trip" button.
- Trips map shows a "General area" cluster for nil-waterbody trips (or inline alongside real-waterbody clusters).
- No UI copy still implies "waterbody required".

#### Phase 4: Verification and manual QA

**Goal:** Confirm the five-scenarios below all work end-to-end.

- `swift test` on the `catchbook-ios` package (or Xcode test runner) — all tests green.
- Fresh simulator run through each golden-path scenario in the acceptance criteria.
- Visual check: every screen that previously said "Select water" now says "No waterbody" (or equivalent).

**Success criteria:** Acceptance criteria pass; no regressions in Spots, Trips, or Catch logging.

## Alternative Approaches Considered

Rejected briefly: auto-creating a placeholder waterbody per record (inflates the picker with garbage), seeding a default "My water" on first launch (same problem, delayed), and inlining the detection helpers as duplicated code rather than a service (appealing for simplicity but drifts between `NewSpotForm` and `TripStartSheet` over time, and the pure/impure split is what makes the defer-commit fix trivial). The service extraction + defer-commit is the shape that resolves the phantom-state risk cleanly.

## System-Wide Impact

### Interaction Graph

`NewSpotForm.save()` → inserts `Spot` (with optional `waterbody`) → `modelContext.save()` → `onSaved(spot)` closure → upstream (map pin → `SpotsView` `pinToAddSpotAt` state or `ActiveTripView` post-trip suggestion handler) refreshes `@Query`-backed spot list. **No change** because `Spot.waterbody` is already optional at the model layer.

`TripStartSheet.startTrip()` → inserts `Trip` (with optional `waterbody`, optional `spot`) → `ConditionCaptureService.snapshot(waterbody:spot:location:)` already takes optional waterbody — already graceful. → `modelContext.save()` → dismiss → `HomeView` / `CatchbookApp` observes new active trip via `@Query`. **No change** beyond dropping the UI gate.

`LogFeatureLogic.quickCatchContextSummary` already uses `trip.spot?.title ?? trip.waterbody?.name ?? "General area"` — nil-safe. Suggestion plumbing in `ActiveTripView` (`catchesForWaterbody` → empty array when nil waterbody) degrades gracefully.

### Error & Failure Propagation

- Auto-detect failure (no placemark, no MKLocalSearch result) → service returns nil → form stays on "No waterbody" with no error message. This is the correct UX: silence when uncertain.
- `WaterbodyAutoDetectionService.findOrCreate` insertion failure → caller falls back to `selectedWaterbodyID = nil` and user saves without a waterbody. Existing `NewSpotForm` already swallows this non-critical failure (line 325-328); the service keeps that posture.
- `modelContext.save()` failure after auto-creating a waterbody during trip start → already handled by `PersistenceWriteCoordinator`'s rollback path; the trip persists with whatever state was committed.

### State Lifecycle Risks

- **Risk:** If `WaterbodyAutoDetectionService.findOrCreate` inserts a waterbody but the subsequent `modelContext.save()` fails, a detached `Waterbody` could linger in the context until rollback. **Mitigation:** existing `PersistenceWriteCoordinator.perform(..., rollback: { modelContext.rollback() })` already covers this. In `NewSpotForm` the `findOrCreate` call happens **inside** the same `perform` block as the `Spot` insert, so a save failure rolls back both in one transaction.
- **Risk (resolved by defer-commit pattern):** Previously, dismissing `NewSpotForm` without saving would leak a phantom `Waterbody` that `applyDetectedWaterbody` had already committed. **Resolution:** the pure/impure service split means `detect(at:)` never touches SwiftData; the `findOrCreate` call is deferred into `save()`'s write coordinator. Cancelling the form now leaves zero trace. This is the right outcome; "accept the leak as harmless" has been discarded.
- **Risk:** Two concurrent `TripStartSheet` instances could race and both insert the same auto-detected waterbody. **Mitigation:** the app enforces one active trip and the sheet is modal, so the race is nearly impossible. If it does happen, `findOrCreate`'s case-insensitive name `FetchDescriptor` dedupes — the second caller finds the first's insert and returns it. Add a comment on the predicate noting this is the dedupe mechanism and must stay case-insensitive.
- **Risk:** `Task { } in .onAppear` would outlive view dismissal and mutate `modelContext` on a gone view. **Mitigation:** `TripStartSheet` uses `.task { }`, which SwiftUI cancels automatically on disappear. `NewSpotForm`'s existing `.task(id:)` already has this property.
- **Risk:** Filter state in `TripHistoryLogic` / `CatchHistoryLogic` filters by `selectedWaterbodyID` — trips with nil waterbody are excluded when a filter is active. That's correct current behavior. **No change.**

### API Surface Parity

Three user entry points to location tagging:
1. `NewSpotForm` — Phase 1–2.
2. `TripStartSheet` — Phase 2.
3. `TripsView` trip editor (`whereSection` in `TripsView.swift` ~line 1628) — Phase 3.

All three share the same picker pattern (`Picker("Waterbody", selection: $selectedWaterbodyID)`). All three need the placeholder-text rename and, where applicable, the `canSave` relaxation. The implementation plan touches each explicitly to avoid surface drift.

### Integration Test Scenarios

Unit tests with mocks miss these — verify on simulator:

1. **Fresh install → Add Spot Here on the map** → no auto-detect possible (simulator location in the ocean near Cupertino by default) → save with empty waterbody → spot shows in list with "Unknown" water label.
2. **Fresh install → Add Spot Here over a real lake** (change simulator location to Lake Tahoe) → CLGeocoder returns `"Lake Tahoe"` as `inlandWater` → waterbody auto-created → spot saved with it attached. User never touched the waterbody picker.
3. **Fresh install → Home → Start Trip** with simulator location over Lake Tahoe → `prefillWaterbodyFromLocation` runs → waterbody auto-created and selected → species field is focused → Start Trip → trip persists with auto-detected waterbody.
4. **Edit trip → clear waterbody → save** → trip persists, `shouldOfferCreateSpot` still fires on end-trip if a coordinate is set.
5. **End trip without waterbody (trip had only a spot with nil waterbody)** → "Create Spot from This Trip" prompt still appears because `shouldOfferCreateSpot` no longer requires waterbody.

## Acceptance Criteria

### Functional Requirements

- [x] `Sources/Services/WaterbodyAutoDetectionService.swift` exists with a pure `detect(at:) async -> Detected?`, an impure `@MainActor findOrCreate(_:in:) throws -> Waterbody`, and `inferType(from:) -> WaterbodyType`. File is added to the Catchbook Xcode target.
- [x] `detect(at:)` is wrapped in a 6-second timeout; late results are discarded.
- [x] `detect(at:)` uses a single combined `MKLocalSearch(naturalLanguageQuery: "lake river reservoir")` as fallback, not three sequential requests.
- [x] `findOrCreate` uses an internal `FetchDescriptor<Waterbody>` with a case-insensitive name `#Predicate`; the `existing: [Waterbody]` parameter does not appear in the signature.
- [x] `findOrCreate` does **not** call `context.save()`; callers commit inside their own `PersistenceWriteCoordinator.perform` block.
- [x] `NewSpotForm` renders the full form on fresh install with zero waterbodies. The empty-state gate, inline `detectWaterbody`, `applyDetectedWaterbody`, and `WaterbodyAutoDetection` private enum are all deleted.
- [x] Dismissing `NewSpotForm` without saving leaves zero new `Waterbody` rows in the store.
- [x] `SpotFormLogic.canSave(title:)` takes only `title` and returns `true` for any non-empty trimmed title. The `FormLogicTests` assertion is rewritten accordingly.
- [x] `TripStartSheet` renders the full form on fresh install with zero waterbodies. The Start Trip button's `.disabled(selectedWaterbody == nil)` is removed along with the helper text.
- [x] `TripStartSheet` uses `.task { }` (not `Task { } in .onAppear`) for waterbody prefill, and reads/writes an `@AppStorage` last-detection cache keyed on coordinate + timestamp with a 500m / 24h freshness gate.
- [x] Pin drops in `NewSpotForm` are debounced by 500ms before triggering `detect(at:)`; rapid re-drops cancel the prior task.
- [x] `TripEditingLogic.canSave` no longer accepts `selectedWaterbodyID`. The one call site in `TripsView.swift:1605` is updated.
- [x] A trip can be saved and edited with `waterbody == nil`.
- [x] `LogFeatureLogic.shouldOfferCreateSpot` returns true for trips that have a resolved coordinate and no spot, regardless of waterbody.
- [x] `TripHistoryLogic.waterbodySummaries()` emits a "General area" (or equivalent synthetic) summary that contains nil-waterbody trips; they appear on the Trips map cluster view.
- [x] `TripsView.swift:701`'s trip row renders a fallback label (spot title or "General area") for nil-waterbody trips instead of nothing.
- [x] Every waterbody picker uses `Text("None").tag(Optional<UUID>.none)` as the first option followed by a `Divider()` — in `NewSpotForm`, `TripStartSheet`, and `TripsView`'s trip editor.
- [x] An unobtrusive `.caption2` "Detected from your location" row renders under the picker when the value came from auto-detect; it clears on user interaction.
- [x] `rg "Select water|No waterbodies yet|Add your first water|Add a waterbody first|Select a waterbody to get started" products/catchbook-ios/Sources` returns empty.
- [x] ADR at `docs/decisions/2026-04-13-waterbody-is-never-a-gate.md` exists and is linked from the brainstorm.

### Non-Functional Requirements

- [x] No SwiftData schema migration is required. (`Spot.waterbody` and `Trip.waterbody` are already `Waterbody?`.)
- [x] Existing users with saved waterbodies see no regression: their picker still shows their waters and selection still works.
- [x] Auto-detection stays silent on failure — no error banners, no alerts. The form remains fully usable.
- [x] Offline behavior: when CLGeocoder / MKLocalSearch fail due to no network, the form still opens, still saves, still dismisses.

### Quality Gates

- [x] `FormLogicTests.testSpotFormLogicRequiresTrimmedTitleAndSelectedWaterbody` is renamed to `testSpotFormLogicRequiresOnlyTrimmedTitle` and rewritten to match the relaxed contract.
- [x] New `WaterbodyAutoDetectionServiceTests` uses `ModelTestSupport.makeStore()` and covers:
  - `inferType(from:)` — river/creek/stream → `.river`, pond → `.pond`, ocean/sea/gulf/bay → `.coastal`, fallback → `.lake`.
  - `findOrCreate` existing-match branch — returns the stored waterbody by case-insensitive name; `fetchCount == 1` after the call.
  - `findOrCreate` new-insert branch — inserts a `Waterbody` and returns it; `fetchCount == 1`.
- [x] SwiftData pre-flight: `rg "SortDescriptor.*waterbody" products/catchbook-ios/Sources` returns empty (or any hit is fixed/justified).
- [x] All existing tests in `Tests/Features/Forms`, `Tests/Features/Log`, `Tests/Features/Trips`, `Tests/Features/Spots`, and `Tests/Models` still pass without modification to their waterbody setup.
- [x] Fresh-install manual QA checklist (scenarios 1–5 above) passes on iOS 17 simulator.

## Success Metrics

- **Primary:** On a freshly installed app, the user can create a Spot and start a Trip in zero taps on any waterbody picker or "Add Waterbody" button.
- **Secondary:** When the user is near a named body of water, the waterbody picker populates itself without the user noticing, matching the "Catchbook should do the work first" principle from the brainstorm.
- **Regression guard:** No existing test suite fails after the refactor except for `FormLogicTests.testSpotFormLogicRequiresTrimmedTitleAndSelectedWaterbody`, which is deliberately updated.

## Dependencies & Risks

### Dependencies

- None external. This is a self-contained iOS refactor.
- SwiftData models already permit nil waterbody — no migration.
- Existing `WaterbodySearchModel` inside `NewWaterbodyForm.swift` is untouched.

### Risks

- **Risk:** Auto-detection false positives (MKLocalSearch returns a nearby unrelated lake name). **Mitigation:** unchanged from current behavior — user can clear the picker. Plan does not widen this surface.
- **Risk:** Auto-created waterbodies accumulate when users frequently drop pins in new places. **Mitigation:** accepted. These are real waterbodies with real names; they're useful records. Future work can add a "Hide unused waterbodies" toggle if needed.
- **Risk:** `prefillWaterbodyFromLocation` on `TripStartSheet` runs a network-dependent task during trip start, potentially delaying the UI. **Mitigation:** runs in a detached `Task`, does not block Start Trip. The user can tap Start Trip immediately; if the prefill arrives first, it attaches; if it arrives after Start Trip fires, the result is discarded.
- **Risk:** Existing tests that rely on `SpotFormLogic.canSave(title:selectedWaterbodyID:)` signature break compile. **Mitigation:** explicitly enumerated in the acceptance criteria — there is exactly one such test.

## Resource Requirements

- One engineer, ~half a day of focused work plus simulator QA. No infra, no migrations, no backend.

## Documentation Plan

- **ADR:** `docs/decisions/2026-04-13-waterbody-is-never-a-gate.md` — records the spec shift from the brainstorm (Phase 3 blocker). Without this, the next planner reading the brainstorm will think waterbody is still a required anchor and re-introduce a gate.
- **Brainstorm link-forward:** add a one-line "See ADR 2026-04-13 — waterbody is never a gate" pointer at the top of `docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md`.
- **Inline code comments** on `WaterbodyAutoDetectionService` covering: (a) the pure/impure split and why `findOrCreate` does not call `context.save()`, (b) the case-insensitive name dedupe as the race-safety mechanism, (c) the 6-second timeout on `detect(at:)` and the "silent on failure" contract.
- **Project note:** if `products/catchbook-ios/CLAUDE.md` exists (or the root `CLAUDE.md`'s "Catchbook" section), add: "Waterbody is optional everywhere. Never add a `waterbody != nil` gate in any new flow."

## Sources & References

### Origin

- **Brainstorm document:** [docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md](../brainstorms/2026-04-11-catchbook-location-model-brainstorm.md) — key decisions carried forward: "Catchbook should do the work first" (aggressive prefill), "Confidence should shape the UI more than provenance" (silent auto-detect, no "inferred" labels), "Use 'At' and 'Near' plain-language location cues". The brainstorm kept waterbody as the canonical anchor; this plan extends the intent by making waterbody fully optional at every entry point.

### Internal References

- Partial refactor to build on: commit `194078d` — `feat(catchbook): make spots map-first with crosshair pin placement and waterbody auto-detection`
- `products/catchbook-ios/Sources/Features/Forms/NewSpotForm.swift:46-62` — empty-state gate to delete
- `products/catchbook-ios/Sources/Features/Forms/NewSpotForm.swift:250-349` — auto-detect logic to extract (pure/impure split)
- `products/catchbook-ios/Sources/Features/Forms/FormLogic.swift:19-21` — `SpotFormLogic.canSave` to relax
- `products/catchbook-ios/Sources/Features/Home/TripStartSheet.swift:54-70` — empty-state gate to delete
- `products/catchbook-ios/Sources/Features/Home/TripStartSheet.swift:162, 166-171` — Start Trip disabled + helper to remove
- `products/catchbook-ios/Sources/Features/Home/TripStartSheet.swift:189-198` — `.onAppear` to split into `.task { }` (prefill) + `.onAppear` (permission prompt)
- `products/catchbook-ios/Sources/Features/Trips/TripEditingLogic.swift:48-55` — `canSave` to relax
- `products/catchbook-ios/Sources/Features/Trips/TripsView.swift:1605, 1629, 701` — caller update + placeholder rename + trip row fallback label
- `products/catchbook-ios/Sources/Features/Trips/TripHistoryLogic.swift:102-106` — `waterbodySummaries()` nil-group dropping (**new blocker caught by pattern audit**)
- `products/catchbook-ios/Sources/Features/Log/LogFeatureLogic.swift:276-278` — `shouldOfferCreateSpot` to relax
- `products/catchbook-ios/Sources/Features/ActiveTrip/ActiveTripView.swift:49-51` — `catchesForWaterbody` returns [] when nil; add explanatory comment
- `products/catchbook-ios/Sources/Services/ConditionCaptureService.swift`, `PersonalBestService.swift` — convention reference for service shape (`enum`, `@MainActor`, `ModelContext` parameter, internal `FetchDescriptor`)
- `products/catchbook-ios/Sources/Models/FishingModels.swift:206, 452` — proof that `Spot.waterbody` and `Trip.waterbody` are already optional
- `products/catchbook-ios/Tests/TestSupport/ModelTestSupport.swift` — `makeStore()` pattern for new in-memory ModelContext tests
- `products/catchbook-ios/Tests/Services/PersonalBestServiceTests.swift:5-28` — concrete test scaffolding pattern to mirror in new service tests
- `products/catchbook-ios/Tests/Features/Forms/FormLogicTests.swift:6-10` — test to update

### Related Work & Learnings

- `docs/solutions/integration-issues/catchbook-layered-location-model-rollout.md` — prior rollout that established the "lock the product contract before coding" pattern. Informs the ADR requirement in Phase 3.
- `docs/solutions/integration-issues/catchbook-angler-ux-parity-rollout.md` — warns that cross-cutting changes should be grouped by shared primitive (the service), not by screen. This plan follows that pattern.
- `docs/solutions/integration-issues/catchbook-competitive-gap-rollout.md` — flags the Xcode project target membership gotcha for new `.swift` files (incorporated into Phase 1).
- Prior brainstorm-driven plan: `docs/plans/2026-04-12-feat-catchbook-angler-ux-parity-plan.md`
- Partial-refactor commit: `194078d9`
- New ADR (to be created in Phase 3): `docs/decisions/2026-04-13-waterbody-is-never-a-gate.md`

### External References (Apple docs)

- [SwiftUI `View.task(_:)`](https://developer.apple.com/documentation/swiftui/view/task(priority:_:)) — cancellation semantics on view disappear
- [SwiftData Modeling data](https://developer.apple.com/documentation/swiftdata/modeling-data) — optional relationships, inverse declarations
- [CLGeocoder](https://developer.apple.com/documentation/corelocation/clgeocoder) — rate limiting guidance (Apple: "no more than one request per user action")
- [MKLocalSearch](https://developer.apple.com/documentation/mapkit/mklocalsearch) — offline and throttling behavior
- [Apple HIG — Pickers](https://developer.apple.com/design/human-interface-guidelines/pickers) — "None" convention and divider placement
- [Apple HIG — Entering data](https://developer.apple.com/design/human-interface-guidelines/entering-data) — intelligent defaults that remain easy to change
