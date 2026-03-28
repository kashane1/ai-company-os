# Backlog: Private Fishing Logbook

## Epic 1: Product Foundation

- `ios_feature`: create the base SwiftUI app shell in `products/fishing-logbook-ios/`
- `ios_feature`: define SwiftData models for waterbody, spot, trip, catch, and condition snapshot
- `ios_feature`: create seed fixtures for deterministic insight acceptance cases

## Epic 2: Trip Logging Core Loop

- `ios_feature`: implement trip start flow with water / spot selection
- `ios_feature`: implement quick catch logging with defaults
- `ios_feature`: implement trip end and skunked-trip support
- `ios_bugfix`: harden offline save and resume behavior

## Epic 3: History And Spot Recall

- `ios_feature`: implement trips list and trip detail
- `ios_feature`: implement spots list and spot detail summaries
- `ios_feature`: implement personal best summaries

## Epic 4: Deterministic Insights

- `ios_feature`: implement rules engine for time window, top lure, seasonality, catch rate, and similar conditions
- `ios_feature`: render insight cards from rule output only
- `ios_bugfix`: validate insight output against seeded acceptance cases

## Epic 5: App Store Preparation

- `engineering_change`: keep app-store positioning brief aligned with the product
- `engineering_change`: seed screenshot planning and metadata draft state
- `engineering_change`: prepare release draft record for TestFlight and App Store review

## Not In Scope For Core MVP

- widgets
- Live Activities
- App Intents
- Watch support
- social features
- team features
- marketplace and subscriptions plumbing beyond structural prep
