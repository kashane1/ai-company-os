# Backlog: Private Fishing Logbook

## Build Now

- `ios_feature`: keep the base SwiftUI shell and SwiftData model set aligned with the private-memory wedge
- `ios_feature`: finish trip start, quick catch logging, trip end, and skunked-trip support with strong one-handed defaults
- `ios_bugfix`: harden offline save, resume, and field-default behavior
- `ios_feature`: implement trips list, trip detail, spots list, and spot detail as the main recall surfaces
- `ios_feature`: implement deterministic spot-detail recall using recent trips, top lure, time window, seasonality, catch rate, and similar conditions
- `ios_feature`: implement personal best summaries where they reinforce recall
- `ios_feature`: add export-only privacy-safe share cards for a catch or personal best with coarse or omitted location detail
- `ios_feature`: keep seeded fixtures and acceptance coverage aligned with deterministic recall rules
- `engineering_change`: keep app-store positioning and screenshot story aligned with the updated wedge

## Build Next

- `product_decision`: decide whether a narrow pre-trip pattern replay surface such as "last time here" is justified before implementation
- `ios_feature`: add seasonal memory nudges and personal-best story moments
- `ios_feature`: explore optional catch-scan-lite logging assist for field prefilling only
- `ios_feature`: refine spot memory browsing if map/list switching proves necessary after the core detail view is coherent

## Later / Not Now

- compact Spot DNA style "what worked here" composition unless a later pass shows it adds clear value beyond the current supported recall stack
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
