# MVP Spec: After Plans

## MVP Goal

Prove that people who just finished a real-world activity will open After Plans, see relevant next-step options, and convert one into a confirmed continuation.

## MVP Promise

Make the next plan easier right after the current one ends.

## Must Ship

### Core Product Loop

- fast onboarding with lightweight identity
- context selection for what just happened
- ranked discovery feed
- exact plan, default option, and open intent creation
- join, interested, and suggest place actions
- visible momentum counts
- plan state progression from Open to Closed
- share link and QR invite flows
- report and block flows
- bounded visibility defaults

### Day-One Trust Layer

- non-anonymous participation
- visibility constrained by context or invite path
- report a plan
- report a user
- block a user
- moderation queue assumption documented
- clear permission timing for location

### Day-One Product Story

- "see what is next after"
- "join with one tap"
- "start what is next your way"
- "people you know or are already around"

## Should Follow Soon After MVP

- known-people ranking refinement
- prior plan partner ranking
- suggested nearby venues
- on-my-way and running-late execution polish
- recurring context memory and recap surfaces

## Explicitly Out Of Scope

- map-wide discovery
- anonymous chat
- DMs before plan context exists
- payments
- ticketing
- large-group hosting
- organizer CRM
- hard consumer paywall

## Launch Constraints

- keep the first implementation focused on continuation after a shared activity
- do not widen into a general social app
- do not require community admin tools to prove the core loop
- do not require a broad backend platform before defining the client contracts cleanly

## MVP Release Criteria

The MVP is ready for the first seeded launch when:

- a new user can onboard in minutes
- the app can represent context, plans, participation, and visibility states cleanly
- discovery cards reveal enough trust cues without overexposing data
- share and QR flows support bounded invites
- report and block flows are testable
- the screen map supports the full continuation loop without dead ends
- App Store positioning clearly avoids dating and anonymous meetup framing

## Core Metrics

- percent of users who reach a feed after onboarding
- percent of viewed plans that receive `Join` or `Interested`
- percent of created plans that reach `Confirmed`
- repeat confirmed after-plans per active user
- share or QR invite conversion
- reports per active plan and resolution time

## Failure Conditions

The MVP should be considered not ready if:

- the app mostly requires users to create plans rather than join them
- the feed looks like open public discovery
- safety controls are superficial or buried
- trust cues are too weak to counter stranger-meetup assumptions
- monetization creates participation friction
