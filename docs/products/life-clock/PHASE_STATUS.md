# Phase Status

- **Product:** Life Clock
- **Last updated:** 2026-04-27
- **Phase:** discovery
- **Owner:** founder (Kashane)
- **Source tree:** `products/life-clock-ios/`
- **Docs root:** `docs/products/life-clock/`

## Current state

Founder pack ingested and registered. iOS MVP skeleton scaffolded under `products/life-clock-ios/` with deterministic engines, mockable HealthKit boundary, six SwiftUI screens, and unit tests.

- ✅ Founder pack normalized into platform conventions
- ✅ Product registered in `infra/products.json`
- ✅ Xcode project scaffold (`project.yml` + `Info.plist` + `PrivacyInfo.xcprivacy`)
- ✅ SwiftData models with `VersionedSchema`
- ✅ `ClockEngine` v1 (deterministic, pure)
- ✅ `QuestEngine` v1 (deterministic, pure)
- ✅ `MockHealthKitService` + `HealthKitServiceProtocol`
- ✅ Six SwiftUI screens with sample-data wiring
- ✅ Unit tests for engines and store
- ⏳ Live HealthKit wiring — deferred to follow-up plan
- ⏳ SwiftData persistence across cold starts — deferred
- ⏳ StoreKit 2 paywall — deferred
- ⏳ Brand-name resolution (Open Question 1) — deferred

## Next decisions

1. **Brand name resolution** — Life Clock vs TimeBack vs Long Game vs DayBank vs Clockwise vs Healthspan Quest (Open Question 1).
2. **Default UI for the clock** — projected date, projected age, or healthspan score (Open Question 2).
3. **Default tone mode** — gentle, coach, or memento mori (Open Question 3).
4. **Live HealthKit plan** — schedule the follow-up plan that adds entitlement + `LiveHealthKitService`.

## Out of scope for the current phase

- Backend / sync
- Paywall enforcement
- AI health coach
- Bloodwork / lab interpretation
- Calorie database
- Apple Watch companion
- Widgets / Lock Screen surfaces
- Push notifications
