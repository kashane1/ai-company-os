---
title: "feat: Implement layered location model for Catchbook"
type: feat
status: active
date: 2026-04-11
product: catchbook
origin: docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md
---

# feat: Implement layered location model for Catchbook

Catchbook needs a clearer, more trustworthy location model that improves recall, supports the new Spots and Trips maps, and preserves the product's low-friction logging feel. The current model stores coordinates in multiple places with different meanings, which makes some records feel more precise than the product can honestly explain on maps or in summaries (see brainstorm: `docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md`).

This plan adopts the brainstorm's recommended **layered location model**: waterbody as canonical place anchor, spot as user-owned recall area, trip as observed outing location, and catch-level precision deferred until later value is proven (see brainstorm: `docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md`).

## Why Now

- the app now has Spots and Trips map surfaces, so ambiguous location semantics are visible to users
- the current data model already separates `Waterbody`, `Spot`, `Trip`, and `ConditionSnapshot`, but their coordinate responsibilities are not explicit enough yet
- future recall and insight surfaces depend on location data being trustworthy before they become more ambitious

## Research Summary

### Repo findings

- Catchbook product artifacts live under `docs/products/catchbook/`, so this plan is stored there instead of inventing a new planning directory.
- The current iOS architecture already declares the relevant entities: `Waterbody`, `Spot`, `Trip`, `Catch`, and `ConditionSnapshot` in [docs/products/catchbook/ios-architecture.md](/Users/simons/ai-company-os/docs/products/catchbook/ios-architecture.md).
- The current product posture is local-first and privacy-by-default, with location precision only serving the user's own recall, not sharing or discovery.
- The current MVP docs explicitly say further recall or logging redesign is not approved yet, so this plan should be treated as the approval artifact for that redesign in [docs/products/catchbook/mvp-spec.md](/Users/simons/ai-company-os/docs/products/catchbook/mvp-spec.md).

### Current implementation touchpoints

- Data models live in [FishingModels.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Models/FishingModels.swift).
- Trip-start location and condition fallback behavior lives in [ConditionCaptureService.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Services/ConditionCaptureService.swift) and [LogView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogView.swift).
- Waterbody and spot creation flows live in [NewWaterbodyForm.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Forms/NewWaterbodyForm.swift) and [NewSpotForm.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Forms/NewSpotForm.swift).
- Spots and trip map/readback behavior lives in [SpotsView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Spots/SpotsView.swift), [SpotPresentationLogic.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Spots/SpotPresentationLogic.swift), and `TripsView.swift`.
- Backup/export implications live in [LogbookBackupExporter.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Services/LogbookBackupExporter.swift).

### Institutional learnings

- No relevant `docs/solutions/` entries currently exist, so this plan relies on product docs and current implementation patterns.

### External research decision

External research is not required for this planning pass. The work is product- and repo-specific, the current codebase already contains the key constraints, and this plan is primarily about clarifying internal semantics and phased implementation.

## Decision Summary

### Chosen approach

Adopt **Approach B: Layered Location Model** from the brainstorm (see brainstorm: `docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md`).

### Decisions carried forward from the brainstorm

- Catchbook should do the work first through smart defaults, nearby suggestions, and context reuse.
- `Waterbody` should have one canonical coordinate used as the representative map anchor for the place.
- `Spot` should remain user-owned and user-named, with pin-drop support becoming the primary precision layer for recall.
- Trip location should remain distinct from waterbody location by preserving the observed outing coordinate in the trip condition snapshot.
- Catch-level coordinates are deferred and should not be required in this redesign.
- The model should distinguish exact, inferred, and inherited location internally even if the main UI uses simpler confidence language.
- The main UI should favor confidence cues like "At" and "Near" over provenance-heavy system wording.
- Map behavior should prefer user memory structures over raw GPS noise.

## Problem Statement

Today, Catchbook has enough location data to imply precision, but not enough consistent semantics to explain what each coordinate means:

- `Waterbody` already supports optional latitude/longitude, but the creation flow does not treat those coordinates as canonical place anchors.
- `Spot` already supports optional latitude/longitude, but spot creation does not yet guide users into pin-drop capture or easy location refinement.
- `ConditionSnapshot` stores trip-time coordinates, but that location is currently presented as a generic snapshot fallback rather than an explicitly observed outing location.
- Maps and summaries therefore mix canonical place, saved spot, and observed trip coordinates without a clear contract.

## Goals

- make maps trustworthy by giving each coordinate layer a clear role
- improve memory recall without forcing precision-first logging
- reduce data-entry burden through prefills, strong guesses, and easy correction
- preserve local-first and privacy-by-default behavior
- create a clean foundation for later location-aware summaries

## Non-Goals

- requiring catch-level coordinates in this pass
- building social, public, or collaborative map features
- introducing server-side geocoding or sync dependencies as a prerequisite
- exposing provenance-heavy system language everywhere in the main flow
- shipping advanced heatmaps or full analytical map layers now

## Scope

### In scope

- explicit product rules for waterbody, spot, and trip location ownership
- updates to the SwiftData model where needed to represent location semantics clearly
- waterbody entry redesign toward search-first plus map-assisted selection
- spot creation redesign toward immediate pin-drop with optional map refinement
- trip-start and trip-detail updates so observed outing location stays distinct from place anchors
- clearer fallback rules for Spots and Trips maps
- export/backup coverage for any new location semantics fields
- test coverage for new logic-bearing model and UI-support logic

### Out of scope for this phase

- catch-level exact bite-zone capture
- broad map analytics or density overlays
- CloudKit or backend-driven location normalization
- release-note, App Store, or marketing updates beyond doc references

## Product Rules

### Waterbody

- A waterbody represents the named place.
- A waterbody should have one canonical coordinate when Catchbook has a confident place anchor.
- That coordinate should drive search ranking, zoomed-out map anchoring, weather fallback when needed, and water-level summaries later.
- Known named waters should be selectable through search-first entry when possible (see brainstorm: `docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md`).
- Private/custom waters must remain possible when no known named water is appropriate.

### Spot

- A spot represents the user's remembered fishing area within a waterbody.
- Spot names remain user-entered.
- Spot coordinates are the primary user-owned precision layer.
- Spot creation should start from the best available current location and make map refinement easy before save.

### Trip

- A trip represents the outing itself, not the waterbody center.
- Every trip belongs to exactly one waterbody.
- A trip may optionally reference one saved spot within that waterbody.
- The trip's observed location should live in trip-owned location data, starting with `ConditionSnapshot` in the current architecture.
- Trip coordinate fallback order should be:
  1. directly recorded trip/device coordinate
  2. selected spot coordinate
  3. canonical waterbody coordinate
  4. no coordinate shown
- Weather/location snapshots must not be conflated with canonical waterbody coordinates.
- If the trip used a saved spot, the UI should still preserve the distinction between "saved place" and "observed outing location."

### Catch

- Catch-level coordinates remain optional and deferred.
- No current acceptance criterion should require users to place a pin for a catch.

## UX Plan

### Waterbody entry

- Replace the current manual-only waterbody creation path with a search-first flow.
- Phase 1 should use Apple-native MapKit search (`MKLocalSearchCompleter` / `MKLocalSearch`) as the named-water discovery path.
- As the user types, Catchbook should show likely waterbody/place matches, ranking nearby likely matches first.
- A nearby map action should allow the user to choose a waterbody by pin if search is not sufficient.
- If search is unavailable, offline, or yields no suitable result, the user must be able to create a private/custom waterbody immediately.
- When a dropped pin is near a likely canonical named water, the product may suggest snapping to that named water, but should not force it.

### Spot creation

- When creating a spot, prefill the pin from the best available current location.
- Show the map early enough that the user understands the spot has a location, but keep saving fast for users who do not want to fine-tune.
- Preserve user naming ownership by never system-generating the final spot name.

### Trip start and trip detail

- Keep the current compressed trip-start flow.
- Use strong defaults when a waterbody or spot is selected.
- Distinguish saved-place context from outing-location context in the product language and data model.
- After a trip with no saved spot, suggest creating a spot from the observed trip location.

### Confidence language

- Use "At" when the app is showing a directly recorded or directly user-selected coordinate for the entity being shown.
- Use "Near" when the app is showing an inherited or fallback-derived coordinate from another location layer.
- For trips specifically:
  - `At` means the trip has its own observed outing coordinate.
  - `Near` means the trip is being represented by a selected spot coordinate or the canonical waterbody coordinate.
- Keep deeper provenance available in the model and secondary UI without making the main logging flow feel technical.

## Technical Plan

### Phase 1: Canonical waters and spot precision

#### Data model

- Audit `Waterbody`, `Spot`, and `ConditionSnapshot` in [FishingModels.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Models/FishingModels.swift) for fields needed to represent:
  - canonical waterbody coordinate
  - spot precision coordinate
  - location confidence/provenance metadata
- Prefer extending existing models rather than introducing parallel location objects in this phase.
- If provenance fields are added, ensure they are exportable in [LogbookBackupExporter.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Services/LogbookBackupExporter.swift).

#### UX and flow work

- Redesign [NewWaterbodyForm.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Forms/NewWaterbodyForm.swift) around MapKit-backed search-first entry with a clear private/custom fallback.
- Redesign [NewSpotForm.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Forms/NewSpotForm.swift) to start from a dropped pin using best-available location and optional map refinement.
- Keep the existing "New Water" / "New Spot" affordances in [LogView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogView.swift), but upgrade what happens inside those flows.

#### Map updates

- Update Spots map behavior so spot pins represent saved user spots only.
- Update trip/water summaries so waterbody maps anchor on canonical waterbody coordinates instead of inferred spot centroids wherever possible.
- Preserve a compatibility fallback for existing data until canonical waterbody coordinates are populated.
- For waterbody anchoring contexts, use:
  1. waterbody canonical coordinate
  2. existing spot-derived centroid fallback
  3. no coordinate shown
- For trip/readback contexts where a trip-level coordinate is needed before canonical data is available, use:
  1. trip `ConditionSnapshot` coordinate
  2. selected spot coordinate
  3. canonical waterbody coordinate
  4. no coordinate shown

### Phase 2: Observed trip location and map fallback semantics

#### Data and service work

- Clarify `ConditionCaptureService` semantics so trip snapshots represent observed outing location rather than generic fallback location.
- Add explicit fallback ordering rules:
  1. observed device location
  2. selected spot coordinate
  3. canonical waterbody coordinate
  4. no coordinate shown
- Preserve enough provenance internally to explain which layer produced a displayed pin when needed.

#### UX and display work

- Update trip-start condition preview and trip detail screens to separate saved place from observed location.
- Introduce confidence-language display rules for "At" versus "Near" in trip- and map-adjacent UI.
- Add post-trip "create spot from this trip" suggestions when a trip ends without a saved spot.

### Phase 3: Deferred precision and advanced summaries

- Revisit catch-level coordinates only after Phase 1 and 2 prove real user value.
- Use the cleaned-up layered model to support later location-aware recall summaries such as productive waters, reliable spots, and better map-backed recall.
- Keep any future exact-catch map surfaces gated behind clear value and uncluttered UX.

## SpecFlow Analysis

### Core user flows

1. User starts a trip with an existing named water and existing saved spot.
2. User starts a trip with an existing named water but no saved spot.
3. User creates a new waterbody through search-first entry during trip start.
4. User creates a new private/custom waterbody through map/manual fallback.
5. User creates a new spot with a prefilled pin and optionally refines it.
6. User completes a trip without a saved spot and is offered post-trip spot creation.
7. User opens the Spots map or Trips map and expects every pin to mean something legible and stable.

### Gaps identified during flow analysis

- The plan needs a product decision for how aggressively map-selected waters should snap to nearby canonical named waters versus staying custom/private.
- The plan needs a concrete rule for suggested spot names after a trip, even if the first implementation ships with minimal suggestions.
- The plan should define what happens when the device has no current location permission or returns stale/low-confidence coordinates during spot creation.
- The plan should define whether older records without canonical waterbody coordinates are backfilled lazily, eagerly, or left unchanged until edited.

### Planning response to those gaps

- Treat snapping strategy and suggested spot-name patterns as required product decisions before implementation starts.
- Default offline and denied-location behavior to manual save with no forced pin refinement.
- Handle historical data migration incrementally and safely; do not block the redesign on a perfect backfill.

## Acceptance Criteria

- Users can create or select a waterbody through a search-first flow while still supporting private/custom waters.
- New waterbodies can store a canonical coordinate when Catchbook has a confident place anchor.
- Users can create a spot with an immediate suggested pin and refine it without leaving the save flow.
- Spot names remain user-entered.
- Trip condition snapshots continue to capture observed outing location separately from the waterbody's canonical coordinate.
- Spots map pins represent saved spots, not inferred water centers.
- Trip and map surfaces apply a documented fallback order and confidence-language rule.
- After a trip without a saved spot, Catchbook can suggest creating one from the trip's observed location.
- Export/backup paths preserve any new location semantics fields introduced by this work.
- Logic-bearing changes ship with matching iOS tests under `products/catchbook-ios/Tests/`.

## Testing Plan

- add model/service tests for location fallback ordering and provenance/confidence mapping
- extend `ConditionCaptureServiceTests` for observed-versus-inherited location behavior
- add form and presentation-logic tests for search-first waterbody selection, spot pin defaults, and map fallback logic
- update backup/export tests if the serialized model changes
- add acceptance-oriented tests for post-trip spot suggestion triggers if that logic becomes deterministic and local

## Risks

- over-designing provenance fields could slow down a product-facing improvement that should stay simple
- map search or canonical-water selection could add friction if the flow feels like data cleanup instead of recall support
- changing location semantics without careful migration could make old records look inconsistent
- surfacing too much precision language could undermine the lightweight tone the brainstorm wants to preserve

## Dependencies

- product approval on snapping behavior for map-selected waters
- product approval on suggested spot-name patterns
- validation of any SwiftData schema evolution needed for persisted semantics fields

## Rollout Order

1. Approve this plan and resolve the critical open product questions below.
2. Update product docs that serve as source of truth if scope is approved:
   - `docs/products/catchbook/mvp-spec.md`
   - `docs/products/catchbook/backlog.md`
   - `docs/products/catchbook/ios-architecture.md`
3. Implement Phase 1 behind the existing local-first flows.
4. Validate map semantics and trip-location clarity before starting Phase 2.
5. Defer any catch-level precision work until after real usage of the layered model.

## Open Questions

- Should map-based waterbody selection automatically snap to a nearby canonical named waterbody, or default to private/custom creation unless the user explicitly confirms a named match?
- Which suggested spot-name patterns should ship first after a trip: nearby place labels, directional hints, shoreline features, or note-derived suggestions?
- Should the broader "Catchbook should do the work first" principle remain in this feature scope, or be elevated into shared product guidance across future logging flows?

## Sources

- Origin brainstorm: [2026-04-11-catchbook-location-model-brainstorm.md](/Users/simons/ai-company-os/docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md)
- Product spec: [mvp-spec.md](/Users/simons/ai-company-os/docs/products/catchbook/mvp-spec.md)
- Product backlog: [backlog.md](/Users/simons/ai-company-os/docs/products/catchbook/backlog.md)
- iOS architecture: [ios-architecture.md](/Users/simons/ai-company-os/docs/products/catchbook/ios-architecture.md)
- Current model: [FishingModels.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Models/FishingModels.swift)
- Trip capture flow: [LogView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogView.swift)
- Spot flow: [NewSpotForm.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Forms/NewSpotForm.swift)
- Water flow: [NewWaterbodyForm.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Forms/NewWaterbodyForm.swift)
- Condition capture: [ConditionCaptureService.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Services/ConditionCaptureService.swift)
