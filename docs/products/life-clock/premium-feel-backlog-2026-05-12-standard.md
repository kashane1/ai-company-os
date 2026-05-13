# Life Clock — Premium-Feel Backlog (2026-05-12, standard depth)

> **Skill:** `premium-feel-audit` (canonical: `skills/canonical/premium-feel-audit/skill.md`)
> **Inputs:** `product_id=life-clock`, `baseline=origin/main`, `depth=standard`, `focus=none`, `minimum_prompts=10`
> **Observer:** [`premium-bar.md`](premium-bar.md)
> **Author:** Claude (Opus 4.7 1M), single read-only pass
> **Consumed by:** `simulator-driven-polish` — each prompt is copy-pasteable into a fresh session

---

## 1. State summary

Life Clock has shipped 38 polish sessions in the last 14 days. Recon is producing thin/remedial backlogs (per operator memory `feedback_simulator_polish_recon_calibration.md`) — the right next move is elevation, not regression. The app has strong category-by-category foundations: a centralized `Lighting` enum with the world-fixed convention, a centralized `LifeClockHaptics` policy, a `DesignTokens` enum, and explicit reduce-motion gating on the wake animation and clock-hand reveal. Where it falls short of `premium-bar.md` is **system coherence**: animation durations vary across 0.18/0.22/0.25/0.30/0.40/0.60/1.4/2.2s with no shared tier vocabulary (rubric demands 100/250/500ms tiers), the Lighting enum only has two call sites (mascot hand + trajectory chart) while WrapUp's clock face and most cards lack it, loading states are bare `ProgressView()` + literal `"Loading…"`/`"Loading subscription options…"` strings on 8 surfaces, and two empty states (`DayDetailView`, `OverrideSheet`) still read `"No data persisted for this day yet."` which is on the rubric's anti-signal list. Typography uses fixed `.system(size: 44|32, ...rounded)` on Today and WrapUp instead of `.font(...).fontDesign(.rounded)` against the Dynamic Type scale. **Premium-readiness: yellow.** The Future + WrapUp ceremonial moments are where the bar is held highest, and they're where the gaps will be most visible to a press reviewer.

## 2. Coverage matrix

One row per surface in `premium-bar.md` § "Surface-level rubric." `s/p/w/a` = strong / partial / weak / absent. "Last polish session" lists the most recent log overlapping that surface.

| Surface | Last polish session | Motion | Haptics | Typography | Transitions | Empty states | Loading states | Color and lighting | Microcopy | Open Qs touching | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Today | 2026-05-12 (today-free-vs-pro-and-a11y) | partial | strong | partial | partial | partial | weak | partial | strong | #1, #2, #3, #14 | premium-gap (motion + typography + loading) |
| History | 2026-05-11 (history-day1-empty-state-tones) | partial | weak | partial | weak | partial | absent | weak | partial | none | premium-gap (transition-snag + lighting-gap + loading-bare) |
| Future | 2026-05-12 (whatif-slider-scrub-feel; trajectory-chart-a11y) | partial | strong | partial | partial | partial | weak | partial | partial | none | premium-gap (motion-incoherence on projection reveal) |
| WrapUp | 2026-05-06 (wrapup-sequencing-foreground-cycles) | weak | partial | weak | partial | n/a | n/a | weak | strong | none | premium-gap (typography-drift + lighting-gap + motion-incoherence on durations 1.4/2.2s) |
| Quest detail / QuickLog | 2026-05-11 (quicklog-drift-and-q11-narration); 2026-05-09 (quest-completion-payoff) | partial | strong | partial | partial | partial | weak | partial | partial | #11, #14 | premium-gap (loading-bare + transition-snag) |
| Profile | 2026-05-09 (profile-section-sweep) | partial | partial | partial | partial | weak | weak | partial | partial | none | premium-gap (loading-bare + lighting-gap on cards) |
| Paywall (motion / typography / haptics only — value is pro-value-audit) | 2026-05-10 (subscription-lifecycle-states) | weak | weak | weak | partial | n/a | weak | partial | weak | #12 | premium-gap (motion-incoherence + microcopy-flab "Loading subscription options…") |
| Onboarding (visual coherence only — funnel is recon) | 2026-05-12 (vision-q9-reveal-escalator-tone-mocks); 2026-05-06 (vision-terminal-onboarding-screens) | partial | partial | partial | partial | n/a | partial | partial | strong | #9 (resolved), #10 (resolved) | premium-aligned with transition-snag risk on RevealEscalator |

## 3. Open Questions ledger

Every `vision.md` Open Question + current status + which emitted prompt (if any) targets it.

| # | Title | Status | Targeted by |
|---|---|---|---|
| 1 | Negative-feedback intensity | Open (V1+V2 softened pools 5/7+5/10) | none — outside premium-bar |
| 2 | Should users be able to hide the clock? | Open, strategic | none — feature scope |
| 3 | Minimum daily manual log threshold | Open | none — feature scope |
| 4 | Visualizing uncertainty without weakness | Open | none — feature scope |
| 5 | Pro daily-loop differentiation | Open | not this skill (pro-value-audit) |
| 6 | First-paywall placement | Open | not this skill (pro-value-audit) |
| 7 | Streak treatment | **Resolved 2026-05-06** | n/a |
| 8 | Tone-mode discoverability | Open | none — feature scope |
| 9 | Reveal-escalator tone-awareness | **Resolved 2026-05-12** | n/a |
| 10 | Onboarding lead-in copy register | **Resolved 2026-05-11** | n/a |
| 11 | QuickLogSheet narration | Open (Stretch) | none — content/policy, not premium |
| 12 | Paywall headline tone | Open (Stretch + marketing review) | **P11** (premium-feel touches motion/typography/microcopy of paywall, NOT value-copy) |
| 13 | DayDetailView heading divergence | Open (Polish) | none — covered by next polish pass |
| 14 | Daily quest completion payoff (A / B / C) | Open (Feature) | **P9** (vision-driven) |
| 15 | Wrap-ups push vs pull | **Resolved 2026-05-09** | n/a |
| 16 | Morning vs evening reminder | **Resolved 2026-05-09** | n/a |
| 17 | SafetyNet → softer Lock-Screen copy | **Resolved 2026-05-09** | n/a |
| 18 | Re-engagement nudges in v1 | **Resolved 2026-05-09** | n/a |
| 19 | 8…22 hour clamp | **Resolved 2026-05-09** | n/a |

## 4. Memory ledger

Every operator-memory entry consulted + how the emitted backlog respects it.

| Memory file | Relevance | Honored by |
|---|---|---|
| `feedback_life_clock_lighting_convention.md` | Binding constants (opacity 0.22, offset 0.35/0.85, radius 0.55× reference, world-fixed via inverse-rotation). | **P5** + **P7** explicitly cite the convention and require the existing `Lighting.lightingDepth(referenceSize:)` / `lightingRotatedDepth(referenceSize:angle:)` modifiers. No prompt proposes new shadow values. |
| `feedback_life_clock_wake_animation.md` | Wake plays on every app open (cold + foreground), 1.0s total envelope, reduce-motion-gated. | **P3** (duration-tier sweep) excludes the wake from the 250/500ms retier — the 1.0s "greeting" envelope is the operator-chosen value and must not be reduced. **P10** (reduce-motion sweep) keeps the existing wake gate. |
| `feedback_life_clock_notifications_constraints.md` | Five rules: one notification class, evening, 8…22 clamp, wrap-ups pull-not-push, lock-screen copy follows in-app tone. | No prompt in this backlog touches notifications. **P11** (paywall premium pass) does not propose any push-based prompts. |
| `feedback_simulator_polish_recon_calibration.md` | Recon on polish-saturated products skews remedial → invoke `premium-feel-audit` for elevation. | This skill IS that invocation. The backlog deliberately avoids drift-sweep prompts that recon would emit. |
| `feedback_xcode_build_loop.md` | Headless `xcodebuild` iteration. | Tangential — not cited by any emitted prompt. |
| `feedback_computer_use_default_apps.md` | Batch app permission requests. | Tangential — used only by the consuming `simulator-driven-polish` sessions, not by this backlog. |

No memory entry contradicts any emitted prompt.

## 5. Fixture knob catalog

Knobs the consuming `simulator-driven-polish` sessions will reach for. Source: `products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift`.

| Knob | Values | Premium-feel use |
|---|---|---|
| `LIFECLOCK_UI_TEST_SCENARIO` | `onboarding` (default) / `onboarded` | Land on a populated Today/History/Future grid for typography + motion screenshots. |
| `LIFECLOCK_UI_TEST_AUTHORIZED` / `LIFECLOCK_HEALTH_AUTH` | `1` / `authorized\|denied\|notDetermined` | Drives loading-state visibility on Profile + Today; needed for P2 spinner sweep. |
| `LIFECLOCK_FORCE_PALETTE` | `default-navy\|aurora-cool\|sunset-warm` | Drives lighting + palette parity sweeps (P5, P6). |
| `LIFECLOCK_FORCE_COLOR_SCHEME` | `light\|dark` | Required for dark-mode parity sweep (P6). |
| `LIFECLOCK_SEED_TONE` | `gentle\|coach\|firm_direct` | Required for tone-aware microcopy passes (P4 empty-state copy, P12 microcopy density). |
| `LIFECLOCK_HEALTH_PROFILE` | `baseline\|poor\|empty` | `empty` triggers the bare-Today loading paths; `poor` exposes the bad-day text-on-secondary contrast and forces the negative-WrapUp motion path (P3). |
| `LIFECLOCK_SEED_BAD_DAY` | `1` | Co-composes with `poor` for ~−90 min frame; used to capture the WrapUp negative motion + lighting (P7). |
| `LIFECLOCK_INITIAL_TAB` | `today\|history\|profile` | Lands on non-Today surfaces; needed for P5 lighting sweep, P10 reduce-motion sweep. |
| `LIFECLOCK_JUMP_TO` | `futureDay0\|futureColdLaunch\|futureWarmingUp\|futureFull\|futureCapReached\|futureFloorReached\|paywallWhatIfSection` | Lands on Future-tab states for the projection-reveal reference match (P8). |
| `LIFECLOCK_FORCE_QUICK_LOG` | `1` | Deterministic QuickLogSheet present for P2 loading + P12 microcopy. |
| `LIFECLOCK_FORCE_SAFETY_NET` | `1` | Lands directly on SafetyNet for transition-coherence check (P10). |
| `LIFECLOCK_FORCE_PAYWALL` / `LIFECLOCK_JUMP_TO=paywallWhatIfSection` | `1` / — | Required for paywall premium pass (P11). |
| `LIFECLOCK_SEED_LAST_LOG_DAYS_AGO` | int | Drives empty-then-fill transition path for History after long absence (P10). |
| `LIFECLOCK_SEED_DAYS_SINCE_INSTALL` | int | Day-1 vs day-30 typography hierarchy sweep on History/Future. |
| `LIFECLOCK_SEED_BASELINE_ADJUSTMENT` | float | Required to render Future projections under P8. |

## 6. The prompts

Fourteen prompts. Every prompt uses the binding 9-field template from `skills/canonical/shared/recon-scaffolding.md`. Every prompt cites `premium-bar.md` + a specific category.

---

### 1. Typography fixed-size sweep (fix-list)

> **Tier:** typography-drift
>
> **Evidence:** `premium-bar.md` § Typography ("Scale: one type scale across the app … Random sizes off the scale = `typography-drift`"; "Fixed-size copy outside the brand-approved exceptions = `typography-drift`"); `products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift:55` (`.font(.system(size: 44, weight: .semibold, design: .rounded))`); `products/life-clock-ios/Sources/Features/Today/TodayView.swift:293` (same); `products/life-clock-ios/Sources/Features/History/OverrideSheet.swift:26` (`.font(.system(size: 32, weight: .semibold, design: .rounded))`).
>
> **Idea:** Three call sites bypass Dynamic Type with fixed pt sizes (44pt on Today/WrapUp delta readout, 32pt on OverrideSheet). The rounded design is on-brand but the fixed size is not. Either replace with `.font(.largeTitle.weight(.semibold)).fontDesign(.rounded)` (and `.title.weight(.semibold)` for OverrideSheet) so Dynamic Type scales it, OR add an explicit `DesignTokens.Typography.numericDisplay` entry in the design-tokens enum that documents the exception and pairs the fixed size with a min/max via `.minimumScaleFactor` + `.dynamicTypeSize(.large ... .xxLarge)` clamping. The hero number on Today and WrapUp is the canonical exception case for premium products; treat it as the ONE exception with a clamp, not as an unaudited fixed point.
>
> **Surfaces:** [WrapUpSheet.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift):55, [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift):293, [OverrideSheet.swift](../../../products/life-clock-ios/Sources/Features/History/OverrideSheet.swift):26
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_FORCE_COLOR_SCHEME=light`, plus screenshot grid across `dynamicTypeSize` `.xSmall`, `.large`, `.accessibility3`.
>
> **Prior context:** none for fixed-size audit specifically. `polish-2026-05-12-trajectory-chart-a11y-colorblind-xxl.md` covered the chart at XXL; this prompt extends the discipline to the three numeric-display sites.
>
> **Success criteria:** All three call sites either (a) use `.font(...)` with a Dynamic Type style + `.fontDesign(.rounded)`, OR (b) reference a single `DesignTokens.Typography.numericDisplay` token whose docstring records the exception. XXL screenshot doesn't truncate the delta number; xSmall doesn't shrink it below 30pt visual.
>
> **Iteration cap:** 3 (fix-list mode default)
>
> **Final computer-use checkpoint:** yes — review the XXL vs xSmall screenshot pair on real Simulator; trade-off between brand presence and a11y is operator-grade.

---

### 2. Loading-state brand sweep (fix-list)

> **Tier:** loading-bare
>
> **Evidence:** `premium-bar.md` § Loading states ("On-brand: loading states use brand-approved indicators (custom Life Clock spinner or skeleton), not the system spinner. System-default-only = `loading-bare`"; anti-signal: "Copy that says 'loading…'"); 8 call sites: `PaywallSheet.swift:78,145,199` (incl. `Text("Loading subscription options…")`), `TodayView.swift:334,349` (incl. `Text("Loading…")`), `Profile/ProfileView.swift:87,108,124,165`, `QuickLogSheet.swift:222`, `History/HistoryView.swift:203`, `Onboarding/OnboardingView.swift:193,228`.
>
> **Idea:** Every visible loading state in the app today is a `ProgressView()` (system spinner) plus a literal `"Loading…"` / `"Loading subscription options…"` string. Anti-signal-positive on both axes. Choose ONE brand approach and apply it: either (a) a tiny `LifeClockSpinner` view that rotates a single tick-mark of the clock face at 1 rev/2s (matches the world-fixed lighting + the clock identity), or (b) a skeleton view — the row outline with the brand `DesignTokens.Palette.elevated` background pulsing at the `breath` tier (500ms). For copy, replace `"Loading…"` with a brand verb: `"Reading your day…"` (Today HealthKit recompute), `"Reading your plan…"` (subscription products), `"Catching up…"` (Profile auth) — each tone-aware via `ToneMode`. Restore-purchase spinner stays as system per Apple HIG conformance — flag the one exception explicitly in code.
>
> **Surfaces:** [PaywallSheet.swift](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift):78, :145, :199; [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift):334, :349; [ProfileView.swift](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift):87, :108, :124, :165; [QuickLogSheet.swift](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift):222; [HistoryView.swift](../../../products/life-clock-ios/Sources/Features/History/HistoryView.swift):203
>
> **Fixture knobs:** `LIFECLOCK_HEALTH_AUTH=notDetermined` + `LIFECLOCK_FORCE_QUICK_LOG=1` for the QuickLog spinner; `LIFECLOCK_FORCE_PAYWALL=1` for paywall; `LIFECLOCK_SEED_TONE=gentle\|coach\|firm_direct` to cover tone-aware copy.
>
> **Prior context:** `polish-2026-05-10-subscription-lifecycle-states.md` audited subscription lifecycle but kept the system spinner; `polish-2026-05-10-healthkit-denied-notdetermined-paths.md` covered HK denied-path copy but not the loading visual.
>
> **Success criteria:** Zero literal `Text("Loading…")` / `Text("Loading subscription options…")` strings outside the documented restore-purchase exception. All non-restore loading visuals use one brand component (either `LifeClockSpinner` or skeleton — operator picks one in-session). Tone-aware copy is per-tone, not generic.
>
> **Iteration cap:** 5 (fix-list with copy work; spinner component is the long tail)
>
> **Final computer-use checkpoint:** yes — the spinner-vs-skeleton choice deserves a side-by-side screenshot before locking the component.

---

### 3. Animation-duration tier coherence sweep (freeform-polish)

> **Tier:** motion-incoherence
>
> **Evidence:** `premium-bar.md` § Motion ("Durations: every named animation has a duration that fits one of three brand-defined tiers (instant 100ms, beat 250ms, breath 500ms). Random durations = `motion-incoherence`"). Current state: durations across the codebase are 0.18s (chart smooth, paywall scroll), 0.22s (mascot scale), 0.25s (ClockHandView reveal pulse, RevealEscalator cycle), 0.30s (mascot scale fall-back), 0.40s (mascot scale rise), 0.60s (mascot scale settle), 1.0s (Today wake — operator-pinned per memory), 1.4s (yesterday WrapUp), 2.2s (weekly WrapUp). Nine distinct durations across 9 sites. Even excluding the operator-pinned 1.0s wake, the remaining 8 don't align to 100/250/500.
>
> **Idea:** Define `Motion.Duration.instant` (0.10), `.beat` (0.25), `.breath` (0.50) in a new `products/life-clock-ios/Sources/Shared/Motion.swift` alongside the existing `Lighting.swift`. Migrate non-pinned sites: chart `.smooth(duration: 0.18)` → `.beat`, paywall `.smooth(duration: 0.18)` → `.beat`, ClockHandView `.easeInOut(0.25)` → `.beat`, mascot keyframe `0.22/0.30/0.40/0.60` → consider collapsing to `.beat` rise + spring settle (operator decision), WrapUp yesterday 1.4s → `2 × .breath + spring tail` decomposition. Preserve the wake's 1.0s envelope (per `feedback_life_clock_wake_animation.md`) and document it as the lifecycle-pinned exception. WrapUp's 1.4s + 2.2s also need an operator call: are these "yesterday-breath × 3" + "weekly-breath × 4" composed values, or freeform ceremonial durations earned by the moment? Lean toward the former; the latter is the only justifiable exception.
>
> **Surfaces:** [TrajectoryChart.swift](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift):140, [PaywallSheet.swift](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift):61, [ClockHandView.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift):78, :86, [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift):474–476, :490–492, [WrapUpSheet.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift):33–38, [RevealEscalatorScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift):435
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_SEED_BAD_DAY=1` (to capture negative-WrapUp motion), `LIFECLOCK_JUMP_TO=futureFull` (to capture chart smooth).
>
> **Prior context:** `polish-2026-05-05-today-screen-morning-greeting.md` resolved the wake envelope; `polish-2026-05-12-whatif-slider-scrub-feel.md` audited scrub haptics (not durations).
>
> **Success criteria:** A new `Motion.Duration` enum exists with three named tiers. All animation duration literals in `Features/**/*.swift` either reference the enum, or are documented as lifecycle-pinned exceptions with a one-line rationale comment (wake = 1.0s greeting; WrapUp ceremonial durations if operator keeps them freeform). The number of distinct numeric duration literals in `Features/` drops from 9 to ≤2 (the wake + at most one ceremonial WrapUp value).
>
> **Iteration cap:** 6 (freeform sweep)
>
> **Final computer-use checkpoint:** yes — motion coherence has to be felt; record a 10s clip of cold launch → quest tap → WrapUp open and watch for rhythm.

---

### 4. Empty-state specificity + affordance sweep (freeform-polish)

> **Tier:** empty-state-flat
>
> **Evidence:** `premium-bar.md` § Empty states ("Specificity: every empty state has copy that addresses the specific empty condition … Generic 'No data' = `empty-state-flat`"; "Action affordance: every empty state offers at least one next-step the user can take. Dead-end empty = `empty-state-flat`"); anti-signal: "Empty states that end with 'no data' and no next step." Current offenders: `DayDetailView.swift:40` (`"No data persisted for this day yet."`), `OverrideSheet.swift:76` (`"No data for this day yet."`), `ProfileView.swift:466` (`badge.earned.isEmpty` branch — needs a check), `PlanEditorSheet.swift:160` (`variants.isEmpty`), `FutureView.swift:328` (`store.sliderOverrides.isEmpty`).
>
> **Idea:** Walk each empty branch and produce a tone-aware specific copy + one affordance. DayDetailView empty → `"This day landed before you started logging. Want to backfill?"` + button to OverrideSheet; OverrideSheet empty (you're already there) → `"No baseline saved yet — your override will start the record."` (no button needed; the form IS the affordance); ProfileView earned-badges-empty → `"Your first badge is one logged day away."` + tone-aware variant + link to Today; PlanEditor variants-empty → `"No plan variants seeded for this slot. Switch plan archetype above to see options."`; FutureView slider-overrides-empty → `"Drag a slider above to see how it bends your trajectory."` (this one is closer to a teaching state than empty — preserve it but tighten copy). Brand-coherence: each variant gets a `ToneMode.gentle/coach/firmDirect` rendering where copy applies.
>
> **Surfaces:** [DayDetailView.swift](../../../products/life-clock-ios/Sources/Features/History/DayDetailView.swift):40, [OverrideSheet.swift](../../../products/life-clock-ios/Sources/Features/History/OverrideSheet.swift):76, [ProfileView.swift](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift):466, [PlanEditorSheet.swift](../../../products/life-clock-ios/Sources/Features/Today/PlanEditorSheet.swift):160, [FutureView.swift](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift):328
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded` + `LIFECLOCK_SEED_DAYS_SINCE_INSTALL=0` for DayDetailView/OverrideSheet pre-baseline; `LIFECLOCK_SEED_TONE=gentle\|coach\|firm_direct` grid.
>
> **Prior context:** `polish-2026-05-11-history-day1-empty-state-tones.md` covered History day-1 specifically (not DayDetailView pre-baseline); `polish-2026-05-09-profile-section-sweep.md` covered Profile layout but not the badge-empty branch copy specifically.
>
> **Success criteria:** Zero literal `"No data"` strings remain in `Features/`. Each empty branch above has tone-aware copy + (where applicable) a next-step button. The empty-state component (if extracted) lands in `Sources/Shared/EmptyStateView.swift` with a `(headline, body, action?)` signature so future surfaces inherit the bar.
>
> **Iteration cap:** 5 (freeform sweep + tone variants)
>
> **Final computer-use checkpoint:** yes — empty states are tone-sensitive; review one tone × one surface × one scheme before broad rollout.

---

### 5. Lighting convention call-site extension sweep (freeform-polish)

> **Tier:** lighting-gap
>
> **Evidence:** `premium-bar.md` § Color and lighting ("Lifecycle-pinned lighting: rotating/dial elements respect the world-fixed lighting convention … See operator memory `feedback_life_clock_lighting_convention.md`. Lighting drift = `lighting-gap`"). Existing call sites: 2 — `LifeClockMascotView.hand()` (rotating, via `lightingRotatedDepth`) and `TrajectoryChart` container (non-rotating, via `lightingDepth`). Per the memory itself: "it can be lifted into a shared `Lighting` enum + `liftedShadow(size:)` … when a third call site appears (DRY trigger)." Multiple unlit surfaces remain: `WrapUpSheet`'s `ClockHandView` clock face (the *primary* ceremonial moment), the Today plan-quest cards, the History summary card, the Profile badge tiles, the `SupportMomentCard`.
>
> **Idea:** Walk each card/elevated surface in the app and decide: (a) "depth-shadow worthy" → apply `.lightingDepth(referenceSize:)` with the card's height as reference; (b) "rotating depth-shadow worthy" → apply `.lightingRotatedDepth(...)` (ClockHandView in WrapUp is the canonical second rotating site); (c) "flat by design" → document on the call site why (e.g., List rows inside a Form should NOT carry the world-fixed shadow — Form already paints elevation). The audit IS the third call site that fires the DRY trigger from the memory, so this work earns the `liftedShadow(size:)` / `rotatingLiftedShadow(size:angle:)` extraction the memory anticipated.
>
> **Surfaces:** [ClockHandView.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift) (whole file — rotating clock face), [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) plan-quest card region, [HistoryView.swift](../../../products/life-clock-ios/Sources/Features/History/HistoryView.swift) summary card, [ProfileView.swift](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift):500–520 (badge tiles), [SupportMomentCard.swift](../../../products/life-clock-ios/Sources/Shared/SupportMomentCard.swift)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_FORCE_COLOR_SCHEME=light\|dark` grid, `LIFECLOCK_FORCE_PALETTE=default-navy\|aurora-cool\|sunset-warm` grid.
>
> **Prior context:** `polish-2026-05-06-accessibility-color-matrix.md` audited contrast but not lighting; the lighting memory explicitly identifies this DRY moment.
>
> **Success criteria:** Every elevated card surface in `Features/` either applies `Lighting`'s modifiers or carries a one-line comment justifying the omission. The mascot face clock + WrapUp ClockHand clock face look like they share a light source in a side-by-side screenshot. `Lighting` enum may grow a thin convenience extension (`liftedShadow(size:)`) but constants stay where they are.
>
> **Iteration cap:** 4 (freeform with three palette × two scheme grid)
>
> **Final computer-use checkpoint:** yes — lighting coherence is the strongest reviewer-eye signal and must be checked across both schemes + all three palettes.

---

### 6. Dark-mode parity sweep on non-Today surfaces (freeform-polish)

> **Tier:** lighting-gap
>
> **Evidence:** `premium-bar.md` § Color and lighting ("Light + dark parity: every surface looks intentional in both modes. Dark-mode afterthought = `lighting-gap`"); anti-signal: "Light-mode-only thinking ('we'll fix dark later')." Today + Onboarding have been audited under multiple polish passes for scheme parity; History, Future projection cards, Profile cards, QuickLogSheet, and WrapUp's negative-delta `DesignTokens.Palette.negative` (Color.orange) tint have not been swept against the dark-mode palette as a single coherent pass.
>
> **Idea:** Capture light+dark × default-navy/aurora-cool/sunset-warm × `onboarded`-seeded screenshots for History summary card, Future trajectory chart container, Profile badge grid, QuickLogSheet section headers, and WrapUp negative-state. For each, score "intentional in both modes" or "afterthought." Common failure modes: orange-on-dark looking muddier than orange-on-light, secondary-system-background lacking the lift it has in light mode, card edges disappearing in dark scheme due to the lighting shadow becoming invisible against `Color(.systemBackground)`. The fix is usually one of: (a) tighten the `DesignTokens.Palette.elevated` for dark scheme, (b) add a hairline border to cards in dark mode only, (c) raise lighting opacity from 0.22 to 0.28 in dark mode (operator-approval needed — would amend the lighting memory). DO NOT silently change the lighting constants; surface the question if the gap is real.
>
> **Surfaces:** [HistoryView.swift](../../../products/life-clock-ios/Sources/Features/History/HistoryView.swift), [FutureView.swift](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift), [ProfileView.swift](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift), [QuickLogSheet.swift](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift), [WrapUpSheet.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift), [DesignTokens.swift](../../../products/life-clock-ios/Sources/Shared/DesignTokens.swift)
>
> **Fixture knobs:** `LIFECLOCK_FORCE_COLOR_SCHEME=light\|dark`, `LIFECLOCK_FORCE_PALETTE=default-navy\|aurora-cool\|sunset-warm`, `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_SEED_BAD_DAY=1` (for the negative WrapUp dark path).
>
> **Prior context:** `polish-2026-05-06-accessibility-color-matrix.md` audited contrast for a11y. This sweep is parity, not contrast — they overlap on the AA pairs but the question is different.
>
> **Success criteria:** A 5-surface × 2-scheme × 3-palette = 30-cell visual matrix screenshotted into `docs/products/life-clock/research/dark-parity-2026-05-12/`. Each cell is annotated "intentional / afterthought." A polish session log lists the ≤5 highest-leverage fixes (probably hairline borders + elevated tint). If the lighting opacity question surfaces, it's flagged as a vision-question pointer to the operator, not silently changed.
>
> **Iteration cap:** 4 (freeform sweep — visual judgment per cell)
>
> **Final computer-use checkpoint:** yes — operator review the 30-cell matrix; mode choice is product-grade.

---

### 7. WrapUp clock-face lighting reference-match against the app icon (reference-match)

> **Tier:** lighting-gap
>
> **Evidence:** `premium-bar.md` § Color and lighting + § Surface-level rubric ("WrapUp: motion (sequenced reveal), haptics on each reveal beat, microcopy tone, lighting on the clock face"); operator memory `feedback_life_clock_lighting_convention.md` ("Founder has the iOS app icon (a 3D-rendered clock) as the visual reference for the whole app. The icon's rendering implies a fixed light source above; shadows on UI elements should read as lit by the same light to make the app feel cohesive instead of slapped-together."). Current state: WrapUp's `ClockHandView` does not apply `lightingRotatedDepth(...)` to its rotating hand and does not apply `lightingDepth(...)` to the clock face. The mascot's hand does. So the two clock faces in the app — the mascot one on Today (lit) and the WrapUp ceremony one (unlit) — read as not-the-same-clock.
>
> **Idea:** Open the app icon side-by-side with the WrapUp screen. The icon dictates the light source: upper-left, slight rightward bias, casting shadow toward bottom-right. Apply `.lightingRotatedDepth(referenceSize: handThickness, angle: handAngle)` to the WrapUp `ClockHand` view (same pattern as `LifeClockMascotView.hand()`), and `.lightingDepth(referenceSize: faceDiameter * 0.04)` to the face circle (the rim depth, per the inner-shadow guidance in the memory). Verify against the icon: does the WrapUp ceremony moment feel like the icon brought to life, or like a different artifact? Iterate `referenceSize` until they match.
>
> **Surfaces:** [ClockHandView.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift) — whole file is in scope; the `Shape` for the hand and the `Circle` for the face are the targets.
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_SEED_BAD_DAY=1` (so the WrapUp presents on cold launch), `LIFECLOCK_FORCE_COLOR_SCHEME=light\|dark`. Reference: the app icon at `products/life-clock-ios/Assets.xcassets/AppIcon.appiconset/` (or whichever asset slug is canonical at audit time).
>
> **Prior context:** `polish-2026-05-06-wrapup-sequencing-foreground-cycles.md` audited WrapUp present-conditions, not lighting.
>
> **Success criteria:** WrapUp's `ClockHand` + face render with the same world-fixed lighting as the mascot hand on Today. Operator confirms side-by-side with the icon that the three feel like one product. No deviation from the lighting constants — if a value needs adjusting, that's a memory amendment and routes to the operator.
>
> **Iteration cap:** 4 (reference-match mode default)
>
> **Final computer-use checkpoint:** yes — this is a reference-match against an external artifact (the icon); operator eye is the only valid arbiter.

---

### 8. Future projection-reveal animation match against a premium graphing reference (reference-match)

> **Tier:** motion-incoherence
>
> **Evidence:** `premium-bar.md` § Motion ("Animation curves: every animated transition uses a curve from the brand-approved set (eased cubic for navigation, spring for direct manipulation, linear only for indeterminate progress)") + § Surface-level rubric ("Future: motion (the projection animation), typography hierarchy across the trajectory cards, transition to detail screens"). The Future tab's trajectory chart enters with `.smooth(duration: 0.18)` (`TrajectoryChart.swift:140`). 0.18s is "fast enough to not feel slow" but is not a tier value and is not a ceremonial reveal — the projection IS the Future tab's headline moment and currently lands with the same curve a generic chart would use.
>
> **Idea:** Reference is Apple Fitness's monthly-summary chart reveal OR Streaks' goal-line draw (operator pick). What those products do: the line draws in over 600–800ms with an eased cubic, the axis labels fade in after the line lands, and the cap/floor zone (if any) tints in last. Right now Life Clock's chart just appears on `.smooth(0.18)`. Replace with a coordinated reveal: `Path.trim(from:to:)` `.beat → .breath` animation (250–500ms) that draws the trajectory, then a separately-delayed fade of the cap/floor zones (`.beat` after the line lands), then the WhatIf slider thumb springs in (`.bouncy` spring). Reuse the same reveal on first-open of Future tab (cold launch on `futureFull`) and gate it behind a "seen-once" flag so subsequent tab switches use the faster `.beat` redraw. Reduce-motion path: line + zones appear without trim animation, just fade.
>
> **Surfaces:** [TrajectoryChart.swift](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift):139–141, [FutureView.swift](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift)
>
> **Fixture knobs:** `LIFECLOCK_INITIAL_TAB=future`, `LIFECLOCK_JUMP_TO=futureFull`, `LIFECLOCK_SEED_BASELINE_ADJUSTMENT=2.5`, `LIFECLOCK_SEED_DAYS_SINCE_INSTALL=30`.
>
> **Prior context:** `polish-2026-05-11-future-tab-v1.7.0-audit-followup.md` covered Future v1.7.0 phase 4 follow-ups; `polish-2026-05-12-trajectory-chart-a11y-colorblind-xxl.md` covered chart a11y. Neither addressed the *reveal feel*.
>
> **Success criteria:** First-open of Future tab (cold launch, `futureFull`) plays a coordinated reveal: line draws over 250–500ms, then zones tint in over `.beat`, then slider thumb springs in. Subsequent tab switches in same session use the cached `.beat` redraw. Reduce-motion path is a static cross-fade. Side-by-side video against the chosen reference shows comparable craft.
>
> **Iteration cap:** 5 (reference-match with motion experiment)
>
> **Final computer-use checkpoint:** yes — record both side-by-side; the reveal must earn the comparison.

---

### 9. Quest-completion payoff (vision-driven — Open Q14)

> **Tier:** vision-question
>
> **Evidence:** `premium-bar.md` § Motion + § Haptics + § Microcopy (this question pulls from all three); `vision.md` Open Question #14 ("Daily quest completion payoff. … Surfaced 2026-05-08 by simulator-driven-polish in vision-driven mode. … Feature-tier — do not ship autonomously. Options: A Mascot reacts, B Clock hand advances by the quest delta, C Tone-aware micro-copy.").
>
> **Idea:** This is the most concrete elevation moment in the vision Open Questions and currently sits as three documented options (A / B / C) plus the existing implementation (row flip + scrolls-to-keep-visible + support card "+18 min" line). The session running this prompt picks ONE option (or a combination) under operator review:
> - Option A (mascot pulse 1.00 → 1.045 → 1.00 over 520ms + 0.22-opacity warm highlight respecting the lighting convention world-fixed offset 0.35/0.85, radius 0.55×; `.sensoryFeedback(.success)`)
> - Option B (clock hand advances by quest delta, 900ms reveal + 350ms hold + 250ms settle; `.impact(.light, intensity: 0.7)` start + `.success` land; preserve "tomorrow's trajectory update is canonical truth")
> - Option C (tone-aware micro-copy: Gentle `"You bought back +18 minutes today."`, Coach `"Banked: +18 min."`, Firm/Direct `"+18 min. Logged."`; `.selection` on tap + `.success` on appear)
>
> Premium-feel lens (this skill's contribution to the question, beyond what vision-Q14 already framed): all three options must respect the lighting convention from operator memory, the Motion duration tiers from P3 (so the 520ms in A is the `breath` tier, the 900ms in B is `2 × .breath - tail`, the 250ms in C is `.beat`), and the haptics policy in `LifeClockHaptics.swift` (don't introduce a new haptic that contradicts the existing `questCompletion = .success`). Reduce-motion path must exist for every option. The "pick one or compose" decision is operator-grade.
>
> **Surfaces:** [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) (the quest-row + support-card region), [LifeClockMascotView.swift](../../../products/life-clock-ios/Sources/Shared/LifeClockMascotView.swift) (Option A target), [LifeClockHaptics.swift](../../../products/life-clock-ios/Sources/Shared/LifeClockHaptics.swift)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_SEED_QUESTS_COMPLETED=0`, `LIFECLOCK_SEED_TONE=gentle\|coach\|firm_direct` (for option C variants).
>
> **Prior context:** `polish-2026-05-08-vision-today-completion-payoff.md` (the surfacing session — read first), `polish-2026-05-09-quest-completion-payoff.md` (follow-up). Q14 still Open.
>
> **Success criteria:** One option (or composition) ships behind operator approval. The shipped behavior respects: Motion duration tiers (from P3), Lighting convention (from operator memory), existing `LifeClockHaptics.questCompletion`, reduce-motion fallback. Vision Q14 moves to Decided constraints with the chosen option + date.
>
> **Iteration cap:** 6 (vision-driven Feature-tier work; expect multiple goldens)
>
> **Final computer-use checkpoint:** yes — Feature-tier never auto-ships; operator picks among the goldens.

---

### 10. Reduce-Motion fallback table sweep (freeform-polish)

> **Tier:** motion-incoherence
>
> **Evidence:** `premium-bar.md` § Motion ("Reduction respect: every animation respects `UIAccessibility.isReduceMotionEnabled`. Missing reduction paths = `motion-incoherence`"). Today's wake (`TodayView.swift`), ClockHandView reveal (`ClockHandView.swift`), and TrajectoryChart snap-back (`TrajectoryChart.swift:30`) explicitly gate on `accessibilityReduceMotion`. The mascot keyframes inside TodayView (lines 474–492), the WrapUp `animationDuration` (lines 33–38), the RevealEscalator cycle (line 435), and the paywall `withAnimation(.smooth(duration: 0.18))` (line 61) do not have an audited fallback.
>
> **Idea:** Build a one-table audit: every `withAnimation` / `.animation` / `KeyframeAnimator` site in `Features/` → does it have a reduce-motion path? Columns: site, current animation, reduce-motion fallback (none / fade-only / static / explicit). Write the table to `docs/products/life-clock/polish-2026-05-12-reduce-motion-fallback-table.md` and apply the trivial fixes inline (any site missing a fallback gets one; default fallback is "no animation, immediate state change unless a haptic + visible state change still reads as feedback"). For RevealEscalator cycling (line 435) and WrapUp 1.4/2.2s timings (33–38), the fallback should be a no-animation cross-fade. For mascot keyframes — they're already scale-based and short; the existing wake gate likely covers them transitively (verify).
>
> **Surfaces:** [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift):474–492, [WrapUpSheet.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift):33–38, [RevealEscalatorScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift):435, [PaywallSheet.swift](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift):61
>
> **Fixture knobs:** Enable Reduce Motion at the Simulator level (Settings → Accessibility → Motion → Reduce Motion ON) + `LIFECLOCK_UI_TEST_SCENARIO=onboarded` + `LIFECLOCK_FORCE_PAYWALL=1` for the paywall path.
>
> **Prior context:** `polish-2026-05-05-today-screen-morning-greeting.md` pinned the wake reduce-motion gate; `polish-2026-05-12-whatif-slider-scrub-feel.md` audited the chart snap-back gate. No comprehensive table exists.
>
> **Success criteria:** A reduce-motion table doc lists every animation site, its fallback, and a status (covered / missing-now-added / N/A). Zero animation sites in `Features/` fail to honor reduce-motion. Spot-check video with RM enabled shows no clipped state transitions.
>
> **Iteration cap:** 4 (freeform with a11y verification)
>
> **Final computer-use checkpoint:** no — table audit + small fixes are mechanical; operator review on the next session is enough.

---

### 11. Paywall motion + typography + microcopy premium pass (NOT value) (freeform-polish)

> **Tier:** microcopy-flab
>
> **Evidence:** `premium-bar.md` § Surface-level rubric ("Paywall: covered by `pro-value-audit`, NOT this skill. Premium-feel-audit walks the paywall surface for motion/typography/haptics only — value-claim concerns are pro-value-audit's territory"); current state: `PaywallSheet.swift:145` `Text("Loading subscription options…")` (microcopy-flab per anti-signals "Copy that says 'loading…'"); `:61` `withAnimation(.smooth(duration: 0.18))` (motion-incoherence with the rest of the app — addressed by P3 but worth a focused paywall pass); `:78,:199` system `ProgressView()` (loading-bare — addressed by P2 but the paywall's restore-purchase path is the documented exception that needs the right call); no `Lighting` modifier on the products list cards (lighting-gap — addressed by P5 but the paywall is a high-stakes commerce surface that deserves an explicit pass).
>
> **Idea:** Single focused session that walks the paywall under `LIFECLOCK_FORCE_PAYWALL=1` and applies: P3's `Motion.Duration.beat` to the `:61` smooth transition; P2's brand spinner + tone-aware copy (`"Reading your plan…"` instead of `"Loading subscription options…"`); P5's `lightingDepth` to the product-tier card surfaces; the existing brand color palette to any default-tint accents. Do NOT change value claims, headlines, pricing display, or trial framing — those belong to `pro-value-audit` and Vision Open Q12. This prompt is the premium-feel polish of the paywall housing, not its sell. After this lands, `pro-value-audit` becomes the right next step for the housing's content.
>
> **Surfaces:** [PaywallSheet.swift](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift):61, :78, :145, :199, :236+
>
> **Fixture knobs:** `LIFECLOCK_FORCE_PAYWALL=1` or `LIFECLOCK_JUMP_TO=paywallWhatIfSection`, `LIFECLOCK_FORCE_COLOR_SCHEME=light\|dark`, `LIFECLOCK_SEED_TONE=gentle\|coach\|firm_direct`.
>
> **Prior context:** `polish-2026-05-10-subscription-lifecycle-states.md` (lifecycle, not premium); `polish-2026-05-10-protouchpoints-t8-baseline-repair.md` (Pro touchpoints, not paywall itself).
>
> **Success criteria:** Paywall housing reads as premium: tier cards have the lighting convention, transitions land on `Motion.Duration` tiers, loading copy is a brand verb, system spinner reserved for the documented restore-purchase exception. Value claims unchanged. Open Q12 still Open — that's a vision question, not a premium-feel one.
>
> **Iteration cap:** 5 (freeform; paywall is high-stakes)
>
> **Final computer-use checkpoint:** yes — paywall is the commerce surface; operator review every change.

---

### 12. Microcopy density terse-sweep across surfaces (freeform-polish)

> **Tier:** microcopy-flab
>
> **Evidence:** `premium-bar.md` § Microcopy ("Density: every label is as short as it can be without sacrificing clarity. Wordy labels in terse contexts = `microcopy-flab`"; "Voice: copy reads like the canonical voice (terse over chatty, confident over hedged, specific over generic — per [vision.md](vision.md)). Hedged or generic copy = `microcopy-flab`"). Candidate sites: ProfileView section headers (verify density), QuickLogSheet intro pair ("A few quick signals help your Life Clock stay honest." / "No calorie counting. No judgment." — already flagged in vision Q11 as Stretch-tier needing operator approval before tone-aware re-render; this prompt does NOT re-render those — see anti-pattern note below), History scroll labels, Future projection card subtitles, Profile feedback / about / disclaimers.
>
> **Idea:** Walk every visible Text view in non-tone-locked surfaces and ask: "Is this label as short as it can be without losing clarity?" + "Does it read terse over chatty, confident over hedged?" Easy wins are usually section subtitles ("Your Life Clock is calculated from…" → "How your clock reads you"), button captions ("Restore Purchases" — leave per Apple HIG / commerce; "Save Changes" → "Save" where context is unambiguous), and footers. Hard NOs: the three `WelcomeView` / `MeetYourClockView` / `ReactiveSliderView` headlines in `LeadInScreens.swift` (Decided constraint 2026-05-11 — do not touch). The seven QuickLogSheet section labels (vision Q11 — needs operator-yes before changing). The reveal-escalator copy (Decided constraint 2026-05-12). Anti-pattern flagged: do not rewrite anything inside an Open vision question; surface it instead.
>
> **Surfaces:** [ProfileView.swift](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift), [HistoryView.swift](../../../products/life-clock-ios/Sources/Features/History/HistoryView.swift), [FutureView.swift](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift), [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) — non-tone-locked Text views only.
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_SEED_TONE=coach` (default), spot-check `gentle` + `firmDirect` for any copy that turns out to be tone-keyed.
>
> **Prior context:** `polish-2026-05-09-profile-section-sweep.md` reorganized Profile sections; this prompt is the copy-density follow-up. `polish-2026-05-11-quicklog-drift-and-q11-narration.md` tabled Q11 narration — do not reopen.
>
> **Success criteria:** A list of N copy diffs (likely 6–12) is applied. None of them touch tone-locked or Decided/vision-Open copy. Each diff has a one-line rationale ("shorter, same clarity," "less hedged," "more specific"). The app reads tighter without any user-visible meaning lost.
>
> **Iteration cap:** 5 (freeform copy sweep)
>
> **Final computer-use checkpoint:** no — copy diffs are easy to review in a PR. Operator review at PR-time is sufficient.

---

### 13. Today first-reveal motion match against a premium clock reference (reference-match)

> **Tier:** motion-incoherence
>
> **Evidence:** `premium-bar.md` § Motion + § Surface-level rubric ("Today: motion + haptics + typography + transitions + microcopy") + anti-signal "Same event animated differently on two screens." Today's wake animation (1.0s envelope, eased ease-out, mascot keyframe) is operator-pinned and excellent for what it is. But the first reveal of the clock — the moment the user sees the hands move for the first time, post-onboarding — is currently handled by `EngineRevealPresenter` + `LifeClockMascotView` and uses a different curve and timing than the daily wake. The mascot wakes on every open (greeting) but the first reveal is structurally distinct (the clock-engine landing). Premium-feel question: should the first reveal feel **bigger** than the daily wake, or should it feel **like the same gesture, just landed for the first time**?
>
> **Idea:** Reference candidates: Citizen Watch Co's first-power-on (Apple Watch Series 9 review video), Hermès clock-face animation, or — operator pick — a non-watch but high-craft reveal like Things' first-open animation. Compare against Life Clock's current first-reveal flow. The decision is qualitative; codify in a one-page polish log. If "bigger": the first reveal earns a `breath × 2` envelope (1.0s) + a different curve (eased cubic versus the wake's ease-out) + a haptic upgrade (`.firstReveal` is already `.impact(.light)` — leave). If "same gesture, just landed": preserve the wake animation and instead add a brand microcopy line that ONLY appears on first-reveal ("Welcome to your clock." or tone-aware variants), letting the language carry the ceremony rather than the motion.
>
> **Surfaces:** [LifeClockMascotView.swift](../../../products/life-clock-ios/Sources/Shared/LifeClockMascotView.swift), [Shared/EngineRevealPresenter.swift](../../../products/life-clock-ios/Sources/Shared/EngineRevealPresenter.swift), [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarding` (so the engine-reveal moment is the first thing after onboarding completes), `LIFECLOCK_SEED_BASELINE_ADJUSTMENT=0` (pre-anchor state), `LIFECLOCK_SEED_DAYS_SINCE_INSTALL=0`.
>
> **Prior context:** `polish-2026-05-05-today-screen-morning-greeting.md` pinned the wake; `polish-2026-05-05-v2-onboarding-rhythm.md` audited onboarding rhythm. The first-reveal is the bridge between those two and is currently neither.
>
> **Success criteria:** A polish log captures the reference + the decision ("bigger" or "same gesture + copy"). The implementation matches the decision. Side-by-side video against the chosen reference shows comparable craft.
>
> **Iteration cap:** 5 (reference-match)
>
> **Final computer-use checkpoint:** yes — the first reveal is a once-per-user moment; the operator must see the reference + the result.

---

### 14. Transition coherence audit across primary nav (freeform-polish)

> **Tier:** transition-snag
>
> **Evidence:** `premium-bar.md` § Transitions ("Between-screen coherence: push/pop transitions use the same animation system across the app. Mixed default+custom = `transition-snag`"; "Return-to-state preservation: when the user navigates away and back, scroll position, selection, and content state are preserved. Flash-of-default-state on return = `transition-snag`"; "No flash-of-empty-state: push transitions don't reveal an empty state before content loads. Empty-then-fill = `transition-snag`"). Open inspection question: do tabs preserve scroll position? Do sheet presentations (Quest detail, QuickLog, Override, Reflection, Paywall, SafetyNet) use the same `.presentationDetents` / `.presentationDragIndicator` policy? Does Future tab show its empty state before the chart renders on cold launch?
>
> **Idea:** Run a 6-cell coherence audit: (a) Today → History tab → Today (does scroll position persist?) (b) Today → Future tab → Today (does the WhatIf slider position persist?) (c) History → DayDetailView push → back (does History scroll stay?) (d) Profile → SafetyNet sheet → dismiss (does Profile scroll stay? does SafetyNet flash an empty state?) (e) Today → QuickLogSheet → dismiss (does QuickLog flash a loading state?) (f) Future tab cold launch (`futureFull`) — does the chart flash empty before drawing? Document each in a one-row table with status + fix. Common fixes: `@State` lifted to a persistent identity, `.id(stable)`, `.presentationDetents([.medium, .large])` standardization, `task { await preload() }` to mask cold loads. Where a flash-of-empty-state IS happening, P2's spinner refactor is the right pairing — schedule them as a combined polish session.
>
> **Surfaces:** [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift), [HistoryView.swift](../../../products/life-clock-ios/Sources/Features/History/HistoryView.swift), [FutureView.swift](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift), [DayDetailView.swift](../../../products/life-clock-ios/Sources/Features/History/DayDetailView.swift), [PlanEditorSheet.swift](../../../products/life-clock-ios/Sources/Features/Today/PlanEditorSheet.swift), [QuickLogSheet.swift](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift), [PaywallSheet.swift](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_JUMP_TO=futureFull` (for cell f), `LIFECLOCK_FORCE_QUICK_LOG=1` (for cell e), `LIFECLOCK_FORCE_SAFETY_NET=1` (for cell d).
>
> **Prior context:** No prior transition-coherence pass in the 14-day window. Closest: `polish-2026-05-06-wrapup-sequencing-foreground-cycles.md` covered WrapUp present-conditions (not transitions between tabs).
>
> **Success criteria:** A 6-row table is written to a polish log. Each row has status + a one-line fix or "no issue." The high-leverage fixes (typically 2–3) are applied. Cold-launch on Future tab shows no flash-of-empty-state.
>
> **Iteration cap:** 4 (freeform sweep + small fixes)
>
> **Final computer-use checkpoint:** no — coherence findings are mechanical once the table is written; operator review at PR-time is enough.

---

## 7. Variety check

Declared distribution across modes and tiers:

| Mode | Count | Floor | Met? | Prompts |
|---|---|---|---|---|
| `fix-list` | 2 | ≥2 | ✓ | P1, P2 |
| `freeform-polish` | 8 | ≥3 | ✓ | P3, P4, P5, P6, P10, P11, P12, P14 |
| `reference-match` | 3 | ≥2 | ✓ | P7, P8, P13 |
| `vision-driven` | 1 | ≥1 | ✓ | P9 |
| **Total** | **14** | min 10 / max 40 | ✓ | — |

| Tier | Count |
|---|---|
| `typography-drift` | 1 (P1) |
| `loading-bare` | 1 (P2) |
| `motion-incoherence` | 4 (P3, P8, P10, P13) |
| `empty-state-flat` | 1 (P4) |
| `lighting-gap` | 3 (P5, P6, P7) |
| `vision-question` | 1 (P9) |
| `microcopy-flab` | 2 (P11, P12) |
| `transition-snag` | 1 (P14) |

No `submission-blocker`-tier prompts: this audit found no touch-target / a11y-contrast gaps that cross the App Store threshold (those were covered by recent recon passes including `polish-2026-05-06-accessibility-color-matrix.md` and `polish-2026-05-12-today-free-vs-pro-and-a11y.md`).

## 8. Recommended sequencing

**Phase A — foundations the others depend on** (run first):

1. **P3** (motion-duration tier coherence) — defines `Motion.Duration.{instant,beat,breath}`. P8, P9, P10, P11 all reference these tiers.
2. **P5** (lighting convention call-site extension) — fires the "third call site" DRY trigger from operator memory; produces the `liftedShadow(size:)` convenience extension. P7, P6, P11 all depend on this being clean.

**Phase B — coherence sweeps** (run after A):

3. **P1** (typography fixed-size sweep) — quick fix-list, but locks the numeric-display exception cleanly.
4. **P2** (loading-state brand sweep) — produces the brand spinner / skeleton component. P11 depends on it.
5. **P10** (reduce-motion fallback table) — surfaces gaps Phase A fixes might have created.
6. **P4** (empty-state specificity + affordance) — independent; can run in parallel with P10.
7. **P12** (microcopy density terse-sweep) — independent; quick win.

**Phase C — high-craft references** (run after B):

8. **P7** (WrapUp clock-face lighting reference-match) — depends on P5's `lightingRotatedDepth` being available.
9. **P6** (dark-mode parity sweep) — depends on P5 (cards are lit), P1 (typography is consistent), P2 (spinners are branded).
10. **P14** (transition coherence audit) — depends on P2 (the spinner is the right surface to use during transitions).

**Phase D — ceremonial / vision moments**:

11. **P8** (Future projection-reveal reference match) — depends on P3 (uses the tier values) and P10 (reduce-motion fallback baked in).
12. **P13** (Today first-reveal reference match) — depends on P3 + P10.
13. **P11** (paywall premium pass) — depends on P2, P3, P5; commerce surface, run when housing is ready.
14. **P9** (vision-driven Q14 quest-completion payoff) — Feature-tier; should run AFTER Phase A so the chosen option respects the new tier vocabulary and the lighting convention. Operator-grade; budget a full session.

## 9. Readiness flag

**Premium-readiness: yellow.**

Why not green: the strict criteria require zero unresolved `motion-incoherence` / `typography-drift` / `lighting-gap` prompts AND that every `premium-bar.md` category have a polish session log covering it in the last 30 days. Counts in this backlog: 4 `motion-incoherence`, 1 `typography-drift`, 3 `lighting-gap` — all currently unresolved. Premium-bar categories Motion + Typography + Loading states + Color and lighting each have ≤partial coverage on multiple surfaces.

Why not red: zero `submission-blocker` prompts. Zero unaddressed-for-30-days `lighting-gap` or `typography-drift` items (lighting convention itself is fresh in operator memory and centrally enforced; the gaps are extension, not regression). Recent recon coverage on a11y is recent and clean.

**The three prompts that would flip yellow → green:**

1. **P3** (motion-duration tier coherence sweep) — resolves all four `motion-incoherence` tier prompts AND defines the vocabulary that makes future motion work non-regressive.
2. **P5** (lighting convention call-site extension sweep) — fires the third-call-site DRY trigger from operator memory and closes two of the three `lighting-gap` prompts (P6 still needs its own dark-mode pass, but with P5 done it's a smaller delta).
3. **P1** (typography fixed-size sweep) — resolves the single `typography-drift` prompt and documents the numeric-display exception so future Dynamic Type passes don't regress.

After those three land, a re-run of this audit should report green provided P7 (WrapUp clock face) lands within the same 30-day window, since the rubric calls WrapUp's clock-face lighting out as the most visible premium surface.

---

> **Cross-cutting elevation themes (one paragraph for the operator):** The app is *individually* polished across most surfaces but lacks a *system* vocabulary for motion and lighting. Three centrally-defined enums would close most of the gap — `Motion.Duration` (P3), the existing `Lighting` enum extended to one more convenience modifier (P5), and a `LifeClockSpinner` / `EmptyStateView` shared component (P2, P4). Those three artifacts plus the WrapUp clock-face reference match against the app icon (P7) are the highest-leverage moves for elevation. The Feature-tier work (P9, P8, P13) is genuinely exciting but should wait until the system vocabulary is in place — otherwise each new motion choice imports the current incoherence into the next high-craft moment.
