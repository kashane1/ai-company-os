# MVP Spec: Private Fishing Logbook

## Scope

This MVP covers one complete loop for a private fishing memory app:

- start trip
- capture conditions
- log catches
- end trip
- review history
- surface deterministic recall

## Core Screens

### Home

- resume current trip
- last trip summary
- suggested memory card
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
- spot detail with history and performance summary

### Insights

- deterministic cards only
- no freeform AI responses

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

- user can see trip count, catch count, recent catches, and successful lures
- summaries are derived from personal data only

### Insights

- insights are deterministic and traceable to logged data
- cards must cite enough support to feel credible
- the app must not present speculative or generated advice

## Offline Assumptions

- trip start, catch logging, note entry, and history must work offline
- condition capture may degrade gracefully if a weather provider is unavailable
- sync is not required for MVP readiness

## Photo Handling

- photo use is optional
- failure to access photos or camera must not block core logging
- photo references should attach to catches, not define the logging flow
