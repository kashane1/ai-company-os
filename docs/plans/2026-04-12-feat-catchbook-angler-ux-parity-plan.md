---
title: "feat: Catchbook Angler UX Parity"
type: feat
status: active
date: 2026-04-12
product: catchbook
---

# Catchbook Angler UX Parity

## Overview

Turn the April 12, 2026 Anglers' Log deep comparison into an execution plan for
the next round of Catchbook usability and feature-parity improvements.

Primary source analysis:

- `docs/products/catchbook/anglers-log-deep-comparison-2026-04-12.md`

This plan is intentionally centered on field-speed, map quality, and "obvious
missing features" that would make anglers compare Catchbook unfavorably to
other fishing log apps.

The first shipping target is the four easy wins called out from the analysis:

1. auto-suggest species and lure from history
2. copy / duplicate catch
3. photo EXIF GPS to spot matching
4. satellite map toggle

This plan also identifies the next parity features worth scheduling once those
four land cleanly:

- catch pins on maps
- calendar view
- photo gallery / trophy wall
- configurable field visibility
- quick tally mode for high-volume sessions
- lightweight gear field with history suggestions

## Problem Statement

Catchbook already has strong privacy, native iOS fit, deterministic recall, and
a better location model than many competitors. The remaining risk is not core
philosophy; it is user perception.

If the app makes anglers type the same values repeatedly, manually re-enter
nearly identical catches, hand-resolve locations that their photos already
contain, or stare at standard map tiles while competitors offer satellite
imagery, the product will feel less complete than the market even where
Catchbook is smarter underneath.

The Anglers' Log comparison is especially useful because it highlights several
features that are:

- normal for serious fishing-log users
- highly visible in daily use
- compatible with Catchbook's private, local-first stance
- achievable without expanding into social features or vague analytics

## Planning Decision

Ship this as a narrow usability-and-parity track rather than a broad product
rewrite.

The right move is:

1. land the four easy wins first
2. build them on shared suggestion and location primitives
3. keep the logging flow fast and optionality low
4. queue the larger parity surfaces behind those primitives

This plan complements, but does not replace, the broader competitive-gap plan
in `docs/plans/2026-04-12-feat-catchbook-competitive-gap-plan.md`.

That existing plan covers schema and history gaps such as disposition, condition
fields, multi-photo support, camera capture, and catch search. This plan covers
the next layer: faster input, stronger map affordances, and expected fishing-log
workflow conveniences.

## Repo Context

Current implementation anchors:

- Shared map wrapper:
  [CatchbookMapView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Shared/UI/CatchbookMapView.swift)
- Spots list and map:
  [SpotsView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Spots/SpotsView.swift)
- Trips map surfaces and trip detail catch rows:
  [TripsView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Trips/TripsView.swift)
- Active trip quick-catch flow:
  [LogView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogView.swift)
- Quick-catch logic and current recent suggestions:
  [LogFeatureLogic.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogFeatureLogic.swift)
- Core models and trip/spot coordinate resolution:
  [FishingModels.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Models/FishingModels.swift)
- Existing location capture:
  [LocationRecorder.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Services/LocationRecorder.swift)
- Existing condition capture and fallback semantics:
  [ConditionCaptureService.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Services/ConditionCaptureService.swift)
- Existing spot creation flow:
  [NewSpotForm.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Forms/NewSpotForm.swift)
- Existing catch photo migration support:
  [CatchPhotoMigrationService.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Services/CatchPhotoMigrationService.swift)

Relevant product constraints and prior decisions:

- [MVP Spec](/Users/simons/ai-company-os/docs/products/catchbook/mvp-spec.md)
- [Backlog](/Users/simons/ai-company-os/docs/products/catchbook/backlog.md)
- [iOS Architecture](/Users/simons/ai-company-os/docs/products/catchbook/ios-architecture.md)
- [Layered Location Model Plan](/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md)
- [Location Model Rollout Learnings](/Users/simons/ai-company-os/docs/solutions/integration-issues/catchbook-layered-location-model-rollout.md)

## Research Summary

### What already exists

- Catchbook already has quick-pick species suggestions in the active trip flow,
  driven by trip targets plus recent catches.
- Catchbook already has recent lure suggestions for quick catch.
- Catchbook already supports a multi-photo catch model plus direct camera
  capture in both quick catch and catch edit.
- Trip detail catch rows already expose `Share Catch` through swipe actions and
  context menus.
- The app already has a strong layered location model, pin-first spot creation,
  and "create spot from this trip" after a finished session.

### What is missing despite nearby groundwork

- suggestions are quick picks only, not full low-friction history-backed input
  that scales as the log grows
- there is no duplicate-catch action in trip detail despite a natural context
  menu insertion point
- catch photos are stored, but there is no EXIF metadata extraction pipeline to
  reuse photo coordinates for spot matching
- `CatchbookMapView` wraps map rendering, but no user-facing map style toggle
  exists

### Key product insight

The goal is not to add more fields. The goal is to make Catchbook feel like it
does more of the work for the angler.

That principle is already consistent with the layered location model plan:
Catchbook should prefer smart defaults, nearby suggestions, and context reuse
before asking the user to type or decide more.

## Spec Flow

### Primary user flows this plan improves

1. Logging several similar catches during one trip
2. Logging a catch from a photo without remembering the exact spot name
3. Browsing fishing locations with actual shoreline and structure visible
4. Revisiting catch history without repetitive data entry

### Edge cases that must be handled

- photo has no GPS metadata
- photo has GPS metadata but no nearby saved spot
- multiple nearby spots are plausible matches
- duplicate catch must not overwrite the original record
- duplicate catch should not accidentally reuse timestamps when the user expects
  "now"
- map style choice should remain consistent across map surfaces
- history suggestions must avoid surfacing blank, whitespace, or typo variants
- logging must still work fully offline

### Scope boundaries

- no social or public map features
- no third-party map SDK
- no account or sync requirement
- no AI-generated species guessing
- no invasive schema expansion unless a feature clearly needs it

## Proposed Solution

Implement this track in three phases.

### Phase 1: Ship The Four Easy Wins

Goal: remove the most visible "why doesn't this app do that?" friction first.

#### 1.1 Upgrade history suggestions into real logging acceleration

Extend the existing suggestion logic in
[LogFeatureLogic.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Log/LogFeatureLogic.swift)
and the catch editor in
[TripsView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Trips/TripsView.swift)
so species and lure entry become history-powered instead of just static recent
chips.

Ship behavior:

- keep the current quick-pick chips for empty fields
- add inline filtered matches while the user types in `species`
- add inline filtered matches while the user types in `lureOrBait`
- normalize casing and whitespace so "largemouth bass" and "Largemouth Bass"
  collapse into one suggestion
- rank suggestions by:
  1. current trip spot
  2. current waterbody
  3. global recency / frequency
- preserve manual entry when the user wants something new

Implementation notes:

- introduce shared suggestion builders instead of duplicating logic across quick
  catch and catch editing
- consider a small `CatchHistorySuggestionService` or equivalent pure logic
  layer if this outgrows `LogFeatureLogic`
- support both empty-state chips and typed autocomplete from the same data
  source

Why this matters:

- after roughly 20 catches, many anglers should barely need to type
- suggestion quality becomes a product differentiator without needing any cloud
  intelligence

#### 1.2 Add copy / duplicate catch from trip detail

Use the existing context menu and swipe-action affordances in
[TripsView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Features/Trips/TripsView.swift)
to add `Duplicate Catch`.

Ship behavior:

- duplicate from a catch row context menu
- optionally expose the same action in swipe actions if it reads cleanly
- open the duplicated record in the existing catch editor, pre-filled
- default the duplicated catch timestamp to `Date()` for the common "same setup,
  just caught another fish" path
- preserve original species, lure, method, disposition, notes, water depth, and
  photos unless the user edits them

Decision:

- treat duplicate as "create a new draft based on this catch," not "clone and
  silently save"

This keeps the action safe, reversible, and consistent with the current editing
model.

#### 1.3 Add photo EXIF GPS to spot matching

Create a small metadata extraction pipeline that reads GPS coordinates from
selected or captured catch photos before save.

Ship behavior:

- when the user adds a photo to a catch, inspect EXIF metadata for GPS
- if GPS exists, compare it against saved spots within an internal default
  matching radius for v1
- if exactly one spot is a strong match, show a lightweight confirmation:
  "Caught near [Spot Name]?"
- if multiple spots are nearby, show a short ranked picker
- if no spot matches, preserve the extracted coordinate as candidate location
  context for:
  - catch editor helper text
  - future spot creation
  - optional "Create Spot from Photo" follow-up

Scope for this phase:

- do not force a catch-level coordinate schema yet
- do not redesign the whole logging flow into a multi-step wizard
- do not block save if metadata extraction fails
- do not add a user-facing matching-radius setting in the first pass

Implementation notes:

- use Apple-native image metadata APIs (`ImageIO` / `CGImageSource`)
- keep metadata parsing in a service, not in SwiftUI views
- introduce spot-matching logic that respects the layered location model and the
  user's saved spots, not a reverse-geocoding dependency
- reuse this pipeline for both library photos and camera photos where metadata
  is available

#### 1.4 Add a satellite / hybrid map toggle

Promote map style into a lightweight, reusable app preference on top of
[CatchbookMapView.swift](/Users/simons/ai-company-os/products/catchbook-ios/Sources/Shared/UI/CatchbookMapView.swift).

Ship behavior:

- one visible control cycles between `standard`, `hybrid`, and `satellite`
- style applies consistently in:
  - spots map
  - trip map surfaces
  - any other screen using `CatchbookMapView`
- remember the user's last-selected map style locally

Implementation notes:

- keep the API surface simple: `CatchbookMapView` should accept style input
  rather than each screen inventing its own map-type logic
- default to standard map on first launch to preserve current behavior

Why this is worth prioritizing:

- it is a small implementation with outsized perceived polish
- anglers care about structure, shoreline shape, and real-world water context

### Phase 2: Build On The Same Primitives

Goal: turn the four wins into stronger parity surfaces without reopening core
architecture.

#### 2.1 Catch pins on maps

Once photo/location helpers and map style controls exist, add optional catch
pins to trip and spot map surfaces.

Recommended scope:

- show catch markers on trip detail maps when the app has confident coordinates
- visually distinguish spots from catches
- only show catch pins when location confidence is honest

Dependency:

- depends on deciding whether EXIF-derived or future catch-level coordinates are
  persisted directly, or only used as soft context

#### 2.2 Calendar view

Add a month-view fishing calendar for frequency recall and day-based browsing.

Recommended scope:

- dots on dates with catches
- tap date to open that day's trip(s) and catches
- keep it deterministic and local

Why it belongs here:

- users expect journal products to answer "when did I fish?"
- it is a parity feature with high perceived completeness

#### 2.3 Photo gallery / trophy wall

Build an aggregate media surface now that multi-photo support already exists.

Recommended scope:

- grid of all catch photos
- tap photo to open the linked catch
- sort newest first
- no social framing, purely personal archive

### Phase 3: Configurable Simplicity And Power-User Capture

Goal: broaden parity without making the default app feel heavy.

#### 3.1 Configurable field visibility

Elevate `showingOptionalFields` into persistent user preferences.

Ship behavior:

- let users enable only the catch fields they care about
- hide disabled fields in quick catch, catch edit, and related summaries where
  appropriate
- keep the default profile minimal

This is the cleanest way to satisfy both casual and data-heavy anglers.

#### 3.2 Quick tally mode

Add a high-volume logging mode for days when users care about count more than
details.

Recommended scope:

- species-first incrementer
- fast add without photo or measurements
- convert tallies into catch records inside a trip

#### 3.3 Lightweight gear field

Add a simple `gear` text field with the same suggestion model as lure/species
before considering a full gear entity system.

This gives parity for anglers who want setup tracking without dragging Catchbook
into a large equipment-management feature.

## Data And Architecture Guidance

### Suggestion system

Create one shared normalization and ranking strategy for user-entered repeated
values:

- species
- lure or bait
- later: gear
- later: method, if useful

Keep the logic deterministic, local, and testable.

### EXIF metadata pipeline

If EXIF GPS support introduces reusable metadata, define a narrow type such as:

- `PhotoCaptureMetadata`
  - `capturedAt`
  - `coordinate`
  - `source`

Keep it ephemeral unless later features justify persistence.

### Map preferences

Store map style once and apply it everywhere. Do not let every screen drift into
its own separate map-style state.

## Acceptance Criteria

### Phase 1

- user can choose species and lure faster from history-backed suggestions in
  both quick catch and catch edit
- duplicate catch creates a new editable catch draft without mutating the
  original
- duplicate catch opens with timestamp defaulted to `now` for the common
  repeat-catch workflow
- adding a photo with GPS can surface nearby saved-spot matching
- absence of EXIF GPS never blocks logging
- user can toggle between standard, hybrid, and satellite map views
- selected map style persists locally across launches
- logic-bearing changes ship with matching iOS tests under
  `products/catchbook-ios/Tests/`

### Phase 2

- maps can show catch markers only when location confidence is honest
- user can browse fishing activity by calendar date
- user can browse all catch photos in a personal gallery

### Phase 3

- users can simplify the catch form by disabling fields they do not care about
- tally mode supports fast count-based logging
- optional gear tracking is available without adding heavy schema complexity

## Testing Strategy

Per the shared testing contract for iOS changes, logic-bearing work under
`products/catchbook-ios/Sources/` must ship with lane-matching tests under
`products/catchbook-ios/Tests/`.

Required test coverage by feature:

- suggestion normalization, deduping, and ranking
- duplicate-catch draft creation behavior
- EXIF GPS extraction success / no-metadata / invalid-metadata paths
- nearby-spot matching thresholds and tie-breaking
- persisted map style preference behavior
- manual QA on device for:
  - PhotosPicker flow
  - camera flow
  - map toggle behavior
  - trip-detail duplicate flow
  - offline logging with no metadata available

## Risks And Mitigations

### Risk: suggestion UI becomes noisy instead of helpful

Mitigation:

- keep empty-state quick picks compact
- only show typed suggestions when there is a meaningful match
- dedupe aggressively

### Risk: EXIF-derived location feels too precise

Mitigation:

- treat EXIF as a helper for spot matching, not automatic truth
- preserve existing layered-location confidence language
- require user confirmation before linking to a nearby saved spot

### Risk: duplicate catch accidentally creates bad history data

Mitigation:

- route through the existing editor before save
- set duplicated timestamps deliberately instead of silently copying stale time

### Risk: map style toggle fragments across screens

Mitigation:

- make `CatchbookMapView` the single style control point
- store one shared local preference

## Release Order Recommendation

Recommended shipping order:

1. satellite / hybrid map toggle
2. duplicate catch
3. upgraded history suggestions
4. photo EXIF GPS to spot matching
5. calendar view
6. photo gallery
7. configurable field visibility
8. tally mode
9. lightweight gear field

Reasoning:

- the first two are very visible and low-risk
- suggestion upgrades deliver daily value once the app has real usage
- EXIF GPS has the most implementation nuance and should build on the now-solid
  location foundation
- later items are strong parity moves, but less important than reducing daily
  logging friction

## Open Questions

- should EXIF GPS matching only suggest saved `Spot` records, or also offer
  waterbody-level helpers when no spot matches?
- should map style be a global app preference only, or also a per-screen quick
  toggle with global persistence?
- when catch pins arrive, do we need a user-facing "show catches on map" toggle
  to avoid clutter?

## Sources

- Anglers' Log comparison:
  [anglers-log-deep-comparison-2026-04-12.md](/Users/simons/ai-company-os/docs/products/catchbook/anglers-log-deep-comparison-2026-04-12.md)
- Broader competitive gap plan:
  [2026-04-12-feat-catchbook-competitive-gap-plan.md](/Users/simons/ai-company-os/docs/plans/2026-04-12-feat-catchbook-competitive-gap-plan.md)
- Catchbook MVP scope:
  [mvp-spec.md](/Users/simons/ai-company-os/docs/products/catchbook/mvp-spec.md)
- Catchbook backlog:
  [backlog.md](/Users/simons/ai-company-os/docs/products/catchbook/backlog.md)
- Location foundation:
  [2026-04-11-location-model-plan.md](/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md)
- Location rollout learnings:
  [catchbook-layered-location-model-rollout.md](/Users/simons/ai-company-os/docs/solutions/integration-issues/catchbook-layered-location-model-rollout.md)
