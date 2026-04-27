# After Plans: Remaining Steps Before iOS Submission

Audit date: 2026-04-25 (refreshed after C1 backend landing)
Scope: audit only, no submission attempted

## Bottom Line

After Plans now has a **real backend wired end-to-end against local Supabase**.
The gap to first manual submission is materially smaller than at the prior
audit.

What exists today:

- complete continuation loop (open → forming → confirmed → active → closed)
- **51 unit tests green** on `xcodebuild test`, including a wire-level
  integration test that exercises `currentUser → suggestedContexts → feed →
  createPlan → join → confirm → markActive → wrap` against a live local
  Supabase instance
- backend contract finalized in [api/CONTRACT.md](api/CONTRACT.md), with both
  in-memory and Supabase adapters conforming to the same protocols
- local Supabase scaffold at [/infra/supabase/](/Users/simons/ai-company-os/infra/supabase/) with schema +
  RLS policies + seed; `supabase start` boots a working dev stack
- runtime backend selection via env vars in `AfterPlansConfiguration` —
  default is in-memory; flip `AFTERPLANS_BACKEND=supabase` in the scheme to
  point the app at local Supabase
- `afterplans://` URL scheme registered and deep-link join handling wired in [AfterPlansStore.swift](/Users/simons/ai-company-os/products/after-plans-ios/Sources/App/AfterPlansStore.swift)
- App icon (placeholder, on-brand) and asset catalog at [Sources/Assets.xcassets/](/Users/simons/ai-company-os/products/after-plans-ios/Sources/Assets.xcassets/)
- `AccentColor` and `LaunchBackground` colorsets matching the in-app palette
- non-empty `UILaunchScreen` configured against `LaunchBackground`
- App Store metadata drafted in [APP_STORE_METADATA_DRAFT.md](APP_STORE_METADATA_DRAFT.md)
- positioning, screenshot plan, launch plan, and trust/safety guardrails all drafted
- privacy posture clean: zero permission strings declared, no `CoreLocation` usage, onboarding copy matches behavior

What does not exist yet:

1. founder approvals on subtitle, age rating, launch contexts, and moderation operating path
2. cloud Supabase project (local stack only — production project not provisioned)
3. real screenshots from a live build on required device sizes
4. icon refinement (current icon is a placeholder; no design pass with a designer)
5. signed release archive and TestFlight build
6. legal/support URLs (privacy policy, support page)
7. App Store Connect record created and forms filled
8. manual QA pass document (Catchbook has one; After Plans does not)

## Current Readiness Assessment

### Manual submission readiness

Estimated status: **late-mid stage**

If we define "ready to submit manually" as "a human can finish the remaining Apple steps without needing more product/engineering discovery," After Plans is roughly in the **70-80% complete** range after C1.

The product artifacts and the in-app experience are real, the backend wire
path is proven against a real Postgres + Auth stack, and the submission
scaffolding (icon set, asset catalog, deep links, privacy posture) is in
place. What remains is bounded Apple-side execution (signing, screenshots,
TestFlight, App Store Connect form work) plus the four founder decisions and
a cloud Supabase provision.

### Fully agent-driven submission readiness

Estimated status: **not close yet**

If we define "ready for Codex/Claude to submit it for me" as "the system can prepare, upload, validate, and advance App Store state through approval-gated automation," After Plans is roughly in the **20-30% complete** range — same gap as Catchbook on the automation side, plus a missing backend.

## Remaining Steps Before Manual iOS Submission

### 1. Founder decisions

Why it still remains:

- the App Store lane handoff checklist in [LAUNCH_PLAN.md](LAUNCH_PLAN.md) blocks on these
- they shape copy, age rating questionnaire answers, and seeding plan

What to do:

1. approve subtitle (recommended: "Keep the moment going")
2. approve age rating (recommended: 17+)
3. approve initial seeded launch contexts
4. confirm moderation operating path — who triages reports, response window

Blocking level: **hard blocker** (some are App Store form inputs; others are operational)

### 2. Define a backend contract and ship a thin networked build — ✅ DONE (local)

Status: **complete for local dev; cloud Supabase project still to provision**

Landed in C1 (2026-04-25):

1. ✅ contract extracted to platform-neutral protocols — see
   [Sources/Services/NetworkProtocols.swift](/Users/simons/ai-company-os/products/after-plans-ios/Sources/Services/NetworkProtocols.swift)
   and [api/CONTRACT.md](api/CONTRACT.md)
2. ✅ Supabase chosen, scaffold at [/infra/supabase/](/Users/simons/ai-company-os/infra/supabase/)
3. ✅ real network adapter at
   [Sources/Services/SupabaseBackend.swift](/Users/simons/ai-company-os/products/after-plans-ios/Sources/Services/SupabaseBackend.swift),
   gated behind `#if canImport(Supabase)`
4. ✅ `InMemoryBackend` retained as the test/preview backing store
5. ✅ `AfterPlansConfiguration` flips between backends via env vars
6. ✅ full lifecycle validated against the real backend by
   [SupabaseBackendIntegrationTests.swift](/Users/simons/ai-company-os/products/after-plans-ios/Tests/Services/SupabaseBackendIntegrationTests.swift)
   (`currentUser → suggestedContexts → feed → createPlan → join → confirm →
   markActive → wrap`)

Wire-shape bugs fixed during validation:

- RLS infinite recursion (`42P17`) on `plans` ↔ `plan_participants` —
  resolved by adding three `security definer` helpers (`user_in_context`,
  `user_on_plan`, `user_can_see_plan`) and rewriting the recursive policies
- supabase-swift cached-session FK violation (`23503` on `profiles_id_fkey`)
  after `supabase db reset` — added
  `SupabaseBackendFactory.resetSessionForTesting(...)` for the test path

Still remaining for the **cloud** lane:

1. provision a cloud Supabase project (free tier is fine for v1)
2. `supabase link --project-ref <ref>` and `supabase db push`
3. add cloud URL + anon key to release-build configuration
4. confirm anonymous sign-ins are enabled and `afterplans://join` and
   `afterplans://` are added as redirect URLs in the project's auth config

Blocking level: **soft blocker for TestFlight, hard blocker for App Review**.
The local stack is sufficient to demo the loop end-to-end; a cloud project
is required for any installed-on-device validation.

### 3. Refine the app icon

Why it still remains:

- the current icon is a programmatically rendered placeholder ([AppIcon-1024.png](/Users/simons/ai-company-os/products/after-plans-ios/Sources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png))
- distinctive enough to ship, but not designer-finished

What to do:

1. either commission a designer pass or iterate the generator script (see `/tmp/afterplans_icon.py` for current source)
2. test legibility at 60pt (the smallest user-facing size)
3. test against Apple's icon guidelines (no transparency, no rounded corners, etc.)
4. re-export all sizes

Blocking level: **soft blocker** (current icon is technically submittable but the brand deserves better)

### 4. Capture real screenshots from a live build

Why it still remains:

- [SCREENSHOT_PLAN.md](SCREENSHOT_PLAN.md) has the storyboard but no actual captures
- App Store Connect requires screenshots at specific device sizes

What to do:

1. seed a demo state in the in-memory shell (or eventually the real backend) that matches each storyboard frame
2. capture from iPhone 15 Pro Max simulator (6.7") and iPhone 8 Plus or equivalent (5.5") at minimum
3. add the headline/caption overlays per `SCREENSHOT_PLAN.md`
4. export at the exact pixel dimensions Apple requires

Blocking level: **hard blocker**

### 5. Stand up legal and support URLs

Why it still remains:

- App Store Connect requires `support_url` and `privacy_url`
- neither exists for After Plans yet

What to do:

1. write a one-page privacy policy reflecting the current data posture (now much simpler — no location, light identity)
2. write a support page or an email-only support contact
3. host both at stable URLs (could be a single static site)
4. add the URLs to [APP_STORE_METADATA_DRAFT.md](APP_STORE_METADATA_DRAFT.md)

Blocking level: **hard blocker**

### 6. Configure signing and produce a release archive

Why it still remains:

- the project has no signing configured for a release build
- bundle id `io.aicompanyos.products.afterplans` is reserved in `project.yml` but not registered in App Store Connect

What to do:

1. create the App ID `io.aicompanyos.products.afterplans` in the Apple Developer portal
2. open `products/after-plans-ios/AfterPlans.xcodeproj`
3. enable automatic signing for the AfterPlans target
4. choose the Apple Developer team
5. produce a Release archive
6. confirm it is uploadable to App Store Connect

Blocking level: **hard blocker**

### 7. Upload to TestFlight and run device QA

Why it still remains:

- no TestFlight build has ever been produced
- there is no manual QA pass document yet (Catchbook has one; After Plans does not)

What to do:

1. write `manual-qa-pass.md` for After Plans following the Catchbook pattern
2. upload the archive from Xcode
3. install via TestFlight on a real device
4. walk through the QA scenarios with at least one second person to validate the join/confirm flow
5. record results, fix issues, re-archive if needed

Blocking level: **hard blocker**

### 8. Complete the App Store Connect form work

Why it still remains:

- the App Store Connect record does not exist yet for After Plans

What to do:

1. create the app record in App Store Connect with bundle id `io.aicompanyos.products.afterplans`
2. complete the age rating questionnaire (per founder decision in step 1)
3. complete the content rights declaration
4. complete the App Privacy nutrition labels (now simpler — see the App Privacy section below)
5. confirm pricing (free) and availability
6. upload screenshots from step 4
7. paste in finalized metadata fields from [APP_STORE_METADATA_DRAFT.md](APP_STORE_METADATA_DRAFT.md)
8. paste in the review notes
9. seed a demo/test account for App Review

Blocking level: **hard blocker**

### 9. Final submission review pass

Why it still remains:

- no end-to-end checklist has been run against the live App Store Connect record

What to do:

1. verify everything in this doc is closed out
2. verify the latest build/version number to submit
3. confirm no last-minute regressions after TestFlight
4. only then move to "Add for Review" and "Submit to App Review"

Blocking level: **hard blocker before actual submission**

## App Privacy Nutrition Label — Updated Posture

After the privacy cleanup pass on 2026-04-25, the live data posture is:

- **no location** — `NSLocationWhenInUseUsageDescription` removed; no `CoreLocation` usage
- **no contacts, photos, mic, camera, motion** — none requested or used
- **light identity only** — first name and a few text-entered context cues
- **user-generated content** — plan titles, plan descriptions, optional notes
- **report content** — report reasons + freeform text submitted to moderation

This is materially simpler than the draft labels in [APP_STORE_METADATA_DRAFT.md](APP_STORE_METADATA_DRAFT.md) and should be re-derived from the actual shipping build, not from the early draft.

## Remaining Work Before Codex Or Claude Can Submit After Plans End-To-End

Same gap pattern as Catchbook:

### 1. Backend contract + real services

After Plans is uniquely blocked here — Catchbook already has a real Core Data backing store. After Plans needs a backend chosen and wired before any release-automation discussion is meaningful.

### 2. Real archive/export automation

Same as Catchbook: deterministic archive command, export configuration, artifact capture, failure handling.

### 3. Real App Store Connect integration

Shared infrastructure with Catchbook — once `packages/tools/appstore_tools/asc_api.py` is real, both products benefit.

### 4. Approval-gated irreversible actions

Shared with Catchbook — same approval policy, same gating requirements.

### 5. Machine-readable release artifact completeness

After Plans has no checkpoint state at all yet for releases. Cleaner starting point than Catchbook (no stale `fishing-logbook`-style identity drift), but it does need to be created from scratch.

### 6. Review-status monitoring and rejection handling

Shared with Catchbook.

## Recommended Sequence From Here

If the goal is **submit After Plans soon**:

1. founder decisions (subtitle, age rating, contexts, moderation)
2. backend contract definition + thin networked build
3. icon refinement
4. real screenshots from the networked build
5. legal/support URLs
6. signing + release archive
7. TestFlight + device QA
8. App Store Connect form work
9. final review pass and submit

The single biggest item is the backend contract — without it, every later step is provisional.

If the goal is **eventually submit through Codex or Claude**:

1. land the manual submission once
2. then share automation work with Catchbook (archive/export, ASC API, approval gating, release verification)

## Comparison Snapshot — Catchbook vs After Plans

| Area | Catchbook | After Plans |
| --- | --- | --- |
| Manual submission readiness | 80-90% | 70-80% |
| Backend wired | yes (Core Data) | yes (Supabase, local; cloud TBD) |
| App icon | shipping-quality | placeholder |
| Screenshots captured | yes (6.7" + 6.5") | no |
| Privacy strings | location, weather (real) | none (clean) |
| Founder decisions outstanding | none | 4 |
| Signed archive ever produced | no | no |
| TestFlight build | no | no |
| Privacy/support URLs | drafted | not yet |

## Practical Answer

After Plans is **not yet close to first manual submission**. The MVP shell is real and the submission scaffolding is in place, but the backend gap and the four founder decisions sit on the critical path. With those resolved, the remaining work is well-scoped and largely Apple-side execution.

It is **not yet close to hands-off autonomous submission** either, for the same reasons as Catchbook plus the missing backend.
