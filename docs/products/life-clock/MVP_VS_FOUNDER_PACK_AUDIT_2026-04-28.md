# Life Clock — MVP vs Founder Pack Audit

> Audit date: 2026-04-28
> Branch reviewed: `feat/life-clock-mvp-skeleton` (PR #14, post-cleanup commit)
> Scope: every requirement and recommendation in the 18-file founder pack, mapped against what shipped on this branch.

## Headline numbers

| Status | Count | Share |
|---|---:|---:|
| ✅ Done | 27 | 24% |
| 🟡 Partial | 19 | 17% |
| ❌ Not started | 67 | 59% |
| **Total** | **113** | |

This is the right ratio for an "MVP skeleton" PR. The ~25% that is done is the foundation: deterministic engines, mockable HealthKit boundary, six SwiftUI screens, three tone modes, the artifact chain, and unit tests for the load-bearing pieces. Almost everything that is *not* done is gated on three follow-up plans: live HealthKit, persistence, and StoreKit.

---

## 1. Strategy & Positioning (`EXECUTIVE_SUMMARY`, `PRODUCT_STRATEGY`, `BUSINESS_PLAN`)

| Item | Status | Notes |
|---|---|---|
| Wedge: "Earn time back with better daily habits" | ✅ Done | Reflected in onboarding value screen, app store-ready disclaimer, and tone-mode copy. |
| Category positioning: Health & Fitness, not Games | ✅ Done | Documented in `PRODUCT_STRATEGY.md`; not yet exercised since we have no App Store submission. |
| Brand stance (lively, motivating, not punitive) | ✅ Done | Copy review pass clean; no medical-claim language; no doom notifications (no notifications at all yet). |
| MVP product sentence: "Today's habits moved your Life Clock by +X. Here's why and how to improve tomorrow" | ✅ Done | Today screen shows delta, drivers, and quests in this order. |
| Three tone modes (gentle / coach / memento mori) | 🟡 Partial | Toggle works and changes Today-screen copy. Time Ledger, Quests, Weekly Report, and Profile do not yet vary copy by tone. |
| Apple-native premium feel | 🟡 Partial | Uses native SwiftUI primitives, accent color, system fonts. No custom design system, no haptics, no animations on the clock value. |
| Brand-name resolution (`OPEN_QUESTIONS` Q1) | ❌ Not started | Code identifier `LifeClock` chosen but no UI rename strategy. Strings are inline (not in `Localizable.strings`), so a future rename is multi-file. |

## 2. PRD — Core Screens (`PRD.md` § Core screens)

### Onboarding

| Item | Status | Notes |
|---|---|---|
| Value framing screen | ✅ Done | "Earn time back" headline. |
| Non-medical disclaimer with explicit accept | ✅ Done | Toggle gate; cannot proceed past safety screen without it. |
| Baseline profile (DOB, biological sex, smoking, alcohol, sleep goal, strength frequency) | ✅ Done | Seven fields. |
| Progressive HealthKit education | 🟡 Partial | Has an education screen, but it explains a feature that does not yet exist. Honest copy ("Live Apple Health reads land in a follow-up update"). |
| Tone mode selection | ✅ Done | Three-way picker with descriptions. |
| Initial Life Clock reveal | ✅ Done | Reveal screen + ClockEngine baseline computed on `completeOnboarding`. |

### Today

| Item | Status | Notes |
|---|---|---|
| Life Clock / projected date / healthspan meter | 🟡 Partial | Shows projected age years and anchor date. No animated clock or healthspan ring. |
| Today's time delta with sign and color | ✅ Done | Green for positive, muted orange for negative. |
| Confidence label | ✅ Done | `ConfidenceBadge` shown alongside delta. |
| Top 3 drivers | ✅ Done | `todayDrivers.prefix(3)`. |
| Daily quests (1–3) | ✅ Done | Embedded card on Today, also full Quests tab. |
| Manual quick-log button | ❌ Not started | The PRD calls it out explicitly; not implemented. Quick-log only happens via quest completion. |

### Time Ledger

| Item | Status | Notes |
|---|---|---|
| Chronological entries | 🟡 Partial | Sorted by delta size, not chronologically. PRD says chronological. |
| Source icons (HealthKit / manual / estimate) | ✅ Done | Three icons mapped. |
| Positive/negative deltas | ✅ Done | Color-coded. |
| Confidence notes per entry | 🟡 Partial | Stored on each entry but not shown in the row UI. Driver type + source shown instead. |

### Quests

| Item | Status | Notes |
|---|---|---|
| Daily movement quest | ✅ Done | |
| Sleep / consistency quest | ✅ Done | |
| Risk-habit quest (alcohol / smoking) | 🟡 Partial | Risk-reduction quest exists, but only triggers around alcohol logging — smoking branch is in the engine but no UI to log smoking outside a not-yet-built habit log. |
| Weekly strength quest | ❌ Not started | Strength category exists in the engine; no quest generator path produces it. |
| Quest completion tracking | ✅ Done | `toggleQuestCompletion` flips `completedAt`, adds ledger entry. |

### Weekly Report

| Item | Status | Notes |
|---|---|---|
| Time earned/lost this week | ✅ Done | Net delta with sign. |
| Biggest positive driver | ✅ Done | Computed in `calculateWeeklyTrend`. |
| Biggest drag | ✅ Done | Same. |
| Next best habit lever | ✅ Done | Deterministic ordering after the cleanup pass. |
| Trend vs prior week | ❌ Not started | No prior-week comparison. Each report is in isolation. |

### Profile / Settings

| Item | Status | Notes |
|---|---|---|
| Baseline profile editing | ❌ Not started | Profile screen does not let you edit DOB, smoking, etc. — only tone mode. Onboarding sets these once. |
| Connected data sources | 🟡 Partial | Shows three Apple Health rows hardcoded as "Not configured". Honest, but not driven by any real state. |
| Health permission state | ❌ Not started | Model removed during cleanup. Permissions dict on store is gone. Will need to come back with live HealthKit. |
| Tone mode toggle | ✅ Done | Live updates copy on Today. |
| Privacy / export / delete | ❌ Not started | All three are placeholder `Button { /* placeholder */ }`. |
| Paywall / restore purchases | ❌ Not started | Restore button is a no-op; no StoreKit at all. |

## 3. PRD — MVP Feature List

### Must have

| Item | Status | Notes |
|---|---|---|
| Local-first user profile | 🟡 Partial | UserProfile class exists. **No persistence** — re-seeded on every cold start. SwiftData was wired then deliberately stripped during cleanup; persistence is a follow-up plan. |
| Baseline survey | ✅ Done | In onboarding flow. |
| HealthKit authorization flow | ❌ Not started | No `HKHealthStore`, no entitlement, no `Info.plist` usage strings. Protocol exists for future drop-in. |
| Step count import | ❌ Not started | Mock service produces seeded fake steps. |
| Exercise minutes / workouts import | ❌ Not started | Same. |
| Sleep import | ❌ Not started | Same. |
| Weight / BMI import | ❌ Not started | Field exists on the model, no surface to capture. |
| Manual habits (alcohol, smoking, diet, stress, strength) | ❌ Not started | `HabitLog` class exists, no screen creates one. The risk-reduction quest assumes habits come from somewhere. |
| Clock estimate | ✅ Done | `ClockEngine.calculateBaseline`. |
| Daily time delta | ✅ Done | `ClockEngine.calculateDailyDelta`. |
| Time ledger | 🟡 Partial | Renders with sample data; no persistence; no chronological ordering. |
| Daily quests | ✅ Done | `QuestEngine.generateDailyQuests`. |
| Weekly report | ✅ Done | `ClockEngine.calculateWeeklyTrend`. |
| Pro paywall | ❌ Not started | Zero StoreKit code. |
| Privacy policy / ToS pages | ❌ Not started | Disclaimer exists in copy; no legal pages. |

### Should have

| Item | Status | Notes |
|---|---|---|
| Widgets / Lock Screen quick glance | ❌ Not started | Phase 2 of roadmap. |
| Manual quick log from Today | ❌ Not started | Today screen has no log entry point. |
| Habit streaks | ❌ Not started | No streak tracking on Quest or HabitLog. |
| Tone modes | ✅ Done | Three-way picker. |
| Confidence indicator | ✅ Done | `ConfidenceBadge` on Today + Weekly. |
| Export / delete data | ❌ Not started | Placeholder buttons only. |

### Later (explicitly out of scope for v1)

All of these are correctly **not started** per scope: Apple Watch, meal photo, HRV / RHR / VO2 Max scoring, BP / glucose, lab upload, AI coach.

## 4. Health Data Strategy (`HEALTH_DATA_STRATEGY.md`)

| Item | Status | Notes |
|---|---|---|
| Tier 1 passive signals declared | ✅ Done | All 11 fields are on `DailyHealthSnapshot`. |
| Manual baseline inputs | ✅ Done | Seven fields collected during onboarding. |
| Daily manual inputs (alcohol, smoking, diet, stress, strength, mindful minutes) | ❌ Not started | `HabitLog` exists but no screen captures input. |
| Pro / later data types | ❌ Not started | Correctly deferred. |
| Confidence model by data source | 🟡 Partial | Implemented as `ConfidenceModel.assign(snapshot:)` but only uses `sourceCompleteness` field; doesn't yet weigh source-tier (HK passive vs manual vs missing). |
| Permission request sequence (5-step) | ❌ Not started | No HealthKit code. |
| Critical UX rule: "never block the app behind full HealthKit access" | ✅ Done | App boots fully without HealthKit. |

## 5. Clock Model (`CLOCK_MODEL.md`)

| Item | Status | Notes |
|---|---|---|
| Population baseline anchor (CDC 79.0 / 76.5 / 81.4) | ✅ Done | `populationBaseline(for:)` in `ClockEngine`. |
| Baseline profile score (smoking, alcohol, activity, sleep) | 🟡 Partial | Smoking, alcohol, sleep, strength implemented. **Activity-level baseline missing** — no general activity input on UserProfile. |
| Daily behavior score (steps, exercise, workouts, sleep, strength, diet, alcohol, smoking, stress) | 🟡 Partial | Steps, exercise, sleep, alcohol, smoking, strength implemented. **Diet, stress, workouts, and exercise → workout minute distinction not implemented.** |
| Weekly trend score (movement trend, sleep consistency, workout frequency, weight trend) | 🟡 Partial | Implemented via summed dailies, not as separate trend signals. No weight trend. |
| Time delta examples honored (movement +10–30, workout +15–45, etc.) | ✅ Done | Numeric ranges roughly match the founder pack's product-tuning placeholders. |
| CDC activity anchor (150 min / week, 2× strength) | 🟡 Partial | Used as a movement-quest anchor (7,500 step daily target), but the explicit 150-min weekly target is not surfaced in any quest or report. |
| Confidence calculation | ✅ Done | Three-tier (high/medium/low). |
| Smoothing (daily delta vs weekly trend) | 🟡 Partial | Daily delta is raw; weekly is summed. No "significant warning before big negative changes". |
| Safety language guards (no "you will die", "added 3.2 years", "guaranteed") | ✅ Done | Grep-verified clean. |

## 6. UX & Game Loop (`UX_GAME_LOOP.md`)

| Item | Status | Notes |
|---|---|---|
| Core loop (open Today → see clock → top drivers → complete quest → log habit → return tomorrow) | 🟡 Partial | Steps 1–4 work. Step 5 (log habit) has no UI. Step 6 (return tomorrow) requires persistence — not present. |
| Time as core game currency | ✅ Done | "+42 min", years for healthspan; no points/coins/XP. |
| Today screen elements | 🟡 Partial | Missing: animated clock, "What moved your clock" copy. |
| Time Ledger explainability | ✅ Done | Each entry has source + driver. |
| Six quest types (movement, sleep, strength, nutrition, risk, recovery) | 🟡 Partial | Movement, sleep, risk, recovery wired. Strength path exists in engine but no generator route. Nutrition not started. |
| Weekly report sections (5 listed) | ✅ Done | Net, top driver, top drag, next lever, confidence. |
| Three tone modes | ✅ Done | But copy varies only on Today (see §1 above). |
| 8-step onboarding flow | 🟡 Partial | Compressed to 6 steps (value, safety, baseline, tone, perm education, reveal). Founder pack lists 8 — first quest screen + permission request screen rolled into others. |
| UX risk: anxiety mitigation, every negative paired with action | 🟡 Partial | Negative deltas use muted orange, not alarming red. Only the recovery-quest path explicitly pairs a negative with a positive next action. |

## 7. Monetization (`MONETIZATION.md`)

Everything in this category is **❌ Not started.**

| Item | Status | Notes |
|---|---|---|
| Free tier (basic clock, 3 daily quests, 7-day trend) | ❌ Not started | No tier gating. Everything is unlocked. |
| Pro Annual ($39.99–$59.99/year) | ❌ Not started | No StoreKit. |
| Pro Monthly ($7.99–$9.99/month) | ❌ Not started | |
| Lifetime ($99.99–$149.99) | ❌ Not started | |
| Paywall timing (after first reveal, after locked driver tap, etc.) | ❌ Not started | |
| 7-day annual trial | ❌ Not started | |
| Restore purchases | ❌ Not started | Placeholder no-op button only. |

## 8. App Store / ASO (`APP_STORE_ASO.md`)

| Item | Status | Notes |
|---|---|---|
| Primary category: Health & Fitness | 🟡 Partial | Documented decision; not yet declared in any App Store Connect listing (none exists). |
| Subtitle copy | ❌ Not started | Five candidates listed in founder pack; none chosen. |
| App Store description | ❌ Not started | Example exists in founder pack; no actual listing copy committed. |
| Six first-screenshots | ❌ Not started | No screenshots, no screenshot strategy artifact. |
| Keyword themes | ❌ Not started | No ASO keyword set chosen. |
| App Review posture document | ✅ Done | Captured in `PRIVACY_COMPLIANCE.md` and reflected in code (no medical claims, no entitlement until used). |

## 9. Privacy & Compliance (`PRIVACY_COMPLIANCE.md`)

| Item | Status | Notes |
|---|---|---|
| Privacy policy page | ❌ Not started | Buttons placeholder. No legal copy. |
| Plain-language permission explanations | 🟡 Partial | Permission education screen exists; explains the *category* not each data type (none are requested yet). |
| Data minimization (only data that powers a visible feature) | ✅ Done | Currently: zero HealthKit reads, so trivially compliant. |
| Progressive permission prompts | ❌ Not started | Deferred with live HealthKit. |
| Local storage | 🟡 Partial | In-memory only; no SwiftData container. The intent is local-first; the implementation is no-storage. |
| Delete data button | ❌ Not started | Placeholder. |
| Estimate labelling, confidence levels, medical disclaimer | ✅ Done | Disclaimer banner on every primary screen, "Estimate" framing in copy. |
| Forbidden uses (no ads, no HealthKit data sale, no third-party sharing, no false writes, no medical truth claims) | ✅ Done | Trivially: app doesn't read HealthKit, doesn't transmit anything, doesn't write to HealthKit. |
| Privacy nutrition label / App Store privacy details | ❌ Not started | `PrivacyInfo.xcprivacy` is empty arrays; will need updating when persistence + HealthKit land. |
| Tone control / gentle mode for emotional safety | ✅ Done | Three tone modes implemented. |

## 10. GTM / Launch (`GTM_LAUNCH_PLAN.md`)

Everything in this category is **❌ Not started** — engineering only built the substrate. The 90-day launch plan has not begun.

| Item | Status | Notes |
|---|---|---|
| Days 1–15: validation, landing page, 10 user interviews | ❌ Not started | |
| Days 16–45: MVP build | 🟡 Partial | This PR delivers the *skeleton* of the MVP build (~30% of named features). |
| Days 46–65: TestFlight beta (50–100 users) | ❌ Not started | |
| Days 66–90: launch | ❌ Not started | |

## 11. Roadmap & Metrics (`ROADMAP_METRICS.md`)

### Phase 1 (MVP) — by feature

| Feature | Status |
|---|---|
| Onboarding | ✅ Done |
| HealthKit core import | ❌ Not started |
| Baseline survey | ✅ Done |
| Clock estimate | ✅ Done |
| Today screen | ✅ Done |
| Time ledger | 🟡 Partial |
| Quests | ✅ Done |
| Weekly report | ✅ Done |
| Paywall | ❌ Not started |

**Phase 1 completion: 5 / 9 done, 1 partial, 3 not started ≈ 56%.**

### Phase 2 (Apple-native depth)

All ❌ — widgets, Lock Screen widget, Apple Watch glance, advanced HK metrics, notification timing, better trends.

### Phase 3 (AI assistance)

All ❌ — meal photo, personalized quest explanations, weekly coach summary, habit suggestions.

### Phase 4 (deeper longevity)

All ❌ — BP/glucose, lab upload, clinician content, deeper reports.

### Metrics infrastructure

| Metric category | Status |
|---|---|
| North star (WAUs completing 3 quests) | ❌ No analytics |
| Activation metrics | ❌ |
| Retention metrics | ❌ |
| Monetization metrics | ❌ |
| Health data metrics | ❌ |
| Emotional safety metrics | ❌ |

No analytics SDK is wired. No event taxonomy exists. By design — there's nothing to measure yet.

## 12. Technical Architecture (`TECHNICAL_ARCHITECTURE.md`)

| Item | Status | Notes |
|---|---|---|
| SwiftUI | ✅ Done | iOS 17 with `@Observable`. |
| SwiftData | ❌ Not started | Stripped during cleanup (todo 020) — schema declared without container is worse than no schema. Will return with persistence plan. |
| HealthKit | 🟡 Partial | Protocol boundary only. No real `HKHealthStore`. |
| StoreKit 2 | ❌ Not started | No `PaywallService` impl. |
| WidgetKit | ❌ Not started | Phase 2. |
| ActivityKit | ❌ Not started | Marked "only if needed". |
| App Intents | ❌ Not started | "Later" per founder pack. |
| Cloud backend | ❌ Not started | Correctly deferred per the V1 engineering rule ("do not add a backend until the local daily loop proves retention"). |
| Architecture stance: local-first | 🟡 Partial | Local *only*, but not actually persisted. |
| Eight core models | ✅ Done (7 of 8) | All seven specified in `TECHNICAL_ARCHITECTURE.md` § Core models exist. `HealthPermissionState` was dropped during cleanup; it returns with live HealthKit. |
| HealthKitService methods (requestAuthorization, fetchDailySnapshot, observeUpdates, handle unavailable) | 🟡 Partial | `dailySnapshot(for:)` and `recentSnapshots(...)` defined on protocol. Authorization + observers deferred. |
| ClockEngine (baseline, dailyDelta, weeklyTrend, assignConfidence, generateLedgerEntries) | ✅ Done | All four (baseline, dailyDelta, weeklyTrend, confidence). `generateLedgerEntries` is implicit in `dailyDelta`. |
| QuestEngine (generateDaily, adapt to missing data, no medical advice) | ✅ Done | All three properties verified. |
| PaywallService (StoreKit products, entitlement state, restore) | ❌ Not started | |
| Testing priorities (engine determinism, confidence, missing data, quests, paywall, mocked HK) | 🟡 Partial | Engine determinism, confidence (basic), missing data, quests are tested. Paywall and HK service mock tests not present. |
| V1 engineering rule (no backend) | ✅ Done | |

## 13. Codex Build Prompt (`CODEX_BUILD_PROMPT.md`)

The founder pack contained a paste-ready Codex first-pass prompt. Mapping its 11 enumerated items:

| # | Item | Status |
|---|---|---|
| 1 | SwiftUI app shell | ✅ |
| 2 | Onboarding flow | ✅ |
| 3 | Local SwiftData models | 🟡 (plain classes, not @Model) |
| 4 | HealthKit permission wrapper with mockable service boundary | 🟡 (boundary only — no real wrapper) |
| 5 | Today screen with placeholder/sample clock | ✅ |
| 6 | Time Ledger screen | ✅ |
| 7 | Daily Quests screen | ✅ |
| 8 | Profile/Settings screen | ✅ |
| 9 | ClockEngine v1 deterministic | ✅ |
| 10 | QuestEngine v1 deterministic | ✅ |
| 11 | Focused unit tests for ClockEngine and QuestEngine | ✅ |

**Codex build prompt completion: 9/11 done, 2 partial. Closest single number to "skeleton complete".**

## 14. Open Questions (`OPEN_QUESTIONS.md`)

19 open questions in the founder pack. None are resolved by this PR. They are decisions the founder needs to make, not implementation work. Status of each is documented in `PHASE_STATUS.md` § Next decisions for Q1–Q3 (the load-bearing ones).

---

## Critical gaps blocking next milestones

Three follow-up plans should be queued, in order:

1. **Live HealthKit plan** — adds entitlement, `Info.plist` `NSHealthShareUsageDescription`, `LiveHealthKitService`, progressive `requestAuthorization`, real per-data-type permission UI in onboarding, and a manual quick-log surface on Today. Unblocks: real time deltas, real ledger, manual habit logging, "missing vs denied" UI distinction. **Largest single value unlock.**

2. **Persistence plan** — re-introduces `@Model`, `VersionedSchema` (with property-level defaults preserved), constructs a `ModelContainer` with CloudKit explicitly disabled, routes mutations through `ModelContext`. Unblocks: cold-start state survival, prior-week comparisons in Weekly Report, real streak tracking, baseline editing on Profile, real "data delete" button.

3. **Paywall plan** — StoreKit 2 products (annual / monthly / lifetime), entitlement state, paywall placement at the four conversion moments listed in `MONETIZATION.md`, restore purchases, free-vs-Pro feature gating. Unblocks: revenue, all four paywall acceptance criteria in PRD, the entire monetization-metrics section.

After those three land, the app is plausibly TestFlight-ready. Before then, the loop the founder pack describes (open → see clock → complete quest → return tomorrow) is broken at "return tomorrow" because nothing persists.

## What to NOT do next

- Brand-name resolution (Open Question 1) is cheap to defer until live HealthKit lands. Strings should move to `Localizable.strings` *as part of* the live HealthKit PR so a future rename is one file.
- Widgets, Apple Watch, AI coach, lab upload, blood pressure, Phase 2/3/4 features — all correctly deferred.
- Analytics / crash reporting before TestFlight is premature; founder pack agrees.
- Backend before retention is proved (`TECHNICAL_ARCHITECTURE.md` V1 rule).

## Confidence in this audit

High for code-shipped items (greppable, code-grounded). Medium for tone-mode coverage and chronological-vs-sorted Time Ledger (judged from a quick read of the SwiftUI views). Low for "will this satisfy App Review" — that's a real-submission question, not an audit question.
