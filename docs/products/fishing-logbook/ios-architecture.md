# iOS Architecture: Private Fishing Logbook

## Implementation Baseline

- UI framework: SwiftUI
- local persistence: SwiftData
- sync stance: CloudKit is deferred and documented, not required for first implementation
- maps and location: MapKit and Core Location
- photo handling: PhotosUI and camera access only where useful

## Local-First Stance

The app should be credible on the water even without service access.

- trip and catch logging must be local-first
- history and insights should derive from local data
- condition capture should degrade gracefully when network-backed data is unavailable

## Privacy-By-Default

- all spot data is private by default
- there is no public sharing or community surface in MVP
- any share surface must be explicit export, not discovery or profile infrastructure
- location precision should only serve the user’s own recall
- photo use is optional and user-controlled

## Data Model Direction

Core entities:

- Waterbody
- Spot
- Trip
- Catch
- ConditionSnapshot

Derived outputs:

- PersonalBest summaries
- deterministic InsightCards
- SpotRecall summaries
- privacy-safe ShareCard exports derived from local trip or catch data

## CloudKit Stance

- do not depend on CloudKit for MVP readiness
- leave room for later personal sync
- avoid schema decisions that force multi-user or server-centric design

## Deterministic Insights Boundary

- insights are computed from local user data only
- insight rules live in the product docs and schema contracts
- output cards must be reproducible and acceptance-testable
- no generative summarization is allowed in the MVP path
- compact Spot DNA output should compose existing deterministic rules instead of introducing a separate reasoning layer
- the current spot-detail recall stack is coherent enough without Spot DNA in the current MVP state

## Share Card Boundary

- share cards should render from already logged local data
- the current share slice is one fixed catch card only
- the current share slice has one entry point only: the existing catch detail/editor surface in trip history
- share cards must be built from an explicit allowlist of safe fields
- share cards must default to omitted location text
- share-card rendering must work fully offline
- share support must not require backend accounts, feeds, or multi-user schema
- the share layer is a wedge enhancer, not the product center

## Product Source Of Truth

During core implementation, engineers should treat these docs as authoritative:

- `product-brief.md`
- `mvp-spec.md`
- `insight-rules.md`
- `insight-acceptance-cases.md`
- `backlog.md`
