# PRD: After Plans

## Product Purpose

Reduce awkwardness and coordination friction in the short window between one real-world activity ending and the next plan forming.

## Product Definition

After Plans is an iPhone-first continuation app that helps users:

- see what is happening next after a shared activity
- signal interest without overcommitting
- join a next plan with low friction
- move a loose social moment toward confirmation

The product is not:

- a dating app
- a broad social network
- a public event marketplace
- an anonymous chat product
- a group-chat replacement

## Primary User

The core user is socially open but more comfortable joining than initiating. They often leave dinners, meetups, classes, conferences, or hangouts with partial momentum and weak coordination.

## Core Jobs To Be Done

1. See what is happening after this.
2. Quietly signal "I'm in" without writing the first awkward text.
3. Join something already forming.
4. Turn weak intent into a confirmed next plan.
5. Keep a good moment going with bounded trust.

## Product Principles

- shared context beats cold-start discovery
- joining is easier than creating
- soft signals come before hard commitment
- the app owns discovery and formation, not last-mile chatter
- known people and same-context people outrank strangers
- bounded visibility beats broad public discovery
- trust and moderation are product requirements, not launch polish

## Core Loop

1. a real-world activity ends
2. the user opens After Plans
3. the user selects or confirms current context
4. the user sees ranked next-plan cards or starts one
5. participants join, signal interest, or suggest a place
6. one option confirms
7. the group continues offline, with optional handoff to text

## MVP User Flows

### Discover And Join

1. user exits an activity
2. app anchors them to a recent or selected context
3. discovery feed shows relevant after-plans
4. user taps `Join` or `Interested`
5. plan gains visible momentum
6. plan reaches confirmed state

### Create A Continuation Plan

1. user taps `Start what's next`
2. user chooses exact plan, default option, or open intent
3. plan publishes to bounded audience
4. others join or signal interest
5. organizer or the group converges on confirmed next step

### Invite Same-Context People

1. user shares a plan through QR, deep link, or in-app invite
2. recipient sees a lightweight preview
3. recipient joins or installs the app
4. the plan remains bounded to context and visibility rules

## MVP Functional Requirements

### Identity And Account

- lightweight profile with first name, photo, and optional context cues
- identity-light but not anonymous
- enough profile realism to support trust and App Review posture

### Context And Relevance

- users can anchor the app to what they just did
- current context can come from user selection first; richer inference can come later
- ranking favors same-context, known people, prior plan partners, time relevance, and momentum

### Plan Creation

- three creation modes:
  - exact plan
  - default option
  - open intent
- creation must be fast enough to use in the moment
- visibility must be chosen or defaulted safely

### Discovery Feed

- feed ranks by context, familiarity, time, distance, and momentum
- public map-wide discovery is out of scope
- the feed should show enough information to judge safety and relevance without overexposing location

### Participation Actions

- `Join`
- `Interested`
- `Suggest place`
- visible participant counts and lightweight social proof

### Plan Lifecycle

- Open
- Forming
- Confirmed
- Active
- Closed

State changes must be visible and legible so users understand whether something is still forming or worth committing to.

### Safety And Trust

- report a user
- report a plan
- block a user
- bounded visibility controls
- moderation review path
- clear identity and permission posture

### Invites

- deep link flow
- QR flow
- share preview that does not expose more than the visibility model allows

## Out Of Scope For MVP

- public city-wide feed
- anonymous chat
- open-ended DMs before plan context exists
- payments or ticketing
- large event-hosting workflows
- organizer CRM
- full community management suite
- broad follower graph

## Non-Functional Requirements

- iPhone-first UX
- low-friction onboarding
- permissions asked only when useful
- bounded visibility by default
- reviewable safety controls from day one
- implementation must preserve lane boundaries between iOS and App Store work

## Analytics Requirements

Track at minimum:

- signup completed
- context selected
- plan created
- plan type selected
- plan viewed
- join tapped
- interested tapped
- suggest place tapped
- plan confirmed
- plan closed
- qr opened
- share link opened
- install from share
- handoff to text
- report submitted
- block user
- repeat plan with same people

## MVP Success Signals

- users open the app after real activities
- users find relevant continuation options quickly
- a meaningful share of plans move from forming to confirmed
- repeat use appears in recurring contexts
- the app does not drift into stranger-meetup or dating framing
