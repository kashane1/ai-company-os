---
title: "feat: Catchbook Competitive Gap Closure"
type: feat
status: active
date: 2026-04-12
---

# Catchbook Competitive Gap Closure

## Overview

Turn the April 12, 2026 competitive deep dive into an execution plan for
Catchbook that includes every remaining Tier 1 must-have and Tier 2 should-have
feature that fits the current MVP boundaries:

- released vs kept logging
- richer condition capture (water clarity, moon phase, air pressure, tide state)
- water depth on catches
- multiple catch photos
- direct camera capture
- catches-per-hour and total-fishing-time stats
- all-catches search and flat catch list

Source analysis:
`docs/products/catchbook/competitive-deep-dive-2026-04-12.md`

This plan keeps Catchbook inside its current product stance:

- private by default
- local-first and offline credible
- deterministic insights only
- no social/community features
- no broad analytics dashboard expansion

## Problem Statement

Catchbook already has strong privacy, location modeling, and deterministic
recall advantages, but the competitive deep dive highlights a set of missing
features that ordinary fishing-log users will reasonably expect. Several are
small data-model gaps, while others are structural gaps in media handling,
history browsing, and computed stats.

If we do not close these gaps, Catchbook risks feeling polished but incomplete:

- no way to record whether a fish was released or kept
- no way to capture several common fishing conditions competitors store
- no multi-photo support for hero/measurement/release shots
- no direct camera path while on the water
- no flat catch history or search once the log grows
- no simple effort metrics like duration and catches per hour

## Repo Context

Current implementation anchors:

- Models:
  `products/catchbook-ios/Sources/Models/FishingModels.swift`
- Trip start and quick catch UI:
  `products/catchbook-ios/Sources/Features/Log/LogView.swift`
- Trip/history/detail UI:
  `products/catchbook-ios/Sources/Features/Trips/TripsView.swift`
- Logging logic:
  `products/catchbook-ios/Sources/Features/Log/LogFeatureLogic.swift`
- Condition capture:
  `products/catchbook-ios/Sources/Services/ConditionCaptureService.swift`
- Weather enrichment:
  `products/catchbook-ios/Sources/Services/WeatherKitService.swift`
- Backup/export:
  `products/catchbook-ios/Sources/Services/LogbookBackupExporter.swift`

Relevant product constraints:

- `docs/products/catchbook/mvp-spec.md`
- `docs/products/catchbook/ios-architecture.md`
- `docs/products/catchbook/backlog.md`

## Planning Decision

Ship all remaining must-have and should-have items, but in dependency order.

The work falls into three buckets:

1. Additive schema and condition enrichment changes with low UX risk
2. Logging and media workflow changes with moderate UI and migration risk
3. History and statistics surfaces built on top of the new/derived data

The only feature that needs special migration treatment is multiple photos per
catch. Everything else can be designed as additive and backwards-compatible.

## Proposed Solution

Implement the gap closure in four phases.

### Phase 1: Data Foundation And Derived Context

Goal: land the smallest schema changes first so the rest of the UI can build on
stable persisted fields.

#### 1.1 Extend `ConditionSnapshot`

Add:

- `waterClarityRawValue: String`
- `moonPhaseRawValue: String`
- `pressureHPa: Double?`
- `tideStateRawValue: String`

Use enums with safe fallback behavior similar to existing raw-value fields so we
keep persistence resilient.

Suggested enums:

- `WaterClarity`: `notRecorded`, `clear`, `stained`, `muddy`
- `MoonPhase`: `newMoon`, `waxingCrescent`, `firstQuarter`, `waxingGibbous`,
  `fullMoon`, `waningGibbous`, `lastQuarter`, `waningCrescent`
- `TideState`: `notRecorded`, `incoming`, `outgoing`, `high`, `low`, `slack`

Implementation notes:

- compute moon phase locally from `capturedAt`; no network dependency
- enrich air pressure from WeatherKit when available
- keep tide state manual to avoid bringing in new APIs or fragile heuristics
- fold the new fields into existing summary/rendering helpers only where the
  added context is genuinely useful, not everywhere by default

#### 1.2 Extend `CatchRecord`

Add:

- `dispositionRawValue: String`
- `waterDepthM: Double?`

Suggested enum:

- `CatchDisposition`: `notRecorded`, `released`, `kept`

Design constraints:

- default both fields to optional / not recorded so quick logging stays fast
- do not split `lureOrBait` yet; that remains an explicit later decision

#### 1.3 Add derived trip metrics

Add lightweight computed helpers on `Trip` or `LogFeatureLogic` /
`TripPresentationLogic` for:

- total fishing time
- catches per hour

Rules:

- duration derives from `endAt - startAt` when the trip is ended
- catches per hour is hidden for active trips, zero-duration trips, or no-catch
  trips where the value would read as misleading noise

#### 1.4 Version and export compatibility

Update backup/export support so new fields survive export:

- extend `ConditionSnapshotExportRecord`
- extend `CatchExportRecord`
- keep format changes additive if possible
- bump backup format version only if required by the multi-photo phase

### Phase 2: Catch Media Migration And Capture Workflow

Goal: replace the single-photo model with a scalable catch-media design.

#### 2.1 Introduce `CatchPhoto`

Create a dedicated SwiftData model instead of storing multiple `Data` blobs
directly on `CatchRecord`.

Suggested shape:

- `id`
- `catchRecord`
- `createdAt`
- `sortOrder`
- `contentType`
- `photoReference`
- `@Attribute(.externalStorage) photoData`

Why this direction:

- scales cleanly from 1 photo to 2-4 photos
- supports hero-photo ordering
- keeps future fullscreen/gallery behavior straightforward
- avoids making `CatchRecord` a bag of numbered photo fields

Registration requirements:

- add `CatchPhoto.self` to `products/catchbook-ios/Sources/App/CatchbookApp.swift`
  model container registration
- add `CatchPhoto.self` to test model-container setup in
  `products/catchbook-ios/Tests/TestSupport/ModelTestSupport.swift`
- verify previews/tests that create in-memory model containers can persist and
  fetch `CatchPhoto` records before wiring any UI to the new model

#### 2.2 Migration strategy

Do not delete `CatchRecord.photoData` in the same step that introduces
multi-photo support.

Safer rollout:

1. add `CatchPhoto`
2. teach reads to prefer `CatchPhoto` but fall back to legacy `photoData`
3. backfill legacy single photos into one `CatchPhoto` per catch on first launch
   or via a one-time migration routine
4. only remove legacy single-photo fields in a later cleanup pass

This reduces data-loss risk and keeps the share/export stack working during the
transition.

Compatibility contract during transition:

- introduce one shared photo accessor on `CatchRecord` or adjacent presentation
  logic for `heroPhotoData` / `primaryPhoto`
- make trip detail, quick-catch review, catch editing, share-card rendering, and
  flat catch history read through that shared accessor instead of reading
  `photoData` directly
- prefer ordered `CatchPhoto` media first and fall back to legacy `photoData`
  until the cleanup pass is complete
- keep migration and fallback logic out of SwiftUI views so behavior stays
  consistent and testable

#### 2.3 Update logging and editing flows

Update quick catch and catch editing to support:

- 0 to 4 photos per catch
- add from library
- replace/remove individual photos
- first photo as default hero image for lists/share card until a picker is added

#### 2.4 Add direct camera capture

Add a camera action alongside the existing photo-library action in:

- quick catch
- catch edit sheet

Rules:

- camera permissions failure must never block save
- library fallback remains available
- simulator / unavailable-camera environments must degrade gracefully

### Phase 3: Logging UX And Condition UX

Goal: expose the new fields without slowing the field workflow down.

#### 3.1 Quick catch and catch editor

Add optional fields for:

- disposition (`Released`, `Kept`, `Not recorded`)
- water depth

Placement:

- disposition belongs above deep optional notes/media fields because it is the
  most important new catch attribute
- water depth belongs in optional numeric details with length/weight

#### 3.2 Start trip and trip detail conditions

Expose:

- water clarity picker
- tide state picker
- moon phase display (auto-captured, read-only)
- air pressure display when weather enrichment succeeds

Recommended UX:

- keep start-trip flow compressed
- place water clarity and tide in optional condition controls
- show moon phase and pressure in the condition summary/detail areas once
  captured rather than forcing extra user input

#### 3.3 Condition presentation

Update trip detail and spot recall support surfaces to present the new condition
fields selectively:

- water clarity is candidate evidence for spot recall and future insights
- pressure and moon phase belong in detailed condition sections first
- tide should display when present, especially for coastal trips

Do not overstuff card summaries. The app should still read like a memory tool,
not a telemetry dump.

### Phase 4: History, Search, And Stats Surfaces

Goal: make the richer data browsable and useful.

#### 4.1 Add flat catch history

Introduce an all-catches view reachable from the Trips tab or as a sibling
history mode.

Minimum capabilities:

- reverse-chronological catch list
- species/lure/date context
- optional trip/waterbody chips
- hero photo thumbnail when present

Do not replace the trip-grouped history; add the flat list as a complementary
surface.

#### 4.2 Add catch search

Add search across the flat catch list for:

- species
- lure or bait
- notes
- waterbody / spot title if available through relationships

Prefer local filtering first. The dataset is likely small enough for in-memory
search at MVP scale.

Architecture decision:

- create a dedicated `CatchHistoryLogic` owner for flat catch list shaping,
  search, and future catch-centric filters
- keep `TripHistoryLogic` focused on trip-grouped history, sections, map
  summaries, and trip-level filters
- define a minimum `CatchHistoryFilter` model with search text plus any first-cut
  flat-list filters we actually ship, so we do not spread ad hoc filtering
  through `TripsView`
- add focused tests for `CatchHistoryLogic` instead of embedding filtering
  behavior only in SwiftUI view state

#### 4.3 Surface effort metrics

Display:

- total fishing time
- catches per hour

Recommended placements:

- trip summary cards in trip end / trip detail
- optional aggregate stat on Home or Trips later, only if it reads cleanly

Keep this focused on recall and effort, not dashboard sprawl.

## Delivery Order

Recommended implementation order:

1. Condition and catch additive fields
2. Weather/moon derived enrichment
3. Logging UI for disposition, depth, clarity, and tide
4. Derived duration / catches-per-hour presentation
5. Flat catch list and search
6. `CatchPhoto` model introduction
7. Multi-photo UI
8. Camera capture integration
9. Export/share/history polish on top of the migrated photo model

This order gets nearly every must/should-have into user hands before the
highest-risk migration work finishes.

## Acceptance Criteria

### Data And Persistence

- `CatchRecord` stores disposition and water depth without breaking older data
- `ConditionSnapshot` stores water clarity, moon phase, air pressure, and tide
  state without requiring network access
- moon phase is auto-derived from trip date/time
- air pressure is captured when WeatherKit succeeds and remains nil otherwise

### Logging

- anglers can mark a catch as released or kept from the quick-catch and edit
  flows
- anglers can optionally record water depth on a catch
- anglers can optionally record water clarity and tide state for a trip
- the default logging path remains fast and does not require any new field

### Media

- catches can hold multiple photos
- users can add a photo from the library or directly from the camera
- camera/library failures never block saving a catch
- existing single-photo catches remain readable after the migration

### History And Search

- users can browse a flat all-catches list
- users can search catches by species, lure/bait, notes, and related place names
- trip-grouped history remains intact

### Stats

- ended trips show total fishing time
- ended trips show catches per hour when the value is meaningful

## Tests

Because these are logic-bearing iOS changes under
`products/catchbook-ios/Sources/`, each phase must ship with matching tests
under `products/catchbook-ios/Tests/`.

Add or extend tests in:

- `Tests/Models/FishingModelsTests.swift`
  for new enums, fallbacks, and computed properties
- `Tests/Services/ConditionCaptureServiceTests.swift`
  for moon phase and pressure enrichment behavior
- `Tests/Services/WeatherKitServiceTests.swift`
  for pressure mapping
- `Tests/Features/Log/LogFeatureLogicTests.swift`
  for quick-catch defaults, reset behavior, and new summary rules
- `Tests/Features/Trips/TripEditingLogicTests.swift`
  for persistence/edit behavior of new catch fields
- `Tests/Features/Trips/TripPresentationLogicTests.swift`
  for trip summary cards and condition presentation
- `Tests/Services/LogbookBackupExporterTests.swift`
  for export records and media packaging
- `Tests/TestSupport/ModelTestSupport.swift`
  to register and exercise the new `CatchPhoto` model in test containers

New tests likely needed:

- `Tests/Features/Trips/CatchHistoryLogicTests.swift`
  for flat-list search, filtering, and hero-photo presentation shaping
- `Tests/Features/Trips/CatchSearchLogicTests.swift`
  only if search behavior ends up separate from `CatchHistoryLogic`
- `Tests/Shared/CatchPhotoMigrationTests.swift`
  or equivalent migration/backfill coverage

## Risks And Mitigations

### Multi-photo migration risk

Risk:
legacy `photoData` is baked into logging, editing, sharing, and backup/export.

Mitigation:
ship `CatchPhoto` as an additive model first and keep legacy fallbacks during the
transition.

### MVP flow bloat risk

Risk:
too many new fields could make logging feel heavy.

Mitigation:
keep new inputs optional, grouped, and collapsed behind the current compressed
logging philosophy.

### Weather dependency risk

Risk:
pressure capture could encourage hidden dependency on online weather fetches.

Mitigation:
moon phase is local-only, pressure is opportunistic, and all new weather fields
must degrade to nil cleanly.

### Scope creep risk

Risk:
the app could slide from recall tool into full analytics platform.

Mitigation:
ship only the requested must/should-have features and keep aggregate metrics
limited to effort-oriented readouts.

## Explicitly Out Of Scope

Still deferred after this plan:

- satellite map toggle
- favorite/starred trips
- water level
- distance from shore
- auto-fill from photo EXIF
- fullscreen photo zoom
- swipe-to-delete safety toggle
- tackle box, route tracking, AI fish ID, tournament mode, Apple Watch, and
  forecast features

## Suggested Task Breakdown

1. `ios_feature`: add competitive-gap enums and additive persisted fields to
   `CatchRecord` and `ConditionSnapshot`
2. `ios_feature`: enrich WeatherKit capture and local moon phase calculation
3. `ios_feature`: expose disposition, water depth, water clarity, and tide in
   logging flows
4. `ios_feature`: add total fishing time and catches-per-hour summary surfaces
5. `ios_feature`: add flat catch list and local search
6. `ios_feature`: introduce `CatchPhoto` with backward-compatible read path
7. `ios_feature`: upgrade catch media UI to multi-photo support
8. `ios_feature`: add direct camera capture to logging and editing flows
9. `ios_feature`: update share/export/backup code for the migrated media model

## Recommended First Cut

If we want the fastest path to "all must-have and should-have coverage" without
blocking on migration work, build in this first milestone:

- disposition
- water clarity
- moon phase
- air pressure
- tide state
- water depth
- total fishing time
- catches per hour
- flat catch list
- catch search

Then treat multi-photo support plus direct camera capture as the second
milestone, because those are the only items that meaningfully change the media
architecture.
