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

## Build Next

- `product_decision`: decide whether a narrow pre-trip pattern replay surface such as "last time here" is justified before implementation
- `ios_feature`: add seasonal memory nudges and personal-best story moments
- `product_decision`: decide whether personal-best sharing is worth doing separately from the current catch-card share slice
- `ios_feature`: explore optional catch-scan-lite logging assist for field prefilling only
- `ios_feature`: refine spot memory browsing if map/list switching proves necessary after the core detail view is coherent

## Later / Not Now

- compact Spot DNA style "what worked here" composition unless a later pass shows it adds clear value beyond the current supported recall stack
- broader sharing system or multiple share templates
- personal-best sharing
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
