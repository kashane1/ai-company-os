# Launch Plan: After Plans

## Launch Objective

Run a seeded launch that proves the continuation loop in a few dense, recurring contexts before broadening distribution or monetization.

## Launch Stages

### Stage 1: Internal Clarity

Deliverables:

- finalized MVP scope
- trust and safety posture
- App Store positioning draft
- initial lane packets

Exit condition:

- the team can describe the product in one sentence and defend what is out of scope

### Stage 2: Seeded Context Preparation

Deliverables:

- target launch contexts selected
- organizer or ambassador outreach materials drafted
- screenshot and metadata direction prepared
- moderation operating assumptions documented

Exit condition:

- at least a small number of launch contexts are intentionally chosen and instrumented

### Stage 3: Seed Launch

Deliverables:

- live iPhone build
- App Store metadata ready
- founder-led seeding in selected contexts
- measurement plan active

Exit condition:

- real users convert post-activity moments into confirmed plans

### Stage 4: Learning And Tightening

Deliverables:

- review of conversion and repeat-use metrics
- ranked list of product friction points
- recommendation on whether to deepen ranking, venue suggestions, or organizer tooling next

Exit condition:

- one clear improvement path is chosen without widening scope

## Go / No-Go Checks

Go only if:

- the core flow is understandable in one use
- safety actions work
- bounded visibility is real
- App Store framing avoids anonymous or dating confusion
- the product has at least one credible seeded-context distribution plan

No-go if:

- the app feels like a generic social feed
- confirmation flow depends on unbuilt chat
- moderation is only theoretical
- launch depends on a hard consumer paywall

## App Store Lane Handoff Checklist

This checklist defines what must be done before the App Store lane can execute. Items marked with source docs can be found in the referenced artifacts.

### Founder Decisions Required

- [ ] approve subtitle — recommended "Keep the moment going" (see APP_STORE_POSITIONING.md)
- [ ] approve age rating — recommended 17+ (see APP_STORE_POSITIONING.md, TRUST_SAFETY_GUARDRAILS.md)
- [ ] approve launch contexts — which communities/groups get seeded first
- [ ] confirm moderation operating path — who triages reports, response window

### Artifacts Ready For Use

- [x] App Store description drafted (APP_STORE_METADATA_DRAFT.md)
- [x] Keywords drafted (APP_STORE_METADATA_DRAFT.md)
- [x] Promotional text drafted (APP_STORE_METADATA_DRAFT.md)
- [x] Review notes drafted (APP_STORE_METADATA_DRAFT.md)
- [x] Screenshot storyboard with per-screenshot specs (SCREENSHOT_PLAN.md)
- [x] Privacy label mapping started (APP_STORE_METADATA_DRAFT.md)
- [x] "What this is not" framing documented (APP_STORE_POSITIONING.md)

### Artifacts Still Needed Before Submission

- [ ] support URL live (landing page or simple support site)
- [ ] privacy policy URL live
- [ ] marketing URL (optional, recommended)
- [ ] app icon finalized at required export sizes
- [ ] screenshot captures from live build on required device sizes
- [ ] demo/test account created and seeded for App Review
- [ ] privacy labels finalized against actual data collection in the shipping build
- [ ] contact information for App Store Connect filled in

### Build Prerequisites

- [ ] backend contract defined (currently in-memory shell)
- [ ] shipping build with real networking layer
- [ ] TestFlight build validated
- [ ] build uploaded to App Store Connect via Xcode or Transporter

## Founder Checklist

- approve launch contexts
- approve age and eligibility stance
- approve App Store subtitle and screenshot story
- confirm moderation operating path
- confirm seeded outreach materials
