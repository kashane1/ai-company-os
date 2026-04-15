---
title: "Rolling Out Catchbook's Navigation Revamp"
category: integration-issues
date: 2026-04-13
tags:
  - catchbook
  - ios
  - swiftui
  - swiftdata
  - mapkit
  - navigation
  - refactoring
  - xcode
  - planning
---

# Rolling Out Catchbook's Navigation Revamp

## Problem

Catchbook's navigation had grown organically into a four-tab shape (Home → Trips → Log → Spots) that no longer matched how anglers actually work. Five related issues were tangled together:

1. **`LogView.swift` was a 1,223-line monolith.** It contained `StartTripView`, `ActiveTripView`, `CatchHistoryRow`, `PrimaryActionLabel`, `EndTripReviewView`, `TripEndedSummaryView`, `ActiveTripStatusCard`, and `ConditionPreviewRow` — most as `private struct`s that couldn't be reused anywhere else.

2. **Cross-tab navigation threaded `@Binding var selectedTab: AppTab` through every view.** This worked for the original two transitions (Home→Log, Log→Trips) but was fragile with 4+ cross-tab transitions planned (Home→ActiveTrip, ActiveTrip→Trips, Spots→Home, SpotDetail→Home).

3. **Backup export lived in HomeView's toolbar.** Wrong place semantically — it's a rare settings-style action, not a home-screen primary.

4. **Spots tab defaulted to list view** with map as a toggle. But anglers think spatially — the map is the natural primary for a fishing spots view.

5. **Waterbody creation forced users to manually type a water name** every time they created a new spot, even though the pin coordinate already tells us what body of water they're standing on.

The implementation risk wasn't one bug. It was a set of coordinated structural changes that had to ship together or the app would be in a half-migrated state.

## Root Cause

The underlying issue was that the original navigation had been built incrementally. The Log tab pattern (a dedicated tab for starting and logging catches) didn't scale when we needed trip start from Home AND from Spots. The `@Binding` pattern didn't scale past a handful of cross-tab transitions without becoming an ISP violation. `LogView` had grown without boundaries because all its supporting types were `private` — making extraction impossible without a deliberate refactor.

Research into competitor apps (LogIT, Anglers' Log, Fishing Journal: Angler Log) all revealed the same pattern: Home hosts trip start + active trip resume, Spots is map-first, and a More tab holds inventory/export/stats. Catchbook needed to converge on that architecture.

## Solution

The rollout ran in three phases. Each phase built cleanly and compiled before moving to the next.

### Phase 1 — Navigation Revamp (commit `d08cf6e`)

**New tab order:** Home → Spots → Trips → More. Log tab removed entirely.

**Created `AppRouter` (`Sources/App/AppRouter.swift`)** as the single source of truth for cross-tab navigation:

```swift
@Observable
class AppRouter {
    var selectedTab: AppTab = .home
    var homePath: [HomeDestination] = []
    var pendingTripStart: TripStartContext?

    func showActiveTrip(_ trip: Trip) {
        selectedTab = .home
        homePath = [.activeTrip(trip)]
    }

    func navigateToTripHistory(_ trip: Trip) {
        selectedTab = .trips
    }

    func requestTripStart(spot: Spot? = nil, waterbody: Waterbody? = nil) {
        selectedTab = .home
        pendingTripStart = TripStartContext(preselectedSpot: spot, preselectedWaterbody: waterbody)
    }
}

enum HomeDestination: Hashable {
    case activeTrip(Trip)
}

struct TripStartContext: Identifiable {
    let id = UUID()
    let preselectedSpot: Spot?
    let preselectedWaterbody: Waterbody?
}
```

Injected once at the app root via `.environment(router)`, read in child views as `@Environment(AppRouter.self) private var router`. When a view needs two-way binding to router state (like `.sheet(item: $router.pendingTripStart)`), shadow it locally with `@Bindable var router = router` inside the view body.

**Decomposed `LogView.swift`** into four files:
- `Sources/Features/ActiveTrip/ActiveTripView.swift` — the active-trip catch logging flow plus `EndTripReviewView`, `TripEndedSummaryView`, `ActiveTripStatusCard`, `EndedTripSummary`
- `Sources/Features/Home/TripStartSheet.swift` — the start-trip flow, reshaped as a sheet presented from Home
- `Sources/Shared/UI/PrimaryActionLabel.swift` — shared button label (used in multiple flows)
- `Sources/Shared/UI/CatchHistoryRow.swift` — shared catch row (used in both ActiveTripView and TripsView)

Only `PrimaryActionLabel` was extracted speculatively. `SuggestionRow`, `SavedConfirmationBanner`, etc. stayed private inside `ActiveTripView` because they had no confirmed second consumer.

**Created `MoreView`** (`Sources/Features/More/MoreView.swift`) as a grouped `List` with four sections: My Inventory, Data & Export, Stats & Insights, About. The backup export logic (previously in HomeView's toolbar) moved here.

**`TripStartSheet` active-trip guard:** Before creating a new trip, check for an existing active trip. If one exists, present a confirmation alert: "End current trip at [location] and start a new one?" This prevents the UI from ever holding multiple simultaneous active trips.

### Phase 2 — Spots Map-First + Waterbody Auto-Detection (commit `194078d`)

**`SpotsView` defaults to `showsMap = true`** and shows a hybrid map with all spot pins by default. A list toggle remains available.

**Crosshair pin-drop pattern.** SwiftUI `Map` has no native long-press gesture, so the established fishing-app pattern is:
1. User taps `+` to enter "add spot mode"
2. A fixed crosshair overlay appears at map center
3. User pans/zooms to position the crosshair over the desired water
4. User taps "Add Spot Here" button
5. `confirmAddSpot()` reads `mapCameraPosition.region?.center` and presents `NewSpotForm(initialCoordinate:)`

**Multi-layer waterbody auto-detection** added to `NewSpotForm.swift`. When `initialCoordinate` is set, a `.task` kicks off `detectWaterbody()`:

```swift
private func detectWaterbody() async {
    guard let coordinate = selectedCoordinate ?? initialCoordinate else { return }
    isDetectingWaterbody = true
    waterbodyDetectionFailed = false

    // Layer 1: CLGeocoder reverse geocoding
    let geocoder = CLGeocoder()
    let location = CLLocation(latitude: coordinate.latitude, longitude: coordinate.longitude)
    if let placemarks = try? await geocoder.reverseGeocodeLocation(location),
       let placemark = placemarks.first {
        if let waterName = placemark.inlandWater {
            await applyDetectedWaterbody(name: waterName, coordinate: coordinate)
            isDetectingWaterbody = false
            return
        }
        if let oceanName = placemark.ocean {
            await applyDetectedWaterbody(name: oceanName, coordinate: coordinate)
            isDetectingWaterbody = false
            return
        }
    }

    // Layer 2: MKLocalSearch nearby water features
    for query in ["lake", "river", "reservoir"] {
        let request = MKLocalSearch.Request()
        request.naturalLanguageQuery = query
        request.region = MKCoordinateRegion(
            center: coordinate,
            latitudinalMeters: 2000,
            longitudinalMeters: 2000
        )
        if let response = try? await MKLocalSearch(request: request).start(),
           let nearest = response.mapItems.first,
           let name = nearest.name {
            await applyDetectedWaterbody(name: name, coordinate: coordinate)
            isDetectingWaterbody = false
            return
        }
    }

    // Layer 3: Manual entry fallback
    isDetectingWaterbody = false
    waterbodyDetectionFailed = true
}
```

`applyDetectedWaterbody` does case-insensitive name matching against existing `Waterbody` records before creating a new one, and infers `WaterbodyType` from name keywords ("river"/"creek"/"stream" → `.river`, "pond" → `.pond`, "ocean"/"sea"/"gulf"/"bay" → `.coastal`, default → `.lake`).

**"Start Trip Here" button** added as the first section of `SpotDetailView`. It calls `router.requestTripStart(spot: spot, waterbody: spot.waterbody)` which switches to the Home tab and presents `TripStartSheet` with the spot pre-selected via `TripStartContext`.

**Pin tap → `SpotDetailView` as a sheet** with `.presentationDetents([.medium, .large])`, instead of navigating to the detail view as a NavigationLink.

### Phase 3 — More Screen Buildout (commit `c31b318`)

**Added `SavedLure` SwiftData model** (`Sources/Models/FishingModels.swift`):

```swift
@Model
final class SavedLure {
    @Attribute(.unique) var id: UUID
    var name: String
    var color: String
    var notes: String
    var createdAt: Date

    init(name: String, color: String = "", notes: String = "") {
        self.id = UUID()
        self.name = name
        self.color = color
        self.notes = notes
        self.createdAt = .now
    }
}
```

**Important:** Standalone entity, no inverse relationship to `CatchRecord`. This avoids a dual-source-of-truth problem and lets us add it as a purely additive schema change (no `SchemaMigrationPlan` needed). Registered in `CatchbookApp.swift` alongside the existing models.

**Feature views** in `Sources/Features/More/`:
- `SavedLuresView.swift` + `SavedLuresLogic.swift` — CRUD list with add/edit form sheet
- `SpeciesListView.swift` + `SpeciesListLogic.swift` — aggregate all caught species with counts
- `PersonalBestsListView.swift` — full vertical list of personal bests (replaces the horizontal-scroll capped at 6 on Home)

### Post-merge refinements (by user)

After merge, the user pushed the simplification further in `TripStartSheet.swift`:
- **Removed the waterbody picker entirely.** `selectedWaterbodyID` is now silent state, set by background auto-detection via a new `prefillWaterbodyFromLocation()` method. Users only pick (or skip) a spot.
- **Added `.characterLimit` modifiers** to all text fields in `TripStartSheet` and `SavedLuresView` (`CharacterLimits.tripTargetSpecies`, `tripNotes`, `lureName`, `lureColor`, `lureNotes`).
- **Changed spot sort** from `\Spot.createdAt` to `\Spot.title` for more intuitive picker ordering.
- **Moved `locationRecorder.requestIfNeeded()` out of `.onAppear`** and alongside prefill in a dedicated `.task`, so SwiftUI can cancel mid-flight if the user dismisses.

These align with the original plan's intent — the user independently arrived at the conclusion that manual waterbody selection was unnecessary friction.

## Key Learnings (Gotchas)

### 1. `project.pbxproj` membership is a four-part contract

Every new `.swift` file needs entries in **four** sections or the build fails:
1. `PBXFileReference` — the file exists
2. `PBXBuildFile` — the file is built
3. `PBXSourcesBuildPhase` files array — the file is compiled into the target
4. Group tree (`PBXGroup` children) — the file shows up in Xcode's navigator and resolves its path

Missing any one causes a confusing failure mode:
- Missing PBXFileReference → Xcode can't find the file at all
- Missing PBXBuildFile → "cannot find type" errors despite the file existing
- Missing from PBXSourcesBuildPhase → file is in the project but never compiled
- Missing from group tree → path resolution can fail silently, or the file shows up in the wrong target's compile list

I hit this three times during the rollout. The past `catchbook-competitive-gap-rollout.md` learning explicitly warned about this, and I still underestimated how easy it is to miss.

**Batching helps.** When adding 6+ files, use a Python script that updates all four sections atomically:

```python
new_files = [
    ("AppRouter.swift", "Sources/App/AppRouter.swift"),
    ("ActiveTripView.swift", "Sources/Features/ActiveTrip/ActiveTripView.swift"),
    # ...
]
# Generate stable 24-char hex IDs once
# Add PBXFileReference entries
# Add PBXBuildFile entries
# Add to PBXSourcesBuildPhase files array
# Add to correct PBXGroup children
```

Regenerating random IDs per-section is a trap — the build file entries must reference the same IDs used in the sources phase.

### 2. NavigationStack nesting is the #1 SwiftUI navigation mistake

If a `TabView` child is wrapped in `NavigationStack` by the parent AND the child already has its own `NavigationStack`, you get:
- Broken back buttons (hierarchical state confusion)
- Duplicated toolbar items
- Sheet presentations attached to the wrong stack
- NavigationDestination resolution failures

Each tab must have exactly ONE NavigationStack. If a child view needs programmatic navigation (like `TripsView` with its `NavigationStack(path: $path)`), that child owns its stack and the parent provides none. If a child is simple (like `HomeView`), the parent can provide the stack.

In the Catchbook revamp, I initially wrapped every tab in CatchbookApp's `NavigationStack` AND left the existing NavigationStacks inside SpotsView/TripsView/MoreView. The `"cannot find AppRouter in scope"` error cascade masked what was actually a nested-stack issue. Removing the outer wrapper for those three tabs (keeping it only for Home, which uses `homePath` binding) fixed it.

### 3. `MapCameraPosition` doesn't support `if case let` pattern matching

This looks reasonable but fails at compile time:

```swift
// ❌ WRONG — "pattern variable binding cannot appear in an expression"
if case let .region(region) = mapCameraPosition {
    addSpotCoordinate = region.center
}
```

`MapCameraPosition` is a struct, not an enum with case-pattern support. Use the public accessors instead:

```swift
// ✅ RIGHT
addSpotCoordinate = mapCameraPosition.region?.center
```

### 4. SwiftUI `Map` has no native long-press gesture

For drop-pin UX, the established pattern in fishing apps is crosshair + button:
1. Show a fixed crosshair at map center (inside a `ZStack`, with `.allowsHitTesting(false)` so it doesn't block map panning)
2. Let the user pan the map to position the crosshair
3. Read the coordinate from `mapCameraPosition.region?.center` when the user taps a confirm button

This avoids all the UIKit bridging you'd need for a `UILongPressGestureRecognizer`, and avoids gesture conflicts with the map's built-in pan/zoom.

### 5. `CLGeocoder.inlandWater` is ~30-50% reliable

In testing against real-world US water bodies, `placemark.inlandWater` returned a name roughly 30-50% of the time for named lakes in well-mapped regions. Small ponds, unnamed creeks, and remote water bodies returned nil. Offshore locations return nil from `inlandWater` entirely and may populate `.ocean` with broad names like "Pacific Ocean".

**Always have a fallback.** The multi-layer strategy (CLGeocoder → MKLocalSearch → manual entry) ensures the flow completes even when the first-line detection fails. And **CLGeocoder doesn't work offline at all** — it returns `kCLErrorNetwork` without connectivity. The UX must degrade gracefully: show "Couldn't identify the waterbody — you can name it manually" and leave the manual entry path open.

### 6. SwiftData additive schema changes need zero migration code

Adding a new `@Model` class (like `SavedLure`) to the container's model list is a purely additive schema change. SwiftData handles it automatically via lightweight migration — no `SchemaMigrationPlan`, no `VersionedSchema`, no code.

This only holds if:
- No required properties added to existing models
- No new relationships to existing models
- New model is standalone

The moment you add a `@Relationship` back from a new model to an existing one, or add a non-optional property without a default, you're in migration territory and need an explicit plan.

### 7. `@Observable` + `@Environment` + `@Bindable`

The pattern for cross-view state with two-way binding on an observable router:

```swift
// Parent: inject
.environment(router)

// Child: read
@Environment(AppRouter.self) private var router

// Child body: shadow with @Bindable for bindings
var body: some View {
    @Bindable var router = router
    SomeView()
        .sheet(item: $router.pendingTripStart) { context in
            TripStartSheet(context: context)
        }
}
```

Without the `@Bindable` shadow, you can read router state but can't create a `Binding` to it for sheet items or similar.

## Prevention Strategies

1. **When adding new `.swift` files, script the `pbxproj` update.** Write a Python helper that takes a list of (name, path, group) tuples and updates all four sections atomically with matching IDs.

2. **Verify `pbxproj` membership before debugging "cannot find type" errors.** That's almost always a project-file issue, not a Swift scope issue.

3. **When restructuring navigation, audit nested NavigationStacks first.** Grep for `NavigationStack` across all views that will be under a new TabView root and decide exactly ONE owner per tab.

4. **Extract view types speculatively only when reuse is confirmed.** Leaving types as `private` inside a feature file is fine. Premature extraction to Shared/UI/ creates its own maintenance burden.

5. **Prefer `@Observable` + `@Environment` over `@Binding` threading** when cross-cutting state has 3+ transition paths. The threshold is low.

6. **When adding SwiftData models, check if they have relationships to existing models.** If yes, write a migration plan. If no, you're additive-only and need nothing.

7. **For any new network-dependent feature, design the offline path first.** CLGeocoder, MKLocalSearch, WeatherKit all require connectivity. The flow must work when they don't respond.

8. **Character limits on `TextField` are cheap UX.** Apply them proactively via a shared `.characterLimit(_:text:)` modifier to prevent runaway input.

## Verification Performed

- `xcodebuild -scheme Catchbook -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build` — all three phases built cleanly, each commit at the end of its phase was a green build
- Every new `.swift` file confirmed present in `PBXFileReference`, `PBXBuildFile`, `PBXSourcesBuildPhase`, and its group's children array
- `LogView.swift` deletion confirmed with no remaining references (`.log` tab case, `LogView` type, `StartTripView`, `EndedTripSummary`, `ConditionPreviewRow`)
- `AppRouter`, `HomeDestination`, `TripStartContext` compile and resolve as expected in all consumer files
- Manual code-read verification that each tab has exactly one `NavigationStack` (Home via root, Spots/Trips/MoreView via their own)

## Related

- [Catchbook Layered Location Model Rollout](./catchbook-layered-location-model-rollout.md) — earlier rollout that defined the Waterbody/Spot/Trip coordinate contract this revamp builds on
- [Catchbook Angler UX Parity Rollout](./catchbook-angler-ux-parity-rollout.md) — earlier rollout that established the grouped-by-primitive pattern for cross-cutting UI work
- [Catchbook Competitive Gap Rollout](./catchbook-competitive-gap-rollout.md) — earlier rollout that first warned about `project.pbxproj` membership being part of "done"
- Plan file: `/Users/simons/.claude/plans/imperative-floating-goblet.md` (original deepened plan)
- Commits: `d08cf6e` (Phase 1), `194078d` (Phase 2), `c31b318` (Phase 3)
- Competitive research: `docs/products/catchbook/competitive-deep-dive-2026-04-12.md`, `docs/products/catchbook/anglers-log-deep-comparison-2026-04-12.md`
