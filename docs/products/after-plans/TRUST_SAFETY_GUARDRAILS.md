# Trust And Safety Guardrails: After Plans

## Why This Matters

After Plans sits close to UGC, real-world coordination, and semi-stranger interaction. Trust and safety are part of the product definition, not a later moderation add-on.

The product should feel:

- bounded
- identity-light but real
- socially useful without inviting anonymous chaos

## Product Safety Posture

- not anonymous
- not random chat
- not map-wide public discovery
- not dating framed
- not open local meetups with no context

The trust model should always favor:

- people you know
- people in the same context
- people you have planned with before

## Eligibility Assumptions

Launch posture should explicitly choose one of these before implementation starts:

- 18+ only for simpler operations and clearer review posture
- mixed-age access with stronger youth safeguards and stricter visibility defaults

Until that decision is made, product and marketing copy should avoid implying youth-focused open social discovery.

## Identity Minimums

At launch, require:

- first name
- profile photo or other visible identity cue
- verified contact method

Avoid:

- anonymous handles as primary identity
- blank-profile participation
- invisible participants in plan counts

## Visibility Guardrails

Recommended v1 visibility modes:

- same-context only
- invite-only
- known people
- friends of participants if the product proves it is needed

Guardrails:

- no public city-wide map
- no default fully public plan visibility
- no discoverability that ignores blocks or safety state

## Location Guardrails

- request location only when it improves a real workflow
- ask for `When In Use` first
- explain value before the system prompt
- avoid showing precise location more broadly than the visibility model allows

## Plan Interaction Guardrails

- `Interested` is a soft signal, not a promise
- `Join` should communicate clearer participation
- confirmation should happen inside the plan lifecycle, not through open-ended chat
- handoff to text may exist after confirmation, not before context exists

## Reporting And Blocking

Minimum launch capabilities:

- report user
- report plan
- block user
- remove blocked users from mutual visibility and participation surfaces
- preserve enough event history for moderation review

Minimum report reasons:

- harassment or creepy behavior
- hate or abusive content
- spam or fake plan
- sexual or dating misuse
- unsafe or misleading real-world behavior

## Moderation Operations

Before launch, define:

- who triages reports
- expected response window
- what actions exist: warn, hide, restrict, block, remove
- where moderation records live

Do not launch with a report button that has no real operating path behind it.

## App Review Risk Management

The app should be described as:

- a continuation app
- a join-first coordination utility
- people you know or are already around

The app should not be described as:

- meet strangers nearby
- anonymous local chat
- make friends fast
- safest way to meet people

## Claims Guardrails

Safe claim territory:

- see what is happening after
- make it easier to join
- keep the moment going
- people you know or are already around

Avoid:

- guaranteed social outcomes
- safety absolutes
- loneliness cures
- dating-adjacent innuendo

## Launch Readiness Checklist

Before seeded launch:

- visibility model is implemented and tested
- block behavior is implemented and tested
- report flow is implemented and operable
- profile realism is sufficient for trust cues
- App Store copy avoids anonymous or stranger-first framing
