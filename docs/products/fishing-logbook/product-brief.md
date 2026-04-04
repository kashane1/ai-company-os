# Product Brief: Private Fishing Logbook

## Product Thesis

Private Fishing Logbook is a local-first iPhone app for repeat anglers who want a clean memory of trips, spots, catches, and conditions without exposing their waters publicly.

The product is a private performance companion:

- capture the trip quickly
- preserve the memory clearly
- surface deterministic reminders before the next outing
- optionally share the win without giving away the spot

## User And Job

Target user:

- a repeat angler who fishes favorite waters
- wants to improve over time
- values privacy over community
- uses ad hoc memory, notes, photos, or a bloated fishing app today

Primary job:

- remember what worked, under what conditions, at which spot, before the next trip

## Value Proposition

- faster than Notes for logging
- more private than social fishing apps
- more focused than all-in-one legacy utilities
- more native and trustworthy than web-heavy tools

## Product Rules

- local-first by default
- privacy-first spot handling
- deterministic insights only
- no AI theater
- no forced social graph
- offline-safe core logging flow
- sharing, if present, must be export-first and privacy-safe

## MVP Promise

Remember what worked, without sharing your spots.

## Expanded MVP Direction

This product is still intentionally narrow. The allowed expansion is meant to strengthen the wedge, not widen the category.

### Build Now

- keep the current coherent spot-detail recall surface stable
- keep the current compressed trip-start and quick-catch flows stable
- keep the current privacy-safe catch share card narrow, export-only, and private by default

### Build Next

- make a narrow product decision on pre-trip pattern replay such as "last time here" before implementation
- add seasonal memory nudges if they clearly reinforce deterministic recall
- add personal-best story surfaces that make progress feel memorable
- explore catch-scan-lite logging assist only as optional field prefilling, not as species-ID product identity

### Later / Not Now

- compact Spot DNA composition unless a later pass shows it adds clear value beyond the current supported card stack
- standalone fish identification
- any social, feed, follow, or community product shape
- marketplace, regulations, licensing, or team workflows
- broad analytics or dashboard expansion
- widgets, Live Activities, App Intents, or Apple Watch work
- monetization implementation beyond lightweight positioning prep

## MVP Boundaries

Include:

- trip start and end
- quick catch logging
- compressed trip start
- saved waters and spots
- basic history and filters
- personal bests
- deterministic recall cards
- deterministic spot-detail recall
- privacy-safe export sharing for a catch only, using one fixed card with omitted location by default

Exclude:

- social feed
- crowdsourced maps
- team tools
- marketplace
- species ID
- regulations
- heavy planning workflows

## Local-First And Sync Stance

- persistence choice: SwiftData for the first implementation path
- sync stance: treat CloudKit as a documented later phase, not a launch dependency
- offline stance: all core logging flows must work without connectivity

## Privacy Defaults

- all spots are private by default
- no public sharing model in MVP
- if a user shares anything, it should be an explicit export with omitted location detail by default
- photo capture is optional
- location data should be stored only for the user’s own recall

## Success Criteria

The system is successful when a user can:

- start a trip in seconds
- log a catch quickly with minimal fields
- review past performance by water or spot
- see simple, credible recall surfaces before a new trip
- share a memorable catch without compromising a private spot

## Current MVP State

- the spot-detail recall stack is coherent enough for the current MVP
- trip start and quick catch have both been compressed for lower-friction field use
- Spot DNA is deferred
- pattern replay is deferred
- sharing currently exists only as one export-only catch card from the catch detail/editor surface
