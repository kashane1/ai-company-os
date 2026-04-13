# iOS Architecture: Catchbook

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

Location responsibilities:

- `Waterbody` is the canonical named-place anchor.
- `Spot` is the user-owned saved fishing area within a waterbody.
- `Trip` belongs to exactly one waterbody and may optionally reference one spot.
- `ConditionSnapshot` carries observed trip-time location and weather context; it should not be treated as a canonical waterbody anchor.

Trip and map fallback rules:

- trip coordinate fallback order:
  1. directly observed trip/device coordinate
  2. selected spot coordinate
  3. canonical waterbody coordinate
  4. unresolved / no coordinate shown
- waterbody summary anchoring fallback order:
  1. waterbody canonical coordinate
  2. legacy spot-centroid compatibility fallback
  3. unresolved / no coordinate shown
- trip readback and waterbody anchoring intentionally use different fallback chains because outing-location semantics and named-place semantics are different

UI language:

- main trip-adjacent UI should use `At` for directly recorded trip coordinates
- main trip-adjacent UI should use `Near` for inherited spot or waterbody fallback coordinates
- deeper provenance may remain in model/service logic without surfacing technical wording in the core logging flow

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

## Maps And Search Contract

- MapKit is the Phase 1 named-water provider
- `MKLocalSearchCompleter` / `MKLocalSearch` are the approved search-first waterbody entry path
- private/custom water creation must remain available immediately when search is unavailable, offline, or not a fit
- spot creation should start from the best available coordinate and allow map refinement before save
- a finished trip without a saved spot may offer "create spot from this trip" using the trip's resolved coordinate fallback

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
