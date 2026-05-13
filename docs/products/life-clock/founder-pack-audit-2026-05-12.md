# Founder Pack vs App Audit — 2026-05-12

> Read-only audit. Five parallel cluster agents walked every founder-pack doc against the shipped app source, `vision.md` Decided constraints, recent polish logs, and operator memory. **No edits have been made** — this report is the review surface. The recommended edit batches at the bottom are sequenced so the operator can approve them one batch at a time.
>
> Trigger: the pro-value-audit P2 finding ("PaywallSheet header subhead must be replaced with concrete bulleted features sourced from MONETIZATION.md § Pro Annual") — but only if MONETIZATION.md is true. This audit verifies which founder-pack claims are still true and produces the edit list that makes them true.

## TL;DR

- **278 substantive claims checked across 15 founder-pack docs + `MASTER_FOUNDER_PACKAGE.md` + `founder-brief.md`.**
- **~90 drifts** (~32% drift rate). Pattern: founder-pack is a 2026-04-27 snapshot; the app moved past it on three big axes — the 2026-05-01 IA refactor (5-tab → 4-tab + Future), the 2026-05-04 tone-mode rename (`mementoMori` → `firmDirect`), and the 2026-05-09→2026-05-12 reveal/healthspan engine work.
- **3 NEW submission-blockers** discovered (on top of P1/P2 from the pro-value audit):
  - `legal/privacy-policy.md:89` states a **12+** rating; Apple deprecated 12+ in July 2025 and Life Clock auto-mapped to **13+**.
  - Same file says "do not knowingly collect data from children under **12**"; COPPA is under-13 and the app enforces under-13.
  - `legal/terms-of-use.md:66` repeats the 12+ rating drift.
- **Canonical-set recommendation: unnumbered files.** Reasoning: source code, every skill rubric, all current plans, and `PaywallSheet.swift` reference unnumbered `MONETIZATION.md` (21 refs vs 2 for numbered); same pattern across the pack. Numbered set is the original 2026-04-27 founder-pack snapshot.
- **Two caveats on archival:**
  - `09b_AGE_COMPLIANCE.md` has **no unnumbered counterpart**. Recommend rename to `AGE_COMPLIANCE.md` (drop `09b_` prefix), keep in unnumbered tier — content is too operationally live to bury.
  - `02_PRODUCT_STRATEGY.md` is a **content regression** of bare `PRODUCT_STRATEGY.md` (drops principle #8 "Monetize depth, not comprehension" + the Core product sentence). Do not archive as-is.
- `founder-brief.md` duplicates `EXECUTIVE_SUMMARY.md` — either delete or rewrite as a true one-pager.

## Submission blockers (all known)

Five known submission-blocker findings. The first two are from the pro-value audit; the next three are new from this audit.

| # | File | Issue | Fix scope |
|---|---|---|---|
| 1 | `Sources/Features/Profile/ProfileView.swift` | Active-Pro users have no in-app "Manage subscription" affordance (`trust-gap`) | Code edit — add `AppStore.showManageSubscriptions(in:)` row to Profile Subscription section |
| 2 | `Sources/Features/Paywall/PaywallSheet.swift` | Header subhead is generic ("Full weekly reports, tailored action plans, and deeper trend breakdowns") for a 9-feature MONETIZATION list (`value-claim-unjustified`) | Code edit, depends on Batch 1 below (MONETIZATION.md must be true first) |
| 3 | `docs/products/life-clock/legal/privacy-policy.md:89` | States 12+ rating; Apple deprecated 12+ in July 2025; auto-mapped to 13+ | Doc edit — Batch 0 below |
| 4 | `docs/products/life-clock/legal/privacy-policy.md` | Children's Privacy says "under 12"; COPPA is under-13, app enforces under-13; missing the suggested under-13 paragraph from `09_PRIVACY_COMPLIANCE.md:76` | Doc edit — Batch 0 below |
| 5 | `docs/products/life-clock/legal/terms-of-use.md:66` | 12+ rating drift on the second public legal surface | Doc edit — Batch 0 below |

## Drift density by cluster

| Cluster | Docs | Claims | ✅ Accurate | ❌ Drift | 🟡 Aspirational | ⚠ Ambiguous | Findings file |
|---|---|---|---:|---:|---:|---:|---|
| A — Monetization + ASO | MONETIZATION, APP_STORE_ASO, app-store-positioning | 38 | 22 | 9 | 5 | 2 | `01-monetization.md` |
| B — Strategy + GTM | EXECUTIVE_SUMMARY, BUSINESS_PLAN, PRODUCT_STRATEGY, GTM_LAUNCH_PLAN, ROADMAP_METRICS, founder-brief | 62 | 27 | 22 | 11 | 2 | `02-strategy.md` |
| C — Product spec | PRD, UX_GAME_LOOP | 58 | 22 | 26 | 4 | 6 | `03-product-spec.md` |
| D — Tech + Health + Clock | TECHNICAL_ARCHITECTURE, HEALTH_DATA_STRATEGY, CLOCK_MODEL, CODEX_BUILD_PROMPT, healthspan-coefficients | 62 | 38 | 18 | 4 | 2 | `04-tech-health.md` |
| E — Compliance + OQs | PRIVACY_COMPLIANCE, 09b_AGE_COMPLIANCE, OPEN_QUESTIONS, legal/* | 58 | 38 | 15 (3 blocker) | 2 | 3 | `05-compliance-oqs.md` |
| **Total** | **15+** | **278** | **147** | **90** | **26** | **15** | — |

Five drift themes recur across clusters:

1. **Tone-mode rename never reached docs.** "Memento Mori" appears in `PRODUCT_STRATEGY.md:84`, `02_PRODUCT_STRATEGY.md:73`, `06_UX_GAME_LOOP.md:90`, `ASC_CHECKLIST.md:179`. Shipped enum is `firmDirect` ("Firm/Direct") per vision Decided 2026-05-04 — and vision.md L46 explicitly calls out this drift.
2. **IA refactor (4-tab + Future) never reached docs.** PRD describes 5 screens (Today/Time Ledger/Quests/Weekly Report/Profile). UX_GAME_LOOP says 3 tabs. Reality is 4 (Today/History/Future/Profile). Quests folded into Today; Time Ledger absorbed by History; Future is entirely new and undocumented.
3. **"Weekly report" still listed as a thing.** EXECUTIVE_SUMMARY, BUSINESS_PLAN, ROADMAP_METRICS, PRD all reference a "weekly report" surface. App shipped `WrapUpSheet` (in-app, pull-only via `WrapUpCoordinator`) plus History weekly teaser cards — no "report" screen exists.
4. **Streak metric explicitly rejected in vision.md but still in docs.** Vision Decided 2026-05-06: "monthly count, no streak"; `DietStreakCalculator` was dropped. `ROADMAP_METRICS.md:73` still tracks "7-day streak rate"; `UX_GAME_LOOP.md:44` describes a "Diet streak banner."
5. **Aspirational Pro features mixed with shipped Pro features.** MONETIZATION.md Pro Annual list mixes 5 shipped features with 4 problematic ones: widgets (no WidgetKit target), Pro export (no UI, Free delete only), advanced HealthKit metrics (no concrete deliverable), AI meal/photo (already "later"). 3 of 5 "best conversion moments" are completely unwired (#3 weekly-report-preview, #4 advanced-HK, #5 widgets).

## Free/Pro rule reconciliation

**The Free/Pro rule itself is sound** — every shipped Pro gate maps cleanly to one of {depth, archive, correction power}. No rule-violation in source. The polish issues (cancel pointer, paywall header, WrapUp signal) are UX, not policy. **Do not edit MONETIZATION.md lines 11–30.**

| Gate site | Mechanism | Rule-aligned? |
|---|---|---|
| `LifeClockStore.applyOverride` (`OverrideService.swift:36`, `EntitlementGatedWritesTests.swift:33`) | `.notEntitled` throw when `!isPro` | ✅ correction power |
| `LifeClockStore.revertOverride` | `.notEntitled` throw | ✅ correction power |
| `LifeClockStore.selectPlanQuest` (`LifeClockStore.swift:794`) | `.notEntitled` throw | ✅ depth (custom quests) |
| History fog stack (`HistoryView.swift:227–276`) | Conditional view on `!isPro` over older rows | ✅ archive |
| History weekly teaser (`HistoryView.swift:337–352`) | `isPro` branch in weekly card | ✅ depth |
| Today plan-edit chip (`TodayView.swift:722–737`) | `isPro` routes Free → paywall | ✅ depth |
| Future What-If thumb (`WhatIfSlider.swift:148`) | `isPro` gates; locked tap → paywall | ✅ depth |
| Profile Subscription section (`ProfileView.swift:146–170`) | Discovery surface; not a gate | ✅ surface |

## Numbered-only content worth preserving

If/when the numbered set is archived, these specific items must migrate first (otherwise content is lost):

| Source (numbered) | Content | Recommended target |
|---|---|---|
| `09b_AGE_COMPLIANCE.md` (entire file, 177 lines) | Apple July-2025 rating overhaul, COPPA actual-knowledge posture, GDPR-K table, Cal AI rejection vector, implementation enumeration, deferred-items rationale | **Rename to `AGE_COMPLIANCE.md`** (drop prefix) — keep in unnumbered tier; too live to archive |
| `09_PRIVACY_COMPLIANCE.md` §"Users under 13 (COPPA posture)" (lines 62–78) | Implementation enumeration + FTC Feb 2026 safe-harbor + suggested public privacy-policy paragraph | Migrate into `PRIVACY_COMPLIANCE.md` (currently the unnumbered is shorter/staler) |
| `09_PRIVACY_COMPLIANCE.md` §"Users in the EU (GDPR-K posture)" (lines 80–84) | Uniform-13-floor v1 decision, local-first defense, residual-risk note | Migrate into `PRIVACY_COMPLIANCE.md` |
| `06_UX_GAME_LOOP.md:43-49` | Time Ledger example entries (illustrative copy: "+18 min - 9,800 steps - Apple Health" etc.) | Migrate into `CLOCK_MODEL.md` or driver-line composition doc |
| `06_UX_GAME_LOOP.md:53-67` | Six quest-types taxonomy with example quests | Reference / re-home in `quest-pool-vocab.md` if not already there |
| `04_HEALTH_DATA_STRATEGY.md` / `05_CLOCK_MODEL.md` source citations [S3][S4][S5][S8][S9] | Link-targets into `SOURCES.md` | Already preserved in unnumbered versions; verify `SOURCES.md` resolves them |
| `02_PRODUCT_STRATEGY.md` ← **regression — the numbered is missing content** | Numbered drops principle #8 "Monetize depth, not comprehension" + Core product sentence that bare has | **Do not archive `02_` as-is** — bare is canonical, leave numbered in place or content-merge bare → numbered first |

Everything else in the numbered set is a strict subset of (or byte-near-identical to) the unnumbered version. `app-store-positioning.md` is byte-identical to `08_APP_STORE_ASO.md` — a duplicate. `13_CODEX_BUILD_PROMPT.md` ≈ `CODEX_BUILD_PROMPT.md`.

## Recommended edit batches

Batches are sequenced so each one unblocks the next. **You approve a batch → I apply those edits → we move on.** Each batch lists concrete file:line + old text + new text; full per-edit detail lives in the cluster findings files at `/tmp/life-clock-fp-audit/`.

### Batch 0 — Submission blockers (legal/* docs)

**Why first:** the public-facing privacy policy URL is what Apple's nutrition label points at. Submitting with the 12+/under-12 drift is a known App Review rejection vector.

1. **`legal/privacy-policy.md:89`** — change "rated **12+**" → "rated **13+**"; rewrite Children's Privacy paragraph to "under 13" + paste the suggested under-13 paragraph from `09_PRIVACY_COMPLIANCE.md:76`.
2. **`legal/terms-of-use.md:66`** — same 12+ → 13+; "not for children under 12" → "not for children under 13."
3. **`legal/privacy-policy.md`** — resolve placeholders `[REPLACE WITH LEGAL ENTITY OR INDIVIDUAL NAME]`, `[REPLACE WITH SUPPORT EMAIL]`, `[REPLACE WITH JURISDICTION]`. **Operator action — I can't fill these in.**
4. **`legal/privacy-policy.md:48`** — Tone-mode preference "(gentle / coach)" → "(gentle / coach / firmDirect)".

### Batch 1 — MONETIZATION truth (unblocks pro-value P2)

**Why next:** P2 paywall-header rewrite must source from a truthful MONETIZATION.md Pro Annual list.

5. **`MONETIZATION.md` lines 48–59** — replace 9-bullet Pro Annual unlocks list with 5 shipped bullets + 4 explicit "Planned (post-v1)" items. Removes the export/delete drift (App Review value-claim risk).
6. **`MONETIZATION.md` lines 77–83** — annotate each of 5 "best conversion moments" with **Wired** / **Planned** / **Deferred to v1.1/v1.2** so paywall copy knows what's real.
7. **`MONETIZATION.md` lines 86–87** — rewrite trial-stance paragraph to state v1 ships without a trial (`Products.storekit` has `introductoryOffer: null` for both subscriptions — any trial language in paywall = value-claim mismatch and App Review rejection vector).
8. **`MONETIZATION.md` lines 36–42** — clean up Free list. Drop false "basic manual habits" bullet (no such feature exists; quests are auto-generated). Note that wrap-ups are Free + pull-only.
9. **`MONETIZATION.md` — new section** — add `## As shipped (2026-05)` block with actual SKU values ($7.99 / $49.99 / $129.99) so strategy docs can link rather than restate ranges.
10. **`APP_STORE_ASO.md` lines 15–19** — disambiguate three brand strings: App Store listing name ("Life Clock: habits earn time"), CFBundleDisplayName ("Life Clock"), tagline ("Habits earn time."). Current doc conflates listing-name with home-screen-name.

### Batch 2 — Tone-mode + brand-name truth (smallest diff, biggest correctness payoff)

11. **`PRODUCT_STRATEGY.md:84`** — "Memento Mori: more direct mortality framing." → "Firm/Direct: terse, specific, no hedging. (Code: `firmDirect` in `ToneMode.swift`. Earlier strategy docs called this 'Memento Mori'; the shipped name is Firm/Direct — see vision.md.)"
12. **`02_PRODUCT_STRATEGY.md:73`** — same edit (or skip if `02_` is being archived).
13. **`06_UX_GAME_LOOP.md:90`** — "Memento Mori" → "Firm/Direct"; add banner at top: "Superseded by `UX_GAME_LOOP.md`. See vision.md for canonical tone-mode names."
14. **`ASC_CHECKLIST.md:179`** — review note "switch to 'Memento Mori'" → "switch to 'Firm/Direct'".
15. **`EXECUTIVE_SUMMARY.md:5–7`** — resolve brand-name claim: "**Life Clock** is the working title… Other brand candidates include TimeBack, Long Game…" → "**Life Clock** is the resolved working name (App Store: 'Life Clock: habits earn time'). See `PHASE_STATUS.md` 'Resolved decisions.' Original April 2026 brand candidates retained below for repositioning reference only…"

### Batch 3 — IA truth (4 tabs + Future + monthly-not-streak)

16. **`UX_GAME_LOOP.md:32`** — "3 tabs" → "4 tabs (Today, History, Future, Profile)".
17. **`UX_GAME_LOOP.md:55`** — "(90 days for Pro, 7 days for free)" → "(90 days for Pro, 3 days for free, with paywall-fogged peek of older rows)" — match `HistoryView.swift:19 freeRowLimit = 3`.
18. **`UX_GAME_LOOP.md:44`** — "Diet streak banner (conditional, ≥2 days)" → "Monthly logging banner (calendar-month count + milestone copy). Cite vision Decided 2026-05-06."
19. **`UX_GAME_LOOP.md:34–46`** — add missing render-order items: trajectoryPeek, rescueLine, ReflectionCard, DisclaimerBanner per `TodayView.swift:105–119`.
20. **`PRD.md` Core screens section (lines 13–86)** — replace 5-screen list with 4-tab list; demote "Time Ledger" + "Quests" to Today-section descriptions; add new "### 4. Future" subsection (covers `TrajectoryChart`, `WhatIfSlider`, `NarrativeEngine`, day0/coldLaunch1to3/warmingUp4to13/full14plus states).
21. **`PRD.md` Profile section (lines 75–86)** — add Appearance/palette picker, daily reminder section (8…22 hour clamp), completion badges, SafetyNet entry. Cite `polish-2026-05-09-profile-section-sweep.md`.
22. **`PRD.md` Weekly Report section (lines 63–73)** — note weekly content lives inside History (`HistoryView.weeklySection`) + `WrapUpSheet` fires pull-only on cold-launch. Cite vision Decided 2026-05-09 (pull, not push).
23. **`PRD.md` Should-have list (lines 108–115)** — drop "Habit streaks" (vision Decided 2026-05-06 rejects); mark Widgets/Lock-Screen as unshipped.
24. **`ROADMAP_METRICS.md` Phase 1 (lines 7–19)** — rewrite to shipped surfaces: reveal-onboarding (29 screens) / sensitive-consent block (PSS-10, UCLA-3) / Future tab Pro-gated / SafetyNet / QuickLog / etc.
25. **`ROADMAP_METRICS.md:73`** — delete "7-day streak rate" retention metric; add "Monthly logging count distribution" (vision Decided 2026-05-06).
26. **`ROADMAP_METRICS.md:56–58`** — North star "WAUs complete 3 quests" → "WAUs complete 3 Today's Plan actions per week"; note analytics is post-TestFlight.
27. **`ROADMAP_METRICS.md` top** — add instrumentation-status note: "Analytics intentionally absent pre-TestFlight (`PHASE_STATUS.md`). Metrics below describe target funnel."

### Batch 4 — Model + Tech-arch accuracy

28. **`TECHNICAL_ARCHITECTURE.md` — new subsection** — document `HealthspanEngine` + Future-tab projection model; reference `healthspan-coefficients.md`. Currently TECHNICAL_ARCHITECTURE reads as if `ClockEngine` is the whole math story.
29. **`TECHNICAL_ARCHITECTURE.md` Core models** — replace inline field lists with a pointer to `Sources/Models/LifeClockSchema.swift` (or sync to V1.7 reality: add `DailyReflection`, `QuestEvent`, `CumulativeSummaryCache` + ~20 missing `UserProfile` fields).
30. **`TECHNICAL_ARCHITECTURE.md` Services** — add the 9 missing service mentions: `HealthKitAggregator`, `OverrideService`, `HistoricalImportCoordinator`, `TelemetryRecorder`, `OnboardingTelemetry`, `AffinityEngine`, `NarrativeEngine`, `HealthspanEngine`, `WrapUpCoordinator`.
31. **`TECHNICAL_ARCHITECTURE.md` iOS target** — add "iOS 17 / Swift 5 (SwiftData → iOS 17 floor)" pin.
32. **`TECHNICAL_ARCHITECTURE.md` — new section** — Notifications constraints (one daily reminder, 8…22 clamp, wrap-ups pull-not-push). Mirrors vision Decided constraints + operator memory `feedback_life_clock_notifications_constraints.md`.
33. **`CLOCK_MODEL.md` Baseline profile score** — expand to list the 5 engine inputs the doc omits: BMI, cardio mins/wk, parental longevity, PSS-10, UCLA-3. PSS+UCLA are vision Q9 Decided 2026-05-12 — documentation that omits them is actively misleading.
34. **`CLOCK_MODEL.md` Smoothing** — drop or honestly mark "weekly trend with smoothing"; engine ships additive rolling sum, no EMA. Same for trajectory model (`HealthspanEngine.weeklyTrajectory` uses linear interpolation, not historical aggregates).
35. **`HEALTH_DATA_STRATEGY.md` Tier 1** — trim to 6 actually-read types (steps, exercise time, active energy, sleep analysis, resting HR, body mass). Move height / heart rate / VO2 max / BMI / workouts / distance to "Not currently read from HealthKit" subsection.
36. **`HEALTH_DATA_STRATEGY.md` Permission flow** — rewrite "progressive permission prompts" claim to match single-prompt reality, or mark as planned. Doc currently imagines a multi-stage prompt that isn't implemented.
37. **`Info.plist NSHealthShareUsageDescription`** — expand to mention active-energy + body-mass (currently lists 4 of 6 types) OR reword inclusively. Reviewer-discoverable inconsistency.
38. **`Info.plist NSHealthUpdateUsageDescription`** — either remove (true read-only) or update docs (`ASC_CHECKLIST.md:187` + `09_PRIVACY_COMPLIANCE.md`) which currently say "no NSHealthUpdateUsageDescription".

### Batch 5 — Strategy/exec accuracy cleanup

39. **`EXECUTIVE_SUMMARY.md:48–49`** — MVP loop steps 6–7: "1-3 quests" → "Today's Plan suggests 1-3 actions"; "Weekly report summarizes" → "Weekly wrap-up sheet (in-app, Monday cold-launch via `WrapUpCoordinator`)".
40. **`EXECUTIVE_SUMMARY.md:67–70`** — replace pricing ranges with shipped SKUs (link to MONETIZATION § As shipped).
41. **`EXECUTIVE_SUMMARY.md:15` + `GTM_LAUNCH_PLAN.md:17`** — wedge "Earn time **back** with better daily habits" → "Earn time with better daily habits" (in-app voice was deliberately moved off "back" per vision Decided 2026-05-11). **Or** add footnote allowing marketing copy to diverge — operator picks.
42. **`BUSINESS_PLAN.md:66–72`** — Free tier list: drop false "limited daily quests" framing; restate from MONETIZATION.md.
43. **`BUSINESS_PLAN.md:76–85`** — Pro list: align with MONETIZATION post-Batch-1 (drops widgets/export from v1, marks v2-scoped items).
44. **`GTM_LAUNCH_PLAN.md:45`** — insert banner before 90-day plan: "April 2026 sequencing; superseded by `PHASE_STATUS.md`."
45. **`GTM_LAUNCH_PLAN.md:85`** — "complete quests for at least one week" → "complete at least one Today's Plan action per day for the first week".

### Batch 6 — Archival hygiene (last)

**Why last:** the prior batches put the unnumbered set in good shape; this batch shrinks the surface area to maintain.

46. **`OPEN_QUESTIONS.md` + `14_OPEN_QUESTIONS.md`** — add deprecation banner at top of each: "This file is a 2026-04-27 founder-pack snapshot. Active OQs live in `vision.md ## Open questions`. See vision.md for current state."
47. **Rename `09b_AGE_COMPLIANCE.md` → `AGE_COMPLIANCE.md`** (drop the `09b_` prefix). Keep in unnumbered tier.
48. **Migrate `09_PRIVACY_COMPLIANCE.md` §"Users under 13" + §"Users in the EU"** → `PRIVACY_COMPLIANCE.md`. (After this, the unnumbered version has all the COPPA defense content.)
49. **`AgeGate.swift:8` + `CLAUDE_HANDOFF.md:80,96`** — update remaining "12+" docstring references to "13+" (already flagged in `09b §1`).
50. **Move CODEX_BUILD_PROMPT.md + 13_CODEX_BUILD_PROMPT.md** → `docs/products/life-clock/archive/codex-build-prompt-2026-04.md`. April skeleton brief; superseded by all post-onboarding work. Lift exclusion list + core rules into vision.md first (most already there).
51. **`founder-brief.md`** — operator decision: (a) delete, (b) rewrite as a true one-pager. Current file is a duplicate of `EXECUTIVE_SUMMARY.md` and produces drift on every update.
52. **`app-store-positioning.md`** — delete (byte-identical to `08_APP_STORE_ASO.md`; both are subsets of canonical `APP_STORE_ASO.md`).
53. **Archive the rest of the numbered set** to `docs/products/life-clock/archive/founder-pack-2026-04-27/`:
    - `00_EXECUTIVE_SUMMARY.md`, `01_BUSINESS_PLAN.md`, **`02_PRODUCT_STRATEGY.md`** (only after content-merging principle #8 + Core product sentence into the bare file is verified — but currently bare already has them, so the numbered version's *absence* of these is the regression; safe to archive numbered as-is), `03_PRD.md`, `04_HEALTH_DATA_STRATEGY.md`, `05_CLOCK_MODEL.md`, `06_UX_GAME_LOOP.md`, `07_MONETIZATION.md`, `08_APP_STORE_ASO.md`, `09_PRIVACY_COMPLIANCE.md` (after content migration in #48), `10_GTM_LAUNCH_PLAN.md`, `11_ROADMAP_METRICS.md`, `12_TECHNICAL_ARCHITECTURE.md`, `14_OPEN_QUESTIONS.md`, `MASTER_FOUNDER_PACKAGE.md`.
54. **Replace numbered references in docs/code** that currently point at numbered paths (`14_OPEN_QUESTIONS.md` etc.) with unnumbered paths. Mostly limited to older plans; can be left in place since archive paths still resolve.

## Cluster findings (full detail)

These five files contain the per-finding evidence (file:line on the doc side, file:line on the app side, classification, proposed-fix text). Read these before approving any batch:

- `/tmp/life-clock-fp-audit/01-monetization.md` (416 lines)
- `/tmp/life-clock-fp-audit/02-strategy.md` (221 lines)
- `/tmp/life-clock-fp-audit/03-product-spec.md` (144 lines)
- `/tmp/life-clock-fp-audit/04-tech-health.md` (271 lines)
- `/tmp/life-clock-fp-audit/05-compliance-oqs.md` (203 lines)

## Decision points needed before edits land

A small handful of items the audit can't resolve without operator input:

1. **Batch 0 #3** — legal-entity name, support email, jurisdiction placeholders in `legal/privacy-policy.md`. Operator-only.
2. **Batch 0 +** — App Store Connect age-rating questionnaire run-through. Operator-only.
3. **Batch 1 #7** — confirm: v1 ships without a trial (Products.storekit shows no introductory offer)? If yes, paywall + MONETIZATION align. If a trial is planned for launch, the order changes.
4. **Batch 5 #41** — "Earn time back" marketing wedge: (a) align to in-app voice "Earn time" or (b) explicitly allow GTM copy to diverge. Operator picks.
5. **Batch 6 #51** — `founder-brief.md`: delete vs rewrite.
6. **Batch 5 ambiguous claim** — `BUSINESS_PLAN.md:13` ICP age band (25–45). Is this still the bet? Operator confirms.

---

**Status:** awaiting operator approval per batch. Most-impactful first three batches (0, 1, 2) are also the smallest diff and resolve all known submission-blockers + unblock the pro-value P2 work + fix the most-widely-propagated drift (Memento Mori naming). Recommend approving 0+1+2 as a single unit; 3+4+5 reviewed separately; 6 (archival) once everything else is settled.
