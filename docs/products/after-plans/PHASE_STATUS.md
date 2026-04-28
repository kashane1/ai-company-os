# After Plans Phase Status

## Current Phase

Phase 7 is in progress. The C1 backend slice landed on 2026-04-25: the
SupabaseBackend adapter is now proven against a live local Postgres + Auth +
RLS stack, with a wire-level integration test gating the full lifecycle.

Phase 6 (the v1 continuation-loop MVP) is complete.

Phases 0 through 5 are complete. Phase 6 includes the known-people ranking refinement, a lifecycle-state clarity pass across Home/detail/confirmation, a tighter invite/share-to-join scaffolding pass, and a trust/safety visibility refinement inside the active loop.

## Completed Phases

- Phase 0: inspected repo conventions, inspected the founder package, chose the `after-plans` slug and `products/after-plans-ios` source root, created resumability artifacts, and logged the assessment
- Phase 1: bootstrapped the After Plans product workspace, normalized the founder package into repo-native docs, created core product docs, updated the product registry, and reserved the managed iOS source root
- Phase 2: derived the implementation-ready artifact chain for product, iOS, trust/safety, App Store, GTM, launch, and backlog work
- Phase 3: created bounded task packets for supervisor, iOS, trust/safety, App Store, and GTM work
- Phase 4: bootstrapped the managed iOS source tree, added the XcodeGen project definition, built a compile-safe SwiftUI shell, scaffolded the continuation loop with in-memory state, and added lane-matching unit tests
- Phase 5: completed the first continuation-loop deepening pass with focused-plan carry-forward, tighter Home/Create/Detail/Confirmation wiring, additional lane-matching tests, and a previously successful full simulator-backed test run

## Blocked Phases

- no product phase is currently blocked by a confirmed repo-local defect
- simulator-backed validation is currently healthy in this repo state after a minimal simulator reboot and exact reruns of the After Plans test commands

## Active Phase Notes

- Phase 6: added `PlanAffinity` as a narrow derived-state helper so same-context, known-people, repeat-context, and meaningful host-memory cues can influence ranking without widening the architecture
- Phase 6: Home discovery cards now show trust-oriented badges and a social-memory explanation line so the feed reads more like "people you know or were just around" and less like a generic list
- Phase 6: focused tests now cover the new ranking preference and host-memory filtering
- Phase 6: lifecycle semantics are now explicit in the model layer, including step labels, state-window copy, confirmation-room action mapping, and suppression of misleading active/closed actions
- Phase 6: Home, plan detail, and confirmation now render the lifecycle state more consistently with shared badge/progress UI and state-specific helper copy
- Phase 6: confirmation can now advance a plan from confirmed to active in the in-memory shell so lifecycle maturity feels intentional instead of static
- Phase 6: a minimal simulator reboot followed by a targeted rerun closed the prior validation question, and the exact full `xcodebuild test` command now completes successfully again
- Phase 6: `xcodegen generate` was rerun after adding a new shared UI source file so the generated project stayed in sync
- Phase 6: invite/share now has lifecycle-aware gating, low-pressure join framing, bounded audience guidance, and an in-memory prepared-share state so the handoff feels like continuation scaffolding instead of generic messaging
- Phase 6: Plan detail and confirmation now expose clearer share entrypoints only when a plan is still sensible to share, while active and closed plans stop advertising invite actions
- Phase 6: focused model/store tests now cover invite availability, low-pressure framing, and one in-memory path from the current loop into the invite/share surface
- Phase 6: plan detail, invite/share, confirmation, and the safety center now make bounded visibility more explicit with inline “who can see this” and “why this is not public” explanations
- Phase 6: safety access is now surfaced more directly from existing plan screens with calm report/block guidance instead of relying only on a toolbar icon
- Phase 6: active and closed plans now keep trust/safety messaging visible while avoiding misleading “still live” visibility posture
- Phase 6: targeted model/store validation for the trust/safety visibility slice is green, so a redundant full-scheme rerun was intentionally skipped this pass
- Phase 6: Home discovery cards, Plan Detail, and Confirmation Room now surface join-confidence and lifecycle-clarity cues (`joinConfidenceCue`, `readinessHint`, `confirmationDisabledReason`) so users can gauge readiness and feel informed without pressure
- Phase 6: full scheme rerun green at 33 tests, 0 failures after the join-confidence cues slice
- Phase 6: Activity surface now functions as a lightweight recap/social-memory feed with `RecapSummary` (follow-through count, repeat-context detection, warm headline/detail copy), `recapLine` on closed plans, recent-partners chip row, and affinity badges on history entries
- Phase 6: full scheme rerun green at 37 tests, 0 failures after the recap/social-memory slice
- Phase 6: added `wrapPlan` lifecycle action so active plans can be closed by the user, completing the full Open → Forming → Confirmed → Active → Closed loop
- Phase 6: Plan Detail and Confirmation Room now surface "Wrap this plan" for active plans where the user has joined or confirmed
- Phase 6: full scheme rerun green at 39 tests, 0 failures after the wrap-lifecycle slice
- Phase 6: added handoff-to-text affordance on confirmed and active plans in the Confirmation Room so the core loop has a credible exit to real-world coordination via Messages
- Phase 6: full scheme rerun green at 41 tests, 0 failures after the handoff-to-text slice
- Phase 7 (C1 backend): platform-neutral contract finalized in `docs/products/after-plans/api/CONTRACT.md`; async `NetworkProtocols.swift` + `AfterPlansBackend` bundle landed; `InMemoryBackend` actor added so existing tests keep using the in-memory path; `AfterPlansStore` consumes the bundle and view actions are `async`
- Phase 7 (C1 backend): local Supabase scaffold at `infra/supabase/` with `config.toml`, `migrations/0001_init.sql`, and `seed.sql`; `supabase-swift` SPM package linked in `project.yml`; `SupabaseBackend.swift` adapter implements identity (anonymous bootstrap), contexts, plan feed/get/create/join/expressInterest/suggestPlace/confirm/markActive/wrap, invite preview/resolve/recordShare, reports, blocks
- Phase 7 (C1 backend): `AfterPlansConfiguration` reads `AFTERPLANS_BACKEND` / `AFTERPLANS_SUPABASE_URL` / `AFTERPLANS_SUPABASE_KEY` to switch between in-memory and Supabase at runtime; default remains in-memory so unit tests stay deterministic
- Phase 7 (C1 backend): `SupabaseBackendIntegrationTests` exercises the full lifecycle (`currentUser → suggestedContexts → feed → createPlan → join → confirm → markActive → wrap`) against a live local Supabase, gated by env vars and skipped cleanly when absent; idempotent across reruns
- Phase 7 (C1 backend): two wire-shape bugs surfaced and fixed during validation — RLS infinite recursion (`42P17`) on `plans`/`plan_participants`/`plan_place_suggestions` resolved by introducing three `security definer` helpers (`user_in_context`, `user_on_plan`, `user_can_see_plan`) and rewriting the recursive policies; supabase-swift cached-session FK violation (`23503`) on `profiles_id_fkey` after `db reset` resolved by adding `SupabaseBackendFactory.resetSessionForTesting(...)` invoked from the test's `setUp`
- Phase 7 (C1 backend): manual UI walkthrough on iPhone 17 Pro simulator (iOS 26.4) confirmed the live wire path through onboarding, anonymous auth bootstrap, contexts query, and feed query against the local Supabase stack; createPlan-via-UI was blocked by a Simulator/computer-use input quirk (long-press accent intercept), not a backend bug — the same operations are fully covered by the green integration test
- Phase 7 (C1 backend): full scheme rerun green at 51 tests, 0 failures (50 in-memory + 1 Supabase integration)

## Locked Decisions

- product slug: `after-plans`
- registry entry added in `infra/products.json`
- docs root: `docs/products/after-plans`
- managed source root: `products/after-plans-ios`
- v1 wedge: post-activity continuation
- trust posture: bounded context, non-anonymous, report/block/moderation from day one
- monetization posture: free consumer core in v1, organizer/community premium later
- iOS shell pattern: XcodeGen project plus SwiftUI shell with in-memory services before any backend work

## Current Source-Of-Truth Artifacts

- `README.md`
- `FOUNDER_BRIEF.md`
- `PRODUCT_BRIEF.md`
- `PRD.md`
- `MVP_SPEC.md`
- `SCREEN_MAP.md`
- `DATA_MODEL.md`
- `IOS_ARCHITECTURE.md`
- `TRUST_SAFETY_GUARDRAILS.md`
- `APP_STORE_POSITIONING.md`
- `APP_STORE_METADATA_DRAFT.md`
- `SCREENSHOT_PLAN.md`
- `GTM_PLAN.md`
- `LAUNCH_PLAN.md`
- `TASK_BACKLOG.md`
- `task-packets/`
- `OPEN_QUESTIONS.md`
- `PHASE_STATUS.md`
- `RESUME_PROMPT.md`
- `state/artifacts/after-plans/codex-append-log.md`
- `products/after-plans-ios/README.md`
- `products/after-plans-ios/project.yml`
- `products/after-plans-ios/Sources/`
- `products/after-plans-ios/Tests/`

## Next Recommended Phase

Phase 7 (C1 backend) is in progress; the local-Supabase wire path is proven.
Remaining items in Phase 7 / before submission are tracked in
[remaining-steps-before-ios-submission.md](remaining-steps-before-ios-submission.md).

Phase 6 is complete. The v1 continuation-loop MVP is complete.

All "Must Ship" items from MVP_SPEC.md are implemented. All PRD core loop steps have working affordances. All MVP Release Criteria are satisfied. The "Should Follow Soon" items were implemented ahead of schedule during Phase 6.

### App Store Positioning Pass: Complete

The App Store positioning and launch-prep artifact pass has been completed. Artifacts are now execution-ready:

- APP_STORE_POSITIONING.md — tightened with decided subtitle, messaging hierarchy, age rating recommendation, full description draft, keyword set, review notes, privacy labels, and "what is not" framing
- APP_STORE_METADATA_DRAFT.md — new, field-by-field draft ready to copy into App Store Connect
- SCREENSHOT_PLAN.md — new, per-screenshot storyboard with screen mappings, headlines, captions, design direction
- LAUNCH_PLAN.md — updated with concrete App Store lane handoff checklist

### Next lanes (in recommended priority)

1. **Founder decisions** — subtitle, age rating, and launch context approvals (see LAUNCH_PLAN.md handoff checklist)
2. **Backend contract definition** — move past the in-memory shell
3. **Seeded launch prep** — select target contexts, draft organizer outreach
4. **App Store lane execution** — screenshots, icon, build, submission (blocked by founder decisions and backend)

Do not continue adding in-app slices unless a clear gap is identified in a fresh review.
