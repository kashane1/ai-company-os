# Catchbook Founder Brief

- Source: `/Users/simons/Desktop/founders-pack-fishing-journal.rtf`
- Normalized for platform use on 2026-03-28

## Core Bet

Build an iPhone-first private fishing logbook for serious hobby anglers who want to remember what worked, where, and under which conditions.

- Not a social network
- Not a generic forecast app
- Not generative AI for fishing

The wedge is private fishing memory, fast on-the-water logging, and simple pattern recall before the next trip.

This pass allows a small MVP expansion that strengthens the wedge without widening the category:

- deepen spot recall
- allow privacy-safe shareability only where it reinforces personal memory rather than social behavior

## Product Thesis

The product wins if it feels:

- faster than Notes
- more private than Fishbrain
- more elegant than legacy fishing utilities
- more iPhone-native than web-heavy platforms

Core promise:

- before you fish: know what has worked in similar conditions
- while you fish: log catches in seconds
- after you fish: keep a clean memory of trips, spots, and patterns

## Target User

Primary users are repeat anglers who fish the same waters and want private recall, not community.

Examples:

- weekend bass anglers
- inshore saltwater regulars
- kayak anglers
- fly anglers with repeat waters
- dads who want a simple private system

They care about:

- productive-condition memory
- private spot history
- fast logging
- personal progress
- confidence before the next outing

## MVP Loop

The MVP should solve one loop completely:

1. start a trip
2. capture time, location, and conditions
3. log catches quickly
4. end the trip
5. show relevant memories and patterns before the next trip

## MVP Feature Shape

### Trip Start

- select or create water / spot
- start trip timer
- capture GPS
- capture weather snapshot
- optional target species behind collapsed optional details
- optional notes behind collapsed optional details

### Catch Logging

- species
- quick species suggestions
- lure / bait
- quick lure suggestions
- save action directly in the quick-catch path
- method behind optional details
- optional photo
- optional weight
- optional length
- auto-filled time and spot
- optional note
- support for skunked trips

### History And Spots

- trip timeline
- catch gallery
- filters by water, species, season, lure
- personal bests by species
- spot detail with trip count, catch count, recent catches, successful lures, and support-gated deterministic condition summaries

### Pre-Trip Recall

- last 3 trips here
- support-gated spot recall for productivity, species, lure, catch window, seasonality, and similar conditions
- no Spot DNA summary in the current MVP state

### Privacy-Safe Shareability

- optional export-only catch share card
- one fixed card template
- one entry point only from the existing catch detail/editor surface in trip history
- offline-rendered image passed to the standard iOS share sheet
- strict allowlist content only
- no location by default
- must not create a public profile, feed, follow graph, or community surface

## Expanded MVP Feature Order

### Build Now

- keep the current coherent deterministic spot-detail recall stable
- keep the current compressed trip-start and quick-catch flows stable
- keep the current privacy-safe export-only catch share card narrow and private by default

### Build Next

- decide whether a narrow pattern replay and "last time here" memory surface is justified before implementation
- personal-best story and seasonal memory nudges
- optional catch-scan-lite logging assist that prefills fields but does not redefine the product as fish ID

### Later / Not Now

- compact Spot DNA style "what worked here" composition, unless a later pass shows it is clearly additive beyond the existing recall stack
- standalone fish photo species ID
- social or community features
- marketplace or team workflows
- broad analytics dashboards
- widgets, Live Activities, App Intents, or Apple Watch work
- regulations, licensing, or generic planning workflows

## Explicit V1 Exclusions

- public social feed
- crowd-sourced hot spots
- chat or community
- tournament tooling
- sonar integration
- standalone fish ID
- regulations database
- marketplace
- full web planner
- team features

## Product Principles

- private by default
- one-handed where possible
- photo optional, never mandatory
- default everything that can be defaulted
- no dead-end setup before first value
- basic catch entry should fit inside about 10 seconds

## Technical Direction

The founder brief recommends a local-first iOS app using:

- SwiftUI
- SwiftData or Core Data
- CloudKit sync later or behind a clear stance
- MapKit
- Core Location
- PhotosUI / camera
- WeatherKit or weather abstraction
- WidgetKit / ActivityKit / App Intents after the private-memory wedge is already working cleanly

Why local-first:

- faster perceived performance
- better offline resilience
- simpler privacy story
- lower backend cost
- a more trustworthy indie feel

## Privacy And Offline Assumptions

- spot privacy is emotionally critical
- the app should be private by default
- offline use matters on the water
- photos are optional and should stay user-controlled
- any sharing must default to privacy-safe exports rather than public discovery

## Deterministic Insights

The first insight engine should be rules-based, not generative.

Initial rules:

- top species by waterbody
- top lure by species
- best time-of-day bucket
- best month / season
- average catches per trip
- catch vs skunk rate
- similar conditions retrieval based on weather/time similarity

These rules now power a coherent spot-detail recall stack. They should not be broadened into a separate "AI insights" identity.

## Launch And Positioning

Position as a private performance companion, not a community app.

Candidate App Store framing:

- primary category: Sports
- secondary category: Reference
- screenshot story: log fast, keep spots private, remember what worked, share a win without exposing the spot

## Success Signal

North-star metric: logged trips per active angler per month.

The product should help anglers feel progress, confidence, and privacy rather than social pressure.
