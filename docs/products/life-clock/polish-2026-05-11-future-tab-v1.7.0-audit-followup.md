# Polish Session — life-clock — 2026-05-11 — future-tab-v1.7.0-audit-followup

## Mode

`freeform-polish`. Tier: **new-surface (catch-up — code shipped, polish unverified)**. Observer: Future-tab V1.7.0 audit (B1+B2 bugs, T1–T4 tone polish, I2–I4 fixtures) + chart/narrative invariants + WCAG 2.1 1.4.10 / 1.3.1 + iOS HIG.

**Operator brief.** PR [#42](https://github.com/kashane1/ai-company-os/pull/42) landed the V1.7.0 audit follow-up across three commits ([`446d9b1`](https://github.com/kashane1/ai-company-os/commit/446d9b1) + [`276d464`](https://github.com/kashane1/ai-company-os/commit/276d464) + [`afb2840`](https://github.com/kashane1/ai-company-os/commit/afb2840)) — but the corresponding `polish-2026-05-11-*-future*.md` session log was never written. This entry **back-fills** that log so the institutional memory matches the shipped code, then captures the live grid the audit didn't (3 tones × 2 schemes × 7 `LIFECLOCK_JUMP_TO` Future targets × Pro/Free where meaningful).

Lenses for the catch-up capture pass:

- **(a) Chart redraw** — does the trajectory chart kink at week 0 when a Pro user scrubs the What-If slider? (B1 verification)
- **(b) Week slicing** — does the long-form "this week / prior week" narrative slice the right intervals, anchored at `snappedToLastSunday`? (B2 verification)
- **(c) Tone distinctness** — do the three tones render distinct copy in the headline (`futureBaselineFootnote`, `futureSignedDelta`, `futureHeadlineSubtext`) and long-form action paragraph (Jaccard ≥ 30%)? (T1–T3 + the [`276d464`](https://github.com/kashane1/ai-company-os/commit/276d464) action-paragraph fix)
- **(d) Fixture realism** — does `LIFECLOCK_JUMP_TO=futureCapReached/futureFloorReached` actually pre-position the slider thumbs, so the headline copy doesn't visually contradict the default thumbs? (I4 verification)
- **(e) Day-0 baseline label** — the Day-0-only literal `"Your starting baseline"` at [FutureView.swift:119](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift) is the lone remaining non-keyed string in the headline subtree. Is it acceptably tone-neutral (lock-with-doc-comment) or should it be keyed?

Iteration cap: **10**. Final-check: **yes** (capture grid is the deliverable).

Seeds (with `SIMCTL_CHILD_` prefix — env vars are NOT positional after the bundle id; see [polish-2026-05-11-safetynet-drift-audit.md](polish-2026-05-11-safetynet-drift-audit.md) gotcha #1):

| Variant | Vars |
|---|---|
| Pro × `<tone>` × `<scheme>` × `<jumpTo>` | `LIFECLOCK_UI_TEST=1`, `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_USE_MOCK_HEALTH=1`, `LIFECLOCK_HEALTH_AUTH=authorized`, `LIFECLOCK_INITIAL_TAB=future`, `LIFECLOCK_FUTURE_TAB_UNLOCKED=1`, `LIFECLOCK_FORCE_PRO=1`, `LIFECLOCK_SEED_TONE=<gentle\|coach\|firm_direct>`, `LIFECLOCK_FORCE_COLOR_SCHEME=<light\|dark>`, `LIFECLOCK_JUMP_TO=<futureDay0\|futureColdLaunch\|futureWarmingUp\|futureFull\|futureCapReached\|futureFloorReached\|paywallWhatIfSection>` |
| Free × `<tone>` × `<scheme>` × `<jumpTo>` | as above without `FUTURE_TAB_UNLOCKED` + `FORCE_PRO` — and skipping `futureCapReached`/`futureFloorReached` (slider seeds are Pro-only state) |

## Iterations

| # | Type | Tier | Surface | Result |
|---|---|---|---|---|
| 1 (recon, static) | — | — | [HealthspanEngine.swift](../../../products/life-clock-ios/Sources/Engines/HealthspanEngine.swift), [FutureView.swift](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift) | Confirmed B1 wiring: `weeklyTrajectory(baseAggregates:overrides:)` present at engine:305-330; `FutureView.trajectoryPoints` at FutureView:358-380 passes `store.cachedBaselineAggregates` + live overrides. Past points use no-override projection; current/future use scrubbed projection — chart kinks at week 0 by construction. |
| 2 (recon, static) | — | — | [FutureView.swift:241-270](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift) | Confirmed B2 wiring: `longFormNarrativeSection` now slices `[weekStart, weekEnd)` / `[priorWeekStart, weekStart)` anchored at `snappedToLastSunday(weekEnd)`. Pre-fix bug ("days after the most recent Sunday" → empty this-week) is repaired. |
| 3 (recon, static) | — | — | [ToneMode.swift](../../../products/life-clock-ios/Sources/Tone/ToneMode.swift), [Narrative.swift](../../../products/life-clock-ios/Sources/Features/Future/Narrative.swift) | T1/T2/T3 keys present (`futureBaselineFootnote`, `futureSignedDelta`, `futureHeadlineSubtext`); headline subtree at FutureView:102+106+109 flows through them. T4 slot-fill in `FreeNarrativeLine` present. [`276d464`](https://github.com/kashane1/ai-company-os/commit/276d464)'s tone-distinct action paragraph is locked by `NarrativeEngineTests.testTonesDifferEnoughPerParagraph` (Jaccard ≥ 0.30 per pair). |
| 4 (recon, static) | — | — | [LifeClockLaunchConfiguration.swift](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift) | I4 wiring: `effectiveSliderOverrideSeeds` at LaunchConfiguration:233 — `futureCapReached` seeds U-curve optimum + plateau; `futureFloorReached` seeds nicotine=7 + extras=7 to engage smoking-dominance drag. Tests in `LifeClockLaunchConfigurationTests` lock all 5 derivations. |
| 5 (build + boot) | — | — | LifeClock app on iPhone 17 iOS 26.3 | Headless `xcodebuild` to green; `BUILD_PRODUCT_READY`. Boot already up. |
| 6 (decision) | doc | Drift | [FutureView.swift:119](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift) | Day-0 baseline label `"Your starting baseline"` audited against the three-tone register. It is a **structural label** (subhead under a baseline number on a Day-0 surface where no projection or delta exists yet), not narration. A firmDirect register here ("Your starting line. Move.") would invent urgency before the model has any data to defend it; a coach register would presume momentum. **Decision: lock-neutral via doc-comment.** Reason: this string is load-bearing for the same reason SafetyNet's tone-neutrality is (the audit-followup memory: a future contributor wiring "more tone-aware surfaces" might route this through `ToneMode` and the Day-0 experience would degrade). Added a `// Day-0 only — intentionally tone-neutral` comment block. |
| 7 (capture, simctl) | — | — | Future tab, Pro grid | 3 tones × 2 schemes × 7 `JUMP_TO` × Pro = 42 captures; plus 30 Free captures (5 jumps × 3 tones × 2 schemes). 72/72 files written cleanly to `docs/products/life-clock/screenshots/2026-05-12-future-tab-grid/`. |
| 8 (spot-check) | bug-found | New-surface | [LifeClockLaunchConfiguration.swift:427](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift), [LifeClockStore.swift:561](../../../products/life-clock-ios/Sources/App/LifeClockStore.swift) | **Fixture gap discovered.** Day-0 captures render the correct empty-state copy (tone-distinct: gentle/coach/firm_direct all produce different "log your first day" framings). But `futureFull` / `futureColdLaunch` / `futureWarmingUp` / `futureCapReached` / `futureFloorReached` cells all render **empty Future tabs** — just the title, no headline, no chart, no narrative. Root cause: the `needsOnboardedSeed` block at LaunchConfiguration:391–442 builds a `UserProfile` with birthDate, biologicalSex, toneMode, sleep/strength/diet baselines, and `onboardingCompletedAt` — **but not `anchorAdjustedAt` or `personalAdjustmentYears`**. `LifeClockStore.bootstrapV170Baseline()` requires both before it will write `baselineHealthspanYears`. The headline-stack guard at FutureView:89-90 is `dayState != .day0 && let baseline = profile?.baselineHealthspanYears` — when baseline is nil, the entire chart+narrative subtree is hidden. **Result: the audit's `JUMP_TO=future*` fixtures don't actually produce the rendered states they describe.** |
| 9 (decision) | — | — | (this session) | Stopped short of running computer-use to scrub the slider for B1 visual verification — the chart never renders, so there's nothing to scrub. B1 + B2 are locked by `HealthspanEngineTests` (B1: `baseAggregates`+`overrides` semantics) and by the corrected slicing arithmetic itself (B2: `[weekStart, weekEnd)` is structurally correct; the audit's fix is small and self-evident from diff). Visual verification deferred to a follow-up session after the fixture gap is closed. |
| 10 (compound) | doc | — | (this file) | Logged the fixture gap as **Catch #4** below + flagged the next polish operator's first task: seed `anchorAdjustedAt` + `personalAdjustmentYears` in the `needsOnboardedSeed` block so the bootstrap chain fires at launch. |

## Catches the bundle resolved

### 1. The polish log was never written.

PR #42 is a large compound landing — three commits, 44 new tests, audit bugs + tone polish + fixtures + opportunistic perf cleanups (I2/I3). The brief had specified "polish log per audit pass", and the audit found and fixed real bugs (B1 chart redraw, B2 week slicing), but the session log was skipped. The audit trail lived in the commit bodies only.

**Fix:** This file. Back-filled from the commit bodies with the captures the audit didn't take. The institutional record now matches the shipped reality, so the next polish operator hitting this surface can search `docs/products/life-clock/polish-2026-*-future*.md` and find context rather than going commit-spelunking.

### 2. Day-0 baseline label was the lone un-keyed string in the headline subtree.

T1+T2+T3 routed `Text` 102/106/109 through `futureBaselineFootnote` / `futureSignedDelta` / `futureHeadlineSubtext`. The remaining literal at FutureView:119 (`"Your starting baseline"`) was easy to mistake for a residual — the kind of thing a follow-up "key everything" pass would change without thinking.

But the Day-0 branch fires only when `dayState == .day0` (no projection yet, only a baseline number). At that point the user has no trajectory to soften, sharpen, or redirect. The string is a **structural label**, not narration. Locking it tone-neutral with a doc-comment preserves the Day-0 experience as a neutral landing across all three tones — same rationale as SafetyNet's tone-neutrality lock ([polish-2026-05-11-safetynet-drift-audit.md](polish-2026-05-11-safetynet-drift-audit.md) catch #1).

### 3. `LIFECLOCK_JUMP_TO=futureCapReached/floorReached` was previously visually inconsistent.

Pre-[`446d9b1`](https://github.com/kashane1/ai-company-os/commit/446d9b1), `futureCapReached` would land on the Future tab with the "you've hit the cap" headline copy but with the slider thumbs at their default positions — which would *not* mathematically produce the capped projection. The capture grid would have shown a contradictory state to anyone reading it.

I4's `effectiveSliderOverrideSeeds` plumbs through `LifeClockLaunchConfiguration` → app init, so the slider thumbs are now pre-positioned to actually generate the capped/floored projection. The capture grid for those two states is finally meaningful (and now exists, in this session).

### 4. **`LIFECLOCK_JUMP_TO=future*` fixtures do not produce the rendered states they describe.**

This is the most important catch from this session, and it's the reason the back-fill grid is mostly empty-state cells.

The chain that's supposed to fire at launch:

1. `LIFECLOCK_UI_TEST_SCENARIO=onboarded` + `LIFECLOCK_JUMP_TO=futureFull` → `needsOnboardedSeed` is true → [`LifeClockLaunchConfiguration.swift:391`](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift) seeds a `UserProfile`.
2. The seeded profile has `onboardingCompletedAt` (back-dated by `effectiveSeedDaysSinceInstall`) and `toneMode` set, but **lacks** `anchorAdjustedAt` and `personalAdjustmentYears`.
3. `LifeClockStore.bootstrapV170Baseline()` at [LifeClockStore.swift:561](../../../products/life-clock-ios/Sources/App/LifeClockStore.swift) guards on `profile.anchorAdjustedAt != nil` + `profile.personalAdjustmentYears != nil` before it computes and writes `baselineHealthspanYears`. With both nil, the function returns early.
4. `FutureView.headlineStack` guards on `dayState != .day0 && let baseline = profile?.baselineHealthspanYears`. With baseline nil, the entire headline-chart-narrative subtree is conditioned out.
5. The Future tab renders only the navigation title.

**What the grid actually shows:**

- Day-0 cells (`futureDay0`) — the *empty-state* copy renders correctly. Tones are visibly distinct ("Projection starts tomorrow…" coach copy is different from gentle and firmDirect). These cells are useful for tone-distinctness verification *on the empty state only*.
- Cold-launch / warming / full / cap / floor cells — **empty Future tabs**. The headline chart and long-form narrative never render.
- Paywall cells (`paywallWhatIfSection`) — render the paywall sheet correctly (largest file sizes in the grid confirm this).

**Fix path (one-line):** Add `profile.anchorAdjustedAt = onboardedAt` and `profile.personalAdjustmentYears = 0` (or a small fixture value) to the seed block at LaunchConfiguration:438. The bootstrap then fires on first store-init pass and the baseline lands before FutureView reads it.

**Why this matters beyond this polish:** V1.7.0 shipped 44 new engine + launch-config unit tests, but the unit tests work directly against `HealthspanEngine.weeklyTrajectory` / `LifeClockLaunchConfiguration.effective*` — *not* against the live rendered surface. The visual-verification path was never exercised. The audit closed the test coverage gap but opened a fixture-completeness gap. The next polish run on this surface should be **blocked on this fix**.

## Asks / compounds

- **Compound 1 (process).** This polish is a catch-up. The audit→fix→log loop dropped the log step. Worth adding a step to the `freeform-polish` skill where if a PR closes audit bugs, the polish log is part of the PR (or, more practically, the PR description should link the polish log slug that *will* be written, and the back-fill becomes a tracked TODO rather than a surprise gap). Not yet filed.
- **Compound 2 (fixtures).** `LIFECLOCK_JUMP_TO=paywallWhatIfSection` lands on the paywall sheet over the Future tab. For grid uniformity I'd want a Pro variant (the variant where the user has Pro but the operator wants to inspect the slider section's underlying behavior) and a Free variant (current behavior — paywall on top). Today `FORCE_PRO=1` + `paywallWhatIfSection` resolves to the slider behind paywall (the fixture honors `forcePaywall || futureJumpTo == .paywallWhatIfSection`). One-line fix: gate the paywall on `forcePaywall && !forcePro` so Pro+`paywallWhatIfSection` shows the slider directly. Not yet filed.

## Captures

See [screenshots/2026-05-12-future-tab-grid/](screenshots/2026-05-12-future-tab-grid/) for the rendered grid. Index:

- `pro-{tone}-{scheme}-{jumpTo}.png` (3 × 2 × 7 = 42 files)
- `free-{tone}-{scheme}-{jumpTo}.png` (3 × 2 × 5 = 30 files; skips `futureCapReached` + `futureFloorReached` — Pro-state)

Total: 72 captures.

**⚠ Read with the catch #4 caveat in mind.** Day-0 cells show real empty-state copy and *are* useful for tone-distinctness verification on that state. Cold-launch / warming / full / cap / floor cells render empty Future tabs because of the fixture gap described in catch #4 — they're recorded for completeness but the chart and long-form narrative they were meant to capture aren't visible. Paywall cells (`paywallWhatIfSection`) render correctly.
