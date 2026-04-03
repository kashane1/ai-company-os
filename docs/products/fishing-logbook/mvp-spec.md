# MVP Spec: Private Fishing Logbook

## Scope

This MVP covers one complete loop for a private fishing memory app:

- start trip
- capture conditions
- log catches
- end trip
- review history
- surface deterministic recall

This pass expands the MVP slightly, but only in ways that strengthen private memory and pre-trip recall.

## Feature Order

### Build Now

- coherent deterministic spot-detail recall
- one-handed trip and catch logging refinements
- privacy-safe brag/share card export for catches or personal bests

### Build Next

- decision pass on narrow pattern replay and "last time here" memory surfaces
- seasonal memory nudges and personal-best story surfaces
- optional catch-scan-lite prefilling assist

### Later / Not Now

- compact Spot DNA style "what worked here" composition unless a later pass proves it adds value beyond the existing recall stack
- standalone fish ID
- social or community features
- widgets, Live Activities, App Intents, or Watch work
- broad analytics dashboards
- monetization implementation

## Core Screens

### Home

- resume current trip
- last trip summary
- suggested memory card
- "last time here" surface later, not in the current build-now slice
- personal bests card

### Trips

- trip list
- filters by water, species, season, and lure
- trip detail

### Log

- start trip
- add catch
- mark skunked trip

### Spots

- saved waters and spots
- map/list view later if helpful
- spot detail with history, performance summary, and deterministic support-gated recall

### Insights

- deterministic cards only
- no freeform AI responses
- no second insight engine separate from recall surfaces

### Sharing

- export-only brag/share card for a catch, trip, or personal best
- exact spot disclosure must remain off by default
- no feed, comments, profiles, or discovery loops

## Acceptance Criteria

### Trip Start

- user can create or select a water / spot
- app records start time and current location
- app captures a condition snapshot when possible
- trip can start without network connectivity

### Catch Logging

- user can log species with optional photo, weight, length, lure, method, and note
- time and current spot default automatically
- logging remains possible offline
- photo is optional and never blocks save

### History

- user can inspect past trips and catches
- user can filter by water, species, season, and lure
- user can view personal bests by species

### Spot Detail

- user can see trip count, catch count, recent catches, successful lures, and simple condition evidence
- summaries are derived from personal data only

### Spot Recall Summary

- spot detail recall should remain coherent enough without requiring a second composed summary layer
- any later Spot DNA style summary would need to be composed from existing deterministic outputs only
- no composed summary should ship unless it is clearly additive beyond the supported card stack

### Insights

- insights are deterministic and traceable to logged data
- cards must cite enough support to feel credible
- the app must not present speculative or generated advice

### Sharing

- user can export a catch or personal best share card without publishing data to other users
- exported card must omit exact coordinates and should default to coarse or generic location wording
- share support must not become a requirement for logging or recall flows

## Offline Assumptions

- trip start, catch logging, note entry, and history must work offline
- condition capture may degrade gracefully if a weather provider is unavailable
- sync is not required for MVP readiness
- share-card generation should work from local data once the user has already logged the catch

## Photo Handling

- photo use is optional
- failure to access photos or camera must not block core logging
- photo references should attach to catches, not define the logging flow
