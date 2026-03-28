# Product Brief: Private Fishing Logbook

## Product Thesis

Private Fishing Logbook is a local-first iPhone app for repeat anglers who want a clean memory of trips, spots, catches, and conditions without exposing their waters publicly.

The product is a private performance companion:

- capture the trip quickly
- preserve the memory clearly
- surface deterministic reminders before the next outing

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

## MVP Promise

Remember what worked, without sharing your spots.

## MVP Boundaries

Include:

- trip start and end
- quick catch logging
- saved waters and spots
- basic history and filters
- personal bests
- deterministic recall cards

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
- photo capture is optional
- location data should be stored only for the user’s own recall

## Success Criteria

The system is successful when a user can:

- start a trip in seconds
- log a catch quickly with minimal fields
- review past performance by water or spot
- see simple, credible pattern cards before a new trip
