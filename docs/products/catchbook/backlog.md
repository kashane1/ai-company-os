# Backlog: Private Fishing Logbook

## Build Now

- `ios_feature`: keep the base SwiftUI shell and SwiftData model set aligned with the private-memory wedge
- `ios_feature`: keep the compressed trip-start, quick-catch, trip end, and skunked-trip flows stable
- `ios_bugfix`: harden offline save, resume, and field-default behavior
- `ios_feature`: implement trips list, trip detail, spots list, and spot detail as the main recall surfaces
- `ios_feature`: keep deterministic spot-detail recall coherent across recent trips, lure, catch window, seasonality, catch rate, and similar conditions
- `ios_feature`: implement personal best summaries where they reinforce recall
- `ios_feature`: keep the export-only privacy-safe catch share card narrow: one template, one entry point, offline image render, no location by default
- `ios_feature`: keep seeded fixtures and acceptance coverage aligned with deterministic recall rules
- `engineering_change`: keep app-store positioning and screenshot story aligned with the updated wedge
- `ios_feature`: add a "Last time here" recall surface on spot detail and on trip-start when a known spot is selected, rendered from existing local data (no geofencing, no background location, no notifications)
- `ios_feature`: extend the existing catch share card with a computed personal-best badge (longest-of-species, heaviest-of-species, or first-of-species), always-on when true, one visual treatment, no separate surface or template
- ~~`ios_feature`: establish the layered location model for waterbody, spot, and trip semantics with clear fallback rules~~ ✓ done — canonical waterbody anchor, user-owned spot precision, trip fallback order, and shared `At` / `Near` confidence language are now defined and implemented
- ~~`ios_feature`: redesign waterbody creation as search-first with private/custom fallback~~ ✓ done — Phase 1 is locked to Apple MapKit search (`MKLocalSearchCompleter` / `MKLocalSearch`) plus immediate custom/private fallback
- ~~`ios_feature`: redesign spot creation around pin-first capture and map refinement~~ ✓ done — new spots now start from the best available coordinate and support map refinement before save
- ~~`ios_feature`: separate waterbody map anchoring from trip readback semantics~~ ✓ done — Trips map now distinguishes canonical water pins from legacy spot-centroid fallback
- ~~`ios_feature`: offer post-trip "create spot from this trip" when a finished trip has a usable saved location but no saved spot~~ ✓ done — trip summary now opens a prefilled new-spot flow from the resolved trip coordinate
- ~~`ios_feature`: expose Share Catch from the trip-detail catch row via swipe action or context menu so the share flow is discoverable without opening the edit sheet~~ ✓ done — trailing swipe + context menu added to trip-detail catch rows, both routing through `CatchSharing.makeImage` / `CatchShareCardRenderer`

## Build Next

- `ios_feature`: add seasonal memory nudges and personal-best story moments
- `ios_feature`: explore optional catch-scan-lite logging assist for field prefilling only
- `ios_feature`: refine spot memory browsing if map/list switching proves necessary after the core detail view is coherent
- `ios_feature`: define the lazy/eager/backfill strategy for older waters that still rely on legacy spot-centroid compatibility anchoring
- `ios_feature`: define denied-location and stale-location behavior for pin-first spot creation and trip-start fallback messaging
- `ios_feature`: decide whether post-trip spot creation should ship with suggested names or remain manual-only for the first pass

## Later / Not Now

- compact Spot DNA style "what worked here" composition unless a later pass shows it adds clear value beyond the current supported recall stack
- broader sharing system or multiple share templates
- standalone fish ID or species-ID-led onboarding
- social features, community feeds, or public discovery
- widgets
- Live Activities
- App Intents
- Watch support
- regulations or licensing workflows
- marketplace or team features
- broad analytics dashboards
- subscriptions or monetization implementation beyond doc-level planning
