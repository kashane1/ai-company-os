---
title: After Plans context model — user-built contexts, public plans, closeness graph
type: brainstorm
status: complete
date: 2026-04-27
participants:
  - Kashane (founder)
  - Claude Opus 4.7 (1M context)
---

# After Plans context model brainstorm

## Why we brainstormed

The pre-launch audit listed "initial seeded launch contexts" as one of four
founder decisions blocking submission. The founder pushed back on
pre-seeding — it bottlenecks on personally vouching for each context and
doesn't scale past launch week. Triggered an exploration of a user-built
context model that may replace pre-seeding entirely.

## Decisions reached

1. **Two-factor model for the social graph.**
   - Factor 1 (visibility): bounded by direct context membership only. No
     visibility expansion through social degrees.
   - Factor 2 (closeness ranking): server-side closeness score from plan
     history (1st-degree = co-confirmed) + invite chains. 2nd-degree
     drives recommendations only, never visibility.

2. **PlanVisibility collapses to three live values.** Add `public` (Swift
   ident: `publicMatch` because `public` is reserved), keep
   `same_context_only` and `invite_only`, remove `known_people` and
   `friends_of_participants` (closeness ranking lives outside visibility).

3. **Onboarding becomes multi-step.** Existing 5-card carousel kept;
   adds first-name capture (required), privacy-mode selection (two
   options), activity+venue picker, optional invite-code entry.

4. **Activity taxonomy is founder-curated, ~30+ entries**, ships in the
   build, includes both specific (basketball) and broad (sports) entries.
   Optional one-level `parent_activity_id` nesting. Used for
   recommendations only; context membership matching stays exact-match.

5. **Venue model uses Apple MKLocalSearch.** No third-party SDK, no API
   key, no location permission required (we search venue addresses, not
   the user's location). Schema gains `latitude`, `longitude`,
   `apple_place_id`. Match by Place ID first, lat/lng-within-30m fallback
   only for geocoded venues. Freeform venues allowed but never
   auto-merge.

6. **Plan creation = three visibility paths.**
   - `same_context_only`: pick a context the user is already in.
   - `invite_only`: no extra required fields.
   - `public`: requires activity+venue selection.
   Plan modes (`default_option`/`open_intent`/`exact`) unchanged.

7. **Lifecycle: closeness graph signal at `confirmed`** (not at join),
   wrap is single-key (any host or participant). The two-person guardrail
   moves to the auto-context-spawn rule, not the wrap rule.

8. **Auto-context formation from wrapped public plans.**
   Trigger: public plan transitions to `closed` AND has ≥2 unique
   confirmed participants. Smart merge: Apple Place ID first, lat/lng-30m
   fallback. Time/day pattern is NOT a context dimension in v1.
   Declared-interest rows matching the new context get converted to
   `context_members`.

9. **Closeness graph computed on the fly** via recursive SQL on
   `plan_participants where lifecycle = confirmed`. 1st and 2nd degree
   only; 3rd skipped. Optimize to denormalized table only if/when feed
   latency demands it.

10. **Recommendation surfaces.** Post-wrap "did you know" card,
    co-invite suggestion at plan creation, onboarding bootstrap via
    invite chain, "friends of friends frequent" prompt in activity-picker.

11. **Push notifications (server-side):** match-on-public-plan,
    plan-joined, lifecycle-change, auto-context-membership.

12. **Privacy posture update.** Privacy policy + nutrition labels gain
    "Venue addresses associated with plans you create or join" under
    "User content," not "Location." Re-confirm we don't request user
    device location.

13. **Plan timing remains free-text** (the after-something-ended
    semantics imply social-context timing, not scheduling).

## Alternatives considered and rejected

| Alternative | Why rejected |
|---|---|
| **Pre-seed 3–5 launch contexts** | Bottlenecks on founder personally vouching. Doesn't scale. Preserved as a fallback in [founder-decisions-needed.md §3](../products/after-plans/founder-decisions-needed.md). |
| **3-tier privacy: strangers / contacts / 1st-2nd-3rd-degree friends** | Too complex for v1. Phone-contacts integration would flip the privacy posture (currently "no contacts"), require new App Review prep, and the implementation needs on-device hashing à la Signal. Two tiers (default / strict) achieve ~90% of the value without changing the data posture. |
| **Phone-contacts as a Factor 2 closeness signal** | Same posture issue as above. Deferred to v1.1 as opt-in. v1 closeness derives from plan-history + invite-chain only. |
| **3rd-degree connections in the closeness graph** | Signal-to-noise drops fast past 2nd-degree (LinkedIn knows this). 3rd-degree also makes the bounded-visibility promise hard to defend. |
| **Visibility expansion through degrees** ("you planned with Maya, so now you see all 14 of her contexts") | Rebuilds an open public-feed surface — exactly what we don't want. Degrees power *recommendations* (which the user opts into), never visibility. |
| **Activity = context (one selector)** | An activity (basketball) and a context (Tuesday pickup at Westside) are different. Two basketball-at-the-gym people who go to different gyms aren't sharing a context — they share an interest. Resolved with activity+venue combo as the context identity. |
| **Anyone-types-anything venue entry** | Worst de-dup outcome ("Westside Court" / "westside court" / "basketball westside" all coexist). Adopted Strava+Google-Maps style: closed activity taxonomy + freeform venue typeahead with structured matching. |
| **Time/day pattern as a third context dimension** | Wednesday-morning vs Saturday-afternoon runners are different communities, but adding time-of-day to context identity adds onboarding complexity and most users won't reliably enter it. v1 merges; revisit in v2 if feed-noise complaints come in. |
| **Two-key wrap** (≥2 distinct participants must each tap "wrap") | Adds friction. Confusing UX ("why is the plan still active?"). Decided: single-key wrap, but the two-person check moves to the auto-context-spawn rule, where it actually matters. |
| **Mapbox / Google Maps for geocoding** | Paid after free tier; adds third-party SDK + API key management; data-sharing concerns. Apple MKLocalSearch is free, native, no key, no location permission required. |

## Open questions deferred to v2

- **Phone-contacts + social-graph linking** as additional Factor 2 inputs.
  Reassess when v1 has signal on whether plan-history + invite-chain
  alone is dense enough.
- **Sub-context splitting by time/day pattern.** Wait for feed-noise
  complaints from large auto-formed contexts.
- **Denormalized `closeness_scores` table.** Compute on the fly in v1;
  add when feed-load latency demands it.
- **Cloud Supabase project provisioning** (out of scope for this
  refactor; tracked separately). Privacy policy gets a region note when
  the cloud project is created.
- **TestFlight + App Store screenshots + signing** (separate slice).

## What this brainstorm produced

- This document.
- The implementation plan at
  [docs/plans/2026-04-27-001-feat-after-plans-context-model-refactor-plan.md](../plans/2026-04-27-001-feat-after-plans-context-model-refactor-plan.md).
- A founder-decisions update marking the launch-contexts decision as
  deferred pending this brainstorm
  ([founder-decisions-needed.md §3](../products/after-plans/founder-decisions-needed.md)).
