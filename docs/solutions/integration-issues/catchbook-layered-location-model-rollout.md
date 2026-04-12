---
title: "Rolling Out Catchbook's Layered Location Model"
category: integration-issues
date: 2026-04-12
tags:
  - catchbook
  - ios
  - mapkit
  - location-model
  - trips
  - spots
  - waterbodies
---

# Rolling Out Catchbook's Layered Location Model

## Problem

Catchbook had coordinates stored across `Waterbody`, `Spot`, `Trip`, and `ConditionSnapshot`, but the product did not clearly define what each coordinate meant. That made trip readback, map anchoring, and new form flows feel more precise than the app could honestly explain.

This also created planning risk: the product wanted a search-first waterbody flow, trip-level `At` / `Near` language, and better map behavior, but the implementation contract was still blurry around fallback order, provider choice, and historical data compatibility.

## Root Cause

The underlying issue was not one broken field. It was a missing semantic contract between four location layers:

- `Waterbody` should anchor the named place.
- `Spot` should capture the user's saved fishing area within that water.
- `Trip` should represent the outing location for that session.
- `ConditionSnapshot` should carry observed trip-time coordinates and weather context, not stand in for canonical water placement.

Without that contract, the UI and services mixed canonical place, user-saved spot, and observed outing coordinates as if they were interchangeable.

## Solution

We solved this by implementing the layered model directly in the app and aligning the plan, forms, service logic, and trip/map readback around the same fallback rules.

### 1. Lock the product contract before coding

The plan was updated to explicitly define:

- One trip belongs to exactly one waterbody.
- A trip may optionally reference one spot.
- Trip coordinate fallback order is:
  1. observed trip/device coordinate
  2. selected spot coordinate
  3. canonical waterbody coordinate
  4. no coordinate shown
- Water summary anchoring fallback order is:
  1. waterbody canonical coordinate
  2. legacy spot-centroid fallback
  3. no coordinate shown
- Phase 1 search uses Apple-native `MKLocalSearchCompleter` / `MKLocalSearch`, with immediate private/custom fallback.

That prevented engineering from having to invent product policy mid-implementation.

### 2. Encode fallback semantics in the models

`FishingModels.swift` became the single source of truth for layered location meaning.

Key additions:

- `ConditionSource` now distinguishes:
  - `deviceLocation`
  - `spotFallback`
  - `waterbodyFallback`
  - `tripFallback`
- `TripCoordinateSource` explicitly models:
  - `observed`
  - `spotFallback`
  - `waterbodyFallback`
  - `unresolved`
- `ConditionSnapshot.locationConfidenceLabel` and `Trip.locationConfidenceLabel` provide the shared `At` / `Near` UI language.
- `Trip.resolvedCoordinate` centralizes the real fallback order used by trip UI and later flows.

This kept the product language simple while preserving enough provenance internally.

### 3. Treat MapKit as the named-water entry path, not as a replacement for private waters

`NewWaterbodyForm.swift` was redesigned around:

- `MKLocalSearchCompleter` for typeahead suggestions
- `MKLocalSearch` to resolve the selected result into a coordinate
- manual/custom naming and pin placement when search is unavailable or unsuitable

The important learning here is that “search-first” should not mean “search-required.” The private/custom path has to be a first-class fallback or the flow starts fighting the product.

### 4. Make spot creation pin-first and reusable

`NewSpotForm.swift` now:

- starts from the best available coordinate
- allows map refinement before save
- persists spot latitude/longitude through `SpotFormLogic`
- supports preseeded coordinates so a finished trip can become a saved spot quickly

This made spot precision the main user-owned recall layer, which fits the product better than pushing precision onto catches.

### 5. Separate trip readback from water summary anchoring

`TripHistoryLogic.swift` was updated so water summaries carry both:

- the coordinate
- the coordinate source (`canonicalWaterbody` vs `legacySpotCentroid`)

That let the Trips map and water summary sheet explain when a pin is truly canonical versus when it is only a temporary compatibility fallback.

This distinction matters because trip-time coordinates are valid for outing recall, but they should not silently become persistent waterbody anchors.

### 6. Add the post-trip “create spot from this trip” path

Once trip fallback logic existed in the model, the clean next step was to use it in the trip-ended flow.

`TripEndedSummaryView` now offers “Create Spot from This Trip” when:

- the trip has no saved spot yet
- the trip belongs to a waterbody
- the trip has a resolvable coordinate

That CTA reuses the resolved trip coordinate and preselected waterbody, which turns the layered model into a practical recall workflow instead of a purely internal cleanup.

## What Worked Well

- Defining fallback order in the plan first made later coding decisions much easier.
- Putting `At` / `Near` behind shared computed properties avoided duplicated UI rules.
- Modeling water summary coordinate source separately from trip coordinate source kept canonical-place and outing-location semantics from bleeding together.
- Reusing the same trip coordinate resolution in the post-trip spot flow made the feature feel cohesive.

## What We Learned

### Lock provider contracts early

The review finding was right: “search-first” is not complete until the provider contract and fallback path are explicit. In this case the correct Phase 1 contract was:

- Apple MapKit for named-water search
- private/custom water creation as the immediate fallback
- no backend geocoding requirement for the first slice

That choice affects scope, privacy posture, and UX, so it should live in the plan, not just in implementation.

### A provenance model is more stable than a distance rule

We considered defining `At` versus `Near` using distance, but provenance turned out to be much cleaner:

- `At` = directly recorded or directly selected for that entity
- `Near` = inherited or fallback-derived from another layer

That rule is easier to test, easier to explain, and less brittle across different water sizes.

### Compatibility fallback needs separate rules for waterbody and trip contexts

The biggest planning cleanup was realizing these are different:

- waterbody anchoring compatibility
- trip readback compatibility

Using trip snapshot coordinates as a waterbody fallback would have quietly broken the distinction the redesign was trying to create. The right fix was to define separate fallback chains for water summaries and trip/readback contexts.

### Form changes are easiest to validate when logic is extracted first

Adding `WaterbodyFormLogic` and expanding `SpotFormLogic` before pushing deeper into SwiftUI forms made it much easier to add tests and keep the location persistence logic stable while the UI changed.

## Verification

Verified successfully:

- App builds after the location-model rollout.
- Model and logic tests were updated to cover:
  - `At` / `Near` behavior
  - condition source fallback layers
  - trip coordinate resolution order
  - water summary coordinate source behavior
  - post-trip spot-creation eligibility

Verification gap:

- Targeted `xcodebuild test` runs reached the simulator/runtime phase and then hung locally, even after explicitly booting the simulator. The code-level compile issues were fixed, but runtime test execution still appears to be blocked by local simulator environment instability rather than by the feature logic itself.

## Prevention

- When a feature changes data meaning, write the semantic contract in the plan before writing the UI.
- If one map surface represents a canonical place and another represents an outing, model those sources separately.
- For “search-first” product language, always define the provider and the non-network fallback together.
- When form flows depend on location semantics, extract pure draft/fallback logic first so tests can anchor the rollout.

## Related Files

- [/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md](/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Models/FishingModels.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Models/FishingModels.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Services/ConditionCaptureService.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Services/ConditionCaptureService.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Forms/NewWaterbodyForm.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Forms/NewWaterbodyForm.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Forms/NewSpotForm.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Forms/NewSpotForm.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Trips/TripHistoryLogic.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Trips/TripHistoryLogic.swift)
- [/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogView.swift)
