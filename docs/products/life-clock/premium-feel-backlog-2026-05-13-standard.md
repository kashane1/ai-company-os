# Life Clock — Premium-Feel Backlog (2026-05-13, standard depth)

> **Skill:** `premium-feel-audit` (canonical: `skills/canonical/premium-feel-audit/skill.md`)
> **Inputs:** `product_id=life-clock`, `baseline=origin/main` @ `79a10fe`, `depth=standard`, `focus=none`, `minimum_prompts=10`
> **Observer:** [`premium-bar.md`](premium-bar.md)
> **Author:** Claude (Opus 4.7 1M), single read-only pass
> **Consumed by:** `simulator-driven-polish` — each prompt is copy-pasteable into a fresh session

> **⚠️ Cadence override.** Operator explicitly authorized a same-week re-run on 2026-05-13 (24h after the 2026-05-12 standard audit). The 14-day cooling-off rule is honored at the slug level: every prompt from [premium-feel-backlog-2026-05-12-standard.md](premium-feel-backlog-2026-05-12-standard.md) that was closed in commits `47e6870` / `14205c6` / `82d12cf` / `7ebee94` / `0840154` / `4769742` / `81eee24` / `a8c8bcd` is NOT re-emitted. Today's report is therefore a **close-out + delta**: it (a) records that 12 of 14 prior prompts are resolved, (b) carries forward the smoke-test-deferred operator-visual-verifications as their own prompts, (c) surfaces genuinely net-new findings from today's source walk, and (d) ratchets the now-anchored Death Clock premium reference into a reference-match prompt that yesterday's audit could not author.

---

## 1. State summary

Branch `claude/thirsty-golick-bf34df` at `79a10fe` (24h after yesterday's audit baseline `b66cd0e`). In that window the operator landed: foundation artifacts ([Motion.swift](../../../products/life-clock-ios/Sources/Shared/Motion.swift), [LifeClockSpinner.swift](../../../products/life-clock-ios/Sources/Shared/LifeClockSpinner.swift), [EmptyStateView.swift](../../../products/life-clock-ios/Sources/Shared/EmptyStateView.swift), [Lighting.swift](../../../products/life-clock-ios/Sources/Shared/Lighting.swift) extension), seven product specs ([motion-spec.md](motion-spec.md), [lighting-spec.md](lighting-spec.md), [typography-spec.md](typography-spec.md), [paywall-spec.md](paywall-spec.md), [microcopy-spec.md](microcopy-spec.md), [accessibility-spec.md](accessibility-spec.md), [reveal-escalator-spec.md](reveal-escalator-spec.md), [subscription-lifecycle-spec.md](subscription-lifecycle-spec.md), [safetynet-spec.md](safetynet-spec.md), [wrap-up-spec.md](wrap-up-spec.md), [palettes-spec.md](palettes-spec.md), [telemetry-spec.md](telemetry-spec.md), [future-tab-tone-pools-spec.md](future-tab-tone-pools-spec.md), [confidence-model-spec.md](confidence-model-spec.md), [narrative-engine-spec.md](narrative-engine-spec.md)), four Sprints (A pricing+discovery+typography+reduce-motion; B vocabulary adoption; C Pro-signal coherence + paywall premium pass + What-If teaser ratchet; D dark-mode parity + WrapUp full lighting + paywall copy↔delivery), the WrapUp Pro affordance (best-conversion moment #3), the reference-apps anchor (Death Clock + MacroFactor), the sandbox-validation runbook, and today's [smoke-test-2026-05-13.md](smoke-test-2026-05-13.md) verifying every Sprint change on screen with zero visual regressions. The premium-feel coverage map has moved decisively from "polished but incoherent" (yesterday's framing) to "system-grounded, with five small visual deferrals + two micro-residuals." **Premium-readiness: yellow→green pending the five smoke-test-deferred verifications.** Residual concrete findings: (a) one `Text("Loading…")` literal survived the Sprint B2 sweep at [TodayView.swift:350](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift), (b) [OverrideSheet.swift:76](../../../products/life-clock-ios/Sources/Features/History/OverrideSheet.swift) still constructs `"No data for this day yet."` as an error-state string (anti-signal-positive on rubric grounds, even though it's a catch branch and not a static empty state).

## 2. Coverage matrix

One row per surface in `premium-bar.md` § "Surface-level rubric." `s/p/w/a` = strong / partial / weak / absent. Verdicts reflect post-Sprint-D state.

| Surface | Last polish session | Motion | Haptics | Typography | Transitions | Empty states | Loading states | Color and lighting | Microcopy | Open Qs touching | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Today | 2026-05-13 (smoke-test); 2026-05-12 (today-free-vs-pro-and-a11y) | strong | strong | strong (numeric-display exception locked in typography-spec) | partial | partial | **partial** (one residual literal at line 350) | strong (cardLighting on 6 cards verified) | strong | #1–4, #14 (resolved) | premium-aligned with one residual |
| History | 2026-05-13 (smoke-test); 2026-05-11 (history-day1-empty-state-tones) | strong | partial | strong | partial | strong (foggy-paywall card matches EmptyStateView shape) | strong | strong (Sprint D1 dark-mode parity, build-verified) | strong | none | premium-aligned (D1 visual verify deferred) |
| Future | 2026-05-12 (whatif-slider-scrub-feel); 2026-05-13 smoke-test (day0 only) | strong (Motion.Duration migrated) | strong | strong | partial | partial | strong | strong | strong | none | premium-aligned (Sprint C3 proFooter + full14plus visual unseen) |
| WrapUp | 2026-05-13 (smoke-test, code-level); 2026-05-06 (sequencing-foreground-cycles) | strong | strong | strong | partial | n/a | n/a | strong (Sprint D2 full lighting build-verified) | strong | none | premium-aligned (D2 visual verify deferred) |
| Quest detail / QuickLog | 2026-05-11 (quicklog-drift-and-q11-narration); 2026-05-09 (quest-completion-payoff) — Q14 resolved 2026-05-13 | strong | strong | partial | partial | partial | strong | strong | strong | #11 (Open Stretch), #14 (**Resolved 2026-05-13**) | premium-aligned |
| Profile | 2026-05-13 (smoke-test verified Subscription Pro + Free states); 2026-05-09 (profile-section-sweep) | strong | strong | strong | partial | partial | strong | strong | strong | none | premium-aligned |
| Paywall (motion / typography / haptics only — value-claim is pro-value-audit) | 2026-05-13 (smoke-test verified C2 premium pass); 2026-05-12 (Sprint C2) | strong (`.smooth(.beat)` on selection ring) | strong | strong | strong | n/a | strong (`LifeClockSpinner("Loading subscription options…", size: .regular)`) | strong | strong ("Pro adds depth:" terse-sweep) | #12 (Open Stretch) | premium-aligned |
| Onboarding (visual coherence only — funnel is recon) | 2026-05-12 (vision-q9-reveal-escalator-tone-mocks); 2026-05-06 (vision-terminal-onboarding-screens) | partial | partial | partial (3 raw `.system(size:)` calls per typography-spec onboarding-numeric bucket — by-design exception) | partial | n/a | partial | strong | strong (Decided 2026-05-11) | #9, #10 (resolved) | premium-aligned (PaywallPrimaryView D3 visual verify deferred) |

## 3. Open Questions ledger

| # | Title | Status | Targeted by today's backlog |
|---|---|---|---|
| 1–4 | Negative-feedback intensity / hide-clock / minimum manual log / uncertainty-without-weakness | Open | none — outside premium-bar |
| 5 | Pro daily-loop differentiation | Open | not this skill (pro-value-audit) |
| 6 | First-paywall placement | Open | not this skill (pro-value-audit) |
| 7 | Streak treatment | **Resolved 2026-05-06** | n/a |
| 8 | Tone-mode discoverability | Open | none |
| 9 | Reveal-escalator tone-awareness | **Resolved 2026-05-12** | n/a |
| 10 | Onboarding lead-in copy register | **Resolved 2026-05-11** | n/a |
| 11 | QuickLogSheet narration | Open (Stretch, needs operator-yes) | none — explicit anti-pattern hold from yesterday's P12, still held |
| 12 | Paywall headline tone | Open (Stretch + marketing review) | none — value-claim work has now landed (Sprint C2 + D3); tone-conditional paywall copy is still gated on operator |
| 13 | DayDetailView heading divergence | Open (Polish) | **P10** (microcopy alignment sweep — quick win, no vision question, can ride along) |
| 14 | Daily quest completion payoff (A/B/C layered) | **Resolved 2026-05-13** — A+B+C shipped, in Decided constraints | n/a |
| 15–19 | Notifications (all five) | **Resolved 2026-05-09** | n/a |

No new Open Questions emitted by this audit.

## 4. Memory ledger

| Memory file | Relevance | Honored by |
|---|---|---|
| [feedback_life_clock_lighting_convention.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_life_clock_lighting_convention.md) | Binding constants (opacity 0.22, offset 0.35/0.85, radius 0.55× reference, world-fixed via inverse-rotation). DRY trigger fired by Sprint B1 (third-call-site `cardLighting`); convention unchanged. | **P5** (WrapUp D2 visual verify) explicitly re-checks the lifecycle-pinned shadow on the rotating hand. **P9** (Death Clock reference-match) is required to *match craft, reject framing* — no shadow values will be lifted from the reference. |
| [feedback_life_clock_wake_animation.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_life_clock_wake_animation.md) | Wake on every app open (cold + foreground), 1.0s envelope, reduce-motion-gated. | **P2** (Sprint A4 reduce-motion operator visual verify) preserves the wake gate. No prompt proposes changing the wake cadence. |
| [feedback_life_clock_notifications_constraints.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_life_clock_notifications_constraints.md) | Five rules including wrap-ups pull-not-push. | No prompt in this backlog touches notifications. |
| [feedback_simulator_polish_recon_calibration.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_simulator_polish_recon_calibration.md) | Recon on polish-saturated products skews remedial → use elevation framing. | This skill IS the elevation framing. Today's call-out: the polish-saturation has compounded — premium-feel-audit itself is now close to producing thin output. The cadence override is reflected in the small prompt count + heavy reliance on smoke-test deferrals (which ARE legitimate elevation surface area, not made-up findings). |
| [feedback_xcode_build_loop.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_xcode_build_loop.md) | Headless `xcodebuild` iteration. | Tangential — used by consuming sessions, not this backlog. |
| [feedback_computer_use_default_apps.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_computer_use_default_apps.md) | Batch app permission requests at start. | Tangential — used by consuming sessions. |

No memory entry contradicts any emitted prompt. Vision Decided constraints checked — no proposed move contradicts a constraint.

## 5. Fixture knob catalog

Knobs needed by today's prompts. Same source: [LifeClockLaunchConfiguration.swift](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift). The smoke test surfaced one composition gap (`LIFECLOCK_JUMP_TO=futureFull` doesn't fully populate when chained with `LIFECLOCK_UI_TEST_SCENARIO=onboarded` because snapshot count = 0); **P8** addresses this directly.

| Knob | Values | Used by today's prompts |
|---|---|---|
| `LIFECLOCK_UI_TEST_SCENARIO` | `onboarding` / `onboarded` | P1, P2, P3, P4, P5, P6, P7, P9, P10 |
| `LIFECLOCK_USE_MOCK_HEALTH` | `1` | P1, P2, P3, P4, P5, P6, P9, P10 |
| `LIFECLOCK_HEALTH_AUTH` | `authorized` / `denied` / `notDetermined` | P1, P2 (denied path), P3 |
| `LIFECLOCK_FORCE_COLOR_SCHEME` | `light` / `dark` | **P3** (Sprint D1 dark-mode operator visual verify — primary use) |
| `LIFECLOCK_FORCE_PALETTE` | `default-navy` / `aurora-cool` / `sunset-warm` | **P3** (parity sweep grid) |
| `LIFECLOCK_SEED_TONE` | `gentle` / `coach` / `firm_direct` | P7, P9, P10 |
| `LIFECLOCK_JUMP_TO` | `futureFull` / `futureWarmingUp` / `futureCapReached` etc. | **P4** (Sprint C3 proFooter visual verify); **P8** (fixture composition gap) |
| `LIFECLOCK_SEED_SNAPSHOTS` (gap — see P8) | int (≥14 to reach `full14plus`) | **P4** — only way to fully populate Future tab |
| `LIFECLOCK_SEED_BAD_DAY` | `1` | **P5** (cold-launch WrapUp lighting on negative delta) |
| `LIFECLOCK_INITIAL_TAB` | `today` / `history` / `profile` | P3 |
| `LIFECLOCK_FORCE_PAYWALL` | `1` | P6 |
| `LIFECLOCK_FORCE_SAFETY_NET` | `1` | none today (transition coherence stays on yesterday's P14 — closed) |

## 6. The prompts

Ten prompts. Every prompt uses the binding 9-field template from `skills/canonical/shared/recon-scaffolding.md`. Every prompt cites `premium-bar.md` + a specific category as `Evidence`. Cooling-off rule honored — none of these slugs overlaps a 2026-05-12 prompt slug.

---

### 1. Residual `Text("Loading…")` on Today sparse-state (fix-list)

> **Tier:** loading-bare
>
> **Evidence:** [premium-bar.md § Loading states](premium-bar.md) ("On-brand: loading states use brand-approved indicators … System-default-only = `loading-bare`"); anti-signal: "Copy that says 'loading…' (use a brand verb)." Source-tree grep confirms zero `ProgressView()` literals in `Features/` (Sprint B2 closed), but [TodayView.swift:350](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) still renders `Text("Loading…").foregroundStyle(.secondary)` in the sparse-state headline `else` branch (when no estimate is available). [LifeClockSpinner](../../../products/life-clock-ios/Sources/Shared/LifeClockSpinner.swift) exists and is adopted elsewhere (e.g. [PaywallSheet.swift:180](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift)) — this site was missed.
>
> **Idea:** Replace the bare `Text("Loading…")` with `LifeClockSpinner` in the appropriate size (likely `.regular` to match the surrounding hero scale, or `.compact` if the spinner reads too heavy in a headline slot). Brand-verb copy options, tone-aware via [ToneMode](../../../products/life-clock-ios/Sources/App/ToneMode.swift): gentle `"Reading your day…"`, coach `"Reading your day."`, firmDirect `"Reading."` Note that the surrounding code at [TodayView.swift:219](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) comments "already render 'Loading…' otherwise; no point sweeping to 0" — that comment is a stale artifact of pre-Sprint-B2 thinking and should be updated or removed in the same diff.
>
> **Surfaces:** [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift):350, comment at :219
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_HEALTH_AUTH=notDetermined`, `LIFECLOCK_USE_MOCK_HEALTH=1` (so the sparse-headline branch is reachable while authorization is pending), `LIFECLOCK_SEED_TONE=gentle|coach|firm_direct` to confirm copy.
>
> **Prior context:** Yesterday's [premium-feel-backlog-2026-05-12-standard.md § P2](premium-feel-backlog-2026-05-12-standard.md) — Sprint B2 closed the broad sweep; this single site survived. Smoke-test 2026-05-13 didn't flag because the headline branch wasn't triggered (HK auth state was `authorized`).
>
> **Success criteria:** Zero `Text("Loading…")` literals anywhere in `Features/`. [TodayView.swift:350](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) renders a `LifeClockSpinner` with tone-aware copy. Stale comment at :219 either updated to reflect new behavior or removed. New UITest assertion against `today.headlineSparse.loading` accessibility identifier confirming presence of brand spinner.
>
> **Iteration cap:** 3
>
> **Final computer-use checkpoint:** no — single-site fix; PR-time review sufficient.

---

### 2. Sprint A4 reduce-motion operator visual verify (freeform-polish)

> **Tier:** motion-incoherence (verification)
>
> **Evidence:** [premium-bar.md § Motion](premium-bar.md) ("Reduction respect: every animation respects `UIAccessibility.isReduceMotionEnabled`. Missing reduction paths = `motion-incoherence`"). [smoke-test-2026-05-13.md § Sprint A4](smoke-test-2026-05-13.md): "Verified at build time (xcodebuild succeeded across 10+ Sprint-A-through-D incremental builds with the reduceMotion guards in place). **Visual verification under Reduce Motion not run in this smoke test** — that requires toggling Settings → Accessibility → Reduce Motion which isn't reachable via JUMP_TO. Defer to operator visual check when convenient." Sprint A4 closed yesterday's P10 (reduce-motion fallback table), but the *visual* still has not been operator-eyed under the system-level toggle.
>
> **Idea:** One simulator session driven by the operator (or computer-use with explicit Settings navigation): toggle Settings → Accessibility → Motion → Reduce Motion ON. Then walk every `withAnimation` / `.animation` / `KeyframeAnimator` site Sprint A4 covered: TodayView mascot keyframes ([:474–492](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift)), WrapUpSheet sequencing ([:33–38](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift)), RevealEscalator cycle ([:435](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift)), PaywallSheet `.smooth(.beat)` selection ring ([:61](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift)), chart smooth ([TrajectoryChart.swift:140](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift)), ClockHandView reveal ([:78, :86](../../../products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift)). Capture a one-row table per site: animation present under RM = yes/no (only haptic + state change = correct, full animation = regression). Append findings to [smoke-test-2026-05-13.md](smoke-test-2026-05-13.md) under a new "RM addendum" subsection, or write a focused `polish-2026-05-13-reduce-motion-visual-addendum.md`.
>
> **Surfaces:** Same site list as Sprint A4 closed yesterday's P10. [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift), [WrapUpSheet.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift), [RevealEscalatorScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift), [PaywallSheet.swift](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift), [TrajectoryChart.swift](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift), [ClockHandView.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_USE_MOCK_HEALTH=1`. Reduce Motion toggled via Simulator → Settings → Accessibility → Motion → Reduce Motion. The wake animation (per operator memory `feedback_life_clock_wake_animation.md`) must specifically be verified: with RM ON, the haptic must still fire while the visible scale/opacity transition is suppressed.
>
> **Prior context:** [polish-2026-05-05-today-screen-morning-greeting.md](polish-2026-05-05-today-screen-morning-greeting.md) pinned the wake's reduce-motion gate. Yesterday's P10 covered the fallback table; smoke test ran build-only.
>
> **Success criteria:** Six-site RM-on visual report appended to a polish log. Each site reports: animation suppressed = ✅ / animation still firing = ✗. Any regression triggers an immediate fix-list prompt before Phase D of consumption sequencing. Wake-haptic-without-animation confirmed for cold-launch in particular.
>
> **Iteration cap:** 3
>
> **Final computer-use checkpoint:** yes — RM verification IS the operator visual checkpoint; nothing to defer past PR.

---

### 3. Sprint D1 dark-mode parity operator visual verify (freeform-polish)

> **Tier:** lighting-gap (verification)
>
> **Evidence:** [premium-bar.md § Color and lighting](premium-bar.md) ("Light + dark parity: every surface looks intentional in both modes. Dark-mode afterthought = `lighting-gap`"). [smoke-test-2026-05-13.md § Sprint D1](smoke-test-2026-05-13.md): "Verified on screen indirectly. Dark mode wasn't explicitly toggled… **Dark-mode verification deferred to a focused operator visual check.**" Sprint D1 ratified semantic-token usage and converted `Color.gray.opacity(0.4)` → `Color(.secondarySystemFill)`; the *visual* dark-mode parity across all surfaces was not eyed.
>
> **Idea:** Drive a 5-surface × 2-scheme × 3-palette = 30-cell matrix via `LIFECLOCK_FORCE_COLOR_SCHEME=light|dark` + `LIFECLOCK_FORCE_PALETTE=default-navy|aurora-cool|sunset-warm`. Surfaces: History summary card + foggy-paywall card, Future trajectory chart container, Profile badge grid + Subscription section, QuickLogSheet section headers, WrapUp negative-state. Save screenshots under `docs/products/life-clock/research/dark-parity-2026-05-13/<surface>/<scheme>-<palette>.png` (or use the `polish-*` log convention if the screenshots are inline). Per cell: "intentional" / "afterthought" annotation. If the lighting-opacity question surfaces (rim depth invisible in dark mode), flag it as a memory-amendment vision-question to the operator — do NOT silently change `Lighting`'s constants. Sprint D1 work has been done at the code level (semantic tokens, hairline parity); this prompt VERIFIES it visually.
>
> **Surfaces:** [HistoryView.swift](../../../products/life-clock-ios/Sources/Features/History/HistoryView.swift), [FutureView.swift](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift), [ProfileView.swift](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift), [QuickLogSheet.swift](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift), [WrapUpSheet.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift), [DesignTokens.swift](../../../products/life-clock-ios/Sources/Shared/DesignTokens.swift)
>
> **Fixture knobs:** `LIFECLOCK_FORCE_COLOR_SCHEME=light|dark`, `LIFECLOCK_FORCE_PALETTE=default-navy|aurora-cool|sunset-warm`, `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_SEED_BAD_DAY=1` (for the WrapUp negative dark path), `LIFECLOCK_USE_MOCK_HEALTH=1`.
>
> **Prior context:** Sprint D1 commit `a8c8bcd`. Yesterday's [premium-feel-backlog-2026-05-12-standard.md § P6](premium-feel-backlog-2026-05-12-standard.md) framed this — Sprint D1 closed it at the code level; this prompt closes it at the visual level.
>
> **Success criteria:** 30-cell visual matrix saved under `research/dark-parity-2026-05-13/`. Per-cell annotation. ≤2 "afterthought" cells (and each one has a one-line operator-approved fix path filed as a follow-up). Zero cells flag the lighting-opacity question without an explicit memory-amendment vision-question for the operator.
>
> **Iteration cap:** 4
>
> **Final computer-use checkpoint:** yes — operator reviews the matrix; mode choices are product-grade.

---

### 4. Sprint C3 WhatIfSlider proFooter visual verify on `full14plus` (freeform-polish)

> **Tier:** premium-gap (verification — Perceived depth on a Pro touchpoint, but premium-feel skill walks motion/typography/lighting only; the Pro-value lens lives in the pro-value-audit sibling)
>
> **Evidence:** [premium-bar.md § Surface-level rubric](premium-bar.md) ("Future: motion (the projection animation), typography hierarchy across the trajectory cards, transition to detail screens"). [smoke-test-2026-05-13.md § Sprint C3](smoke-test-2026-05-13.md): "Verified at code level. Visual verification not triggered — the proFooter renders only when the Future tab has enough data to show the slider (`full14plus` state), and `LIFECLOCK_JUMP_TO=futureFull` requires more fixture seed data than this smoke test set up. **Defer visual verification to a polish session with `LIFECLOCK_SEED_SNAPSHOTS=14+` set up.**" The proFooter is the Pro-side preview of the What-If lever; premium-feel-audit walks its motion + typography + lighting (the value-claim half lives in pro-value-audit).
>
> **Idea:** Stand up the `full14plus` Future state via either (a) operator-provided `LIFECLOCK_SEED_SNAPSHOTS=14+` knob (if it exists — verify via `LifeClockLaunchConfiguration.swift`), or (b) a one-line fixture extension to allow direct injection of a populated `snapshots` array on cold-launch (this latter is **P8**'s scope — see sequencing). Capture: proFooter render under default-navy light, default-navy dark, aurora-cool light. Check: (1) motion — does the proFooter animate in coherently with the slider thumb / scrub feel (per yesterday's `polish-2026-05-12-whatif-slider-scrub-feel.md`)? (2) typography — does the footer's pricing/copy use approved roles (Body / Caption / Compact-numeric)? (3) lighting — does the footer card carry `cardLighting`? If any answer is no, file an inline fix into the same polish log.
>
> **Surfaces:** [WhatIfSlider.swift](../../../products/life-clock-ios/Sources/Features/Future/WhatIfSlider.swift), [FutureView.swift](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift), [LifeClockLaunchConfiguration.swift](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift) (fixture extension if needed)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_JUMP_TO=futureFull`, `LIFECLOCK_SEED_SNAPSHOTS=14+` (verify or extend — see P8), `LIFECLOCK_FORCE_COLOR_SCHEME=light|dark`, `LIFECLOCK_FORCE_PALETTE=default-navy|aurora-cool`.
>
> **Prior context:** Sprint C3 commit `81eee24`. [polish-2026-05-12-whatif-slider-scrub-feel.md](polish-2026-05-12-whatif-slider-scrub-feel.md) covered scrub feel without proFooter.
>
> **Success criteria:** ProFooter visually verified across light+dark on at least one palette. The three premium-bar axes (motion / typography / lighting) score `strong` or have an inline fix queued. If `LIFECLOCK_SEED_SNAPSHOTS=14+` doesn't exist, **P8** is queued as a hard dependency before this prompt can run.
>
> **Iteration cap:** 4
>
> **Final computer-use checkpoint:** yes — Pro-touchpoint surface visual; operator-eye on premium-feel craft is required.

---

### 5. Sprint D2 WrapUp clock-face full-lighting visual verify (freeform-polish)

> **Tier:** lighting-gap (verification)
>
> **Evidence:** [premium-bar.md § Color and lighting + § Surface-level rubric](premium-bar.md) ("WrapUp: motion (sequenced reveal), haptics on each reveal beat, microcopy tone, lighting on the clock face"); [feedback_life_clock_lighting_convention.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_life_clock_lighting_convention.md). [smoke-test-2026-05-13.md § Sprint D2](smoke-test-2026-05-13.md): "Verified at code level. WrapUp doesn't trigger in this smoke test (requires cold-launch conditions). The `lightingDepth(referenceSize: 6)` modifier on the static `Circle().stroke(...)` is present in `ClockHandView.swift`; **behavior unchanged from build verification.**" The WrapUp ceremony moment is the single most premium-leverage surface in the app per yesterday's [premium-feel-backlog-2026-05-12-standard.md § P7](premium-feel-backlog-2026-05-12-standard.md) — and its full lighting has now been wired but never seen.
>
> **Idea:** Stand up the cold-launch WrapUp present-condition via the `WrapUpCoordinator` path: seed `LIFECLOCK_SEED_STREAK=7` + `LIFECLOCK_SEED_DAYS_SINCE_INSTALL=8` + `LIFECLOCK_SEED_BASELINE_ADJUSTMENT=0` per [polish-2026-05-06-wrapup-sequencing-foreground-cycles.md](polish-2026-05-06-wrapup-sequencing-foreground-cycles.md) (Monday-return weekly). Capture WrapUp clock-face render against the app icon side-by-side (the icon is the canonical lighting reference per the operator memory). The rotating hand should carry `lightingRotatedDepth(referenceSize:angle:)` and the face should carry `lightingDepth(referenceSize: 6)`. Verify: (a) the world-fixed light source reads as upper-left (matching icon), (b) rim depth visible in both schemes, (c) when the hand rotates during the sequenced reveal, the shadow stays world-fixed (does not rotate with the hand — inverse-rotation math working). If the reference-side-by-side shows the icon-and-clock as the same artifact, Sprint D2 is closed visually. Negative-delta path (`LIFECLOCK_SEED_BAD_DAY=1`) also captured.
>
> **Surfaces:** [ClockHandView.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift), [WrapUpSheet.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift), [WrapUpCoordinator.swift](../../../products/life-clock-ios/Sources/Engines/WrapUpCoordinator.swift), reference at `products/life-clock-ios/Assets.xcassets/AppIcon.appiconset/`
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_SEED_STREAK=7`, `LIFECLOCK_SEED_DAYS_SINCE_INSTALL=8`, `LIFECLOCK_SEED_BASELINE_ADJUSTMENT=0`, `LIFECLOCK_USE_MOCK_HEALTH=1`, `LIFECLOCK_FORCE_COLOR_SCHEME=light|dark`, plus `LIFECLOCK_SEED_BAD_DAY=1` second run.
>
> **Prior context:** Sprint D2 commit `a8c8bcd`. Yesterday's [premium-feel-backlog-2026-05-12-standard.md § P7](premium-feel-backlog-2026-05-12-standard.md) framed this — Sprint D2 wired the lighting; this prompt verifies it visually against the icon.
>
> **Success criteria:** WrapUp clock-face render side-by-side with app icon, both schemes captured. Operator confirms in the polish log that "the three feel like one product." No deviation from the lighting constants — if a value seems to need adjusting, that's a memory-amendment vision-question routed to the operator.
>
> **Iteration cap:** 4
>
> **Final computer-use checkpoint:** yes — reference-match against the icon is operator-only.

---

### 6. Sprint D3 PaywallPrimaryView visual verify via onboarding walkthrough (freeform-polish)

> **Tier:** microcopy-flab (verification)
>
> **Evidence:** [premium-bar.md § Microcopy](premium-bar.md). [smoke-test-2026-05-13.md § Sprint D3](smoke-test-2026-05-13.md): "Verified at code level. Sprint D3 changed `PaywallPrimaryView`'s body from 'Pro keeps your full history, weekly drivers, and every wrap-up.' → 'Pro adds full daily history, weekly drivers, and the richer wrap-up.' `PaywallPrimaryView` only renders during onboarding's terminal paywall screen — not reachable from `onboarded` JUMP_TO state. **Defer visual verification to an onboarding walkthrough.**" The onboarding terminal paywall is the first paywall the user ever sees; getting the copy right at that moment is high-leverage. Closing this prompt requires a full onboarding walkthrough.
>
> **Idea:** Drive `LIFECLOCK_UI_TEST_SCENARIO=onboarding` (fresh-install path), walk through the onboarding screens to the terminal paywall, capture the `PaywallPrimaryView` render. Verify: (a) the body copy is the new "Pro adds full daily history, weekly drivers, and the richer wrap-up." string (no stale "every wrap-up" residual — a value-claim issue audited yesterday and addressed in Sprint D3); (b) the `≈ $X.XX / mo equivalent` annual-savings caption from [PaywallPrimaryView.swift:210–216](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift) renders with the post-Sprint-A1 dollar values; (c) the headline ("Earn time with better habits." per Decided constraint 2026-05-11) is preserved. Also check transition coherence into and out of the terminal paywall — does it match the rest of the onboarding rhythm, or does it feel discontinuous?
>
> **Surfaces:** [PaywallPrimaryView.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift), [LeadInScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift), [RevealEscalatorScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarding` (fresh-install path is required — `onboarded` skips the terminal paywall), `LIFECLOCK_USE_MOCK_HEALTH=1`, `LIFECLOCK_HEALTH_AUTH=authorized`. Optional: run the PSS + UCLA threshold path that triggers the softer reveal (per Decided constraint 2026-05-12) to verify the paywall arrives coherently from either reveal register.
>
> **Prior context:** Sprint D3 commit `a8c8bcd`. Yesterday's [pro-value-backlog-2026-05-12-standard.md § P7](pro-value-backlog-2026-05-12-standard.md) caught the copy mismatch; Sprint D3 fixed it — visual unseen.
>
> **Success criteria:** PaywallPrimaryView rendered visual matches the new copy exactly. Annual `≈ $X.XX / mo equivalent` line renders with $4.17. Transition into/out of the paywall reads continuous with the rest of onboarding. If the softer-reveal path's transition into the paywall feels register-mismatched (dramatic reveal → standard paywall), file a Stretch-tier follow-up.
>
> **Iteration cap:** 4
>
> **Final computer-use checkpoint:** yes — first-paywall visual is high-leverage; operator-eye required.

---

### 7. Death Clock: The Life Lab reference-match for premium reveal craft (reference-match)

> **Tier:** motion-incoherence (elevation via reference)
>
> **Evidence:** [premium-bar.md § Motion + § Surface-level rubric](premium-bar.md) — Today motion + Future projection animation + WrapUp sequenced reveal are the three ceremonial moments in the app. [vision.md § References](vision.md) (Decided constraint 2026-05-13): "Premium-feel reference app: Death Clock: The Life Lab. Source: operator decision 2026-05-13, documented in [reference-apps.md](reference-apps.md). Used as the craft benchmark for reference-match audit prompts targeting motion, transitions, reveal animations, and number-animation patterns. *Match the craft, reject the framing* — Life Clock's vision Decided constraints (trajectory-not-prophecy, no AI concierge, no bloodwork, no mortality-heavy lexicon) supersede any reference pattern." Yesterday's audit could not author this prompt because the reference wasn't anchored yet.
>
> **Idea:** Two-iteration reference-match. Iteration 1: capture Death Clock's reveal sequence (App Store preview video + installed-app recording if the operator can permit) and Life Clock's three ceremonial moments — onboarding RevealEscalator, Today first-wake, Future projection reveal — side-by-side. Score on: (a) number-animation craft (how does Death Clock animate the headline number? does Life Clock match?), (b) reveal pacing (Death Clock's beat structure vs Life Clock's `Motion.Duration.{instant,beat,breath}` tiers from Sprint A — do the ceremonial moments earn their durations?), (c) transition feel between major moments. Iteration 2: pick 1–3 specific craft moves to import — **without** importing Death Clock's mortality framing, mortality lexicon, or any "prophecy" framing (rejected by vision Decided 2026-05-04 "trajectory, not prophecy"). Examples of importable craft: number-counter animation timing, reveal-stagger curves, the way an exact-date display lands. Examples of explicitly NOT importable: any "you will die on YYYY-MM-DD" framing, any countdown-to-death visual, any bloodwork/medical-claim UI. Output is a `polish-2026-05-13-death-clock-reference-match.md` log with the side-by-side + 1–3 concrete ratchet recommendations + an explicit "what we are NOT importing" list to keep the operator's brake on framing.
>
> **Surfaces:** [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift), [LifeClockMascotView.swift](../../../products/life-clock-ios/Sources/Shared/LifeClockMascotView.swift), [EngineRevealPresenter.swift](../../../products/life-clock-ios/Sources/Shared/EngineRevealPresenter.swift), [TrajectoryChart.swift](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift), [RevealEscalatorScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift), reference recordings under `docs/products/life-clock/research/death-clock-2026-05-13/`
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarding` (for the full RevealEscalator pass), `LIFECLOCK_UI_TEST_SCENARIO=onboarded` (for the Today first-wake + Future projection), `LIFECLOCK_SEED_BASELINE_ADJUSTMENT=2.5` + `LIFECLOCK_JUMP_TO=futureFull` (for Future projection coherence — co-dependent on P4's fixture composition).
>
> **Prior context:** Reference anchor landed 2026-05-13 in commit `b65099a`. [reference-apps.md](reference-apps.md) is the binding doc. No prior reference-match session.
>
> **Success criteria:** A `polish-2026-05-13-death-clock-reference-match.md` log contains: the side-by-side captures (both apps, both products' three ceremonial moments), a 3-dimension scoring matrix, 1–3 ratchet recommendations, and an explicit "what we are NOT importing" list naming framing/lexicon/prophecy patterns we are rejecting. No source change in this prompt — recommendations feed forward into focused fix-list prompts in a subsequent session. Vision Decided constraints 2026-05-04 ("trajectory, not prophecy") and 2026-05-13 (reference reject-list) explicitly cited in the log.
>
> **Iteration cap:** 5
>
> **Final computer-use checkpoint:** yes — reference-match against a real app is the whole point.

---

### 8. Fixture composition gap: `LIFECLOCK_JUMP_TO=futureFull` + `onboarded` doesn't populate (fix-list)

> **Tier:** premium-gap (infrastructure — but premium audits depend on it)
>
> **Evidence:** [smoke-test-2026-05-13.md § Things noticed in passing](smoke-test-2026-05-13.md): "`LIFECLOCK_JUMP_TO=futureFull` doesn't fully populate when seeded onto `LIFECLOCK_UI_TEST_SCENARIO=onboarded` — the Future tab still renders the day0 state because the underlying snapshot count is 0. To exercise the `full14plus` Future state, would need `LIFECLOCK_SEED_SNAPSHOTS` or equivalent. **Fixture composition gap — file as a polish item if it bites future audits.**" The gap bites today: **P4** (Sprint C3 visual verify) and **P7** (Death Clock reference-match on Future projection) both depend on a populated Future tab. Without a fix this prompt blocks both.
>
> **Idea:** Inspect [LifeClockLaunchConfiguration.swift](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift) and the `JumpToTarget` enum — either (a) `LIFECLOCK_SEED_SNAPSHOTS` exists but is undocumented, or (b) it doesn't and needs adding. If (b): add a `LIFECLOCK_SEED_SNAPSHOTS` knob accepting an int (number of synthetic snapshots to backfill into the in-memory store before first render), with realistic baseline drift so the chart isn't a flat line. Document the knob in `LifeClockLaunchConfiguration.swift`'s knob list comment AND in `docs/products/life-clock/CLAUDE_HANDOFF.md` (the developer-facing knob reference). Audit `JumpToTarget`'s assumptions: which targets *implicitly require* a populated snapshot store? `futureFull`, `futureWarmingUp`, `futureCapReached`, `futureFloorReached`. If they don't auto-seed, document that too. This unblocks the operator's audit cadence going forward — any future Future-tab visual verification can now compose cleanly.
>
> **Surfaces:** [LifeClockLaunchConfiguration.swift](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift), [LifeClockStore.swift](../../../products/life-clock-ios/Sources/App/LifeClockStore.swift) (snapshot-seeding path), [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md) (knob reference)
>
> **Fixture knobs:** N/A — this prompt IS the fixture-knob work.
>
> **Prior context:** Smoke test noted but did not file. No prior polish session covered fixture knob hygiene.
>
> **Success criteria:** `LIFECLOCK_SEED_SNAPSHOTS=<int>` either documented as existing and working, or added. Smoke-test recipe re-run: `LIFECLOCK_UI_TEST_SCENARIO=onboarded` + `LIFECLOCK_JUMP_TO=futureFull` + `LIFECLOCK_SEED_SNAPSHOTS=21` lands on the Future tab with a populated 21-day chart and the WhatIfSlider rendering its `full14plus` state. Knob list comment in `LifeClockLaunchConfiguration.swift` updated. Acceptance verified by **P4**.
>
> **Iteration cap:** 4
>
> **Final computer-use checkpoint:** no — fixture-knob work is mechanical; PR-time review sufficient.

---

### 9. SupportMomentCard lighting reference-coverage check (fix-list)

> **Tier:** lighting-gap
>
> **Evidence:** [premium-bar.md § Color and lighting](premium-bar.md). Yesterday's [premium-feel-backlog-2026-05-12-standard.md § P5](premium-feel-backlog-2026-05-12-standard.md) listed [SupportMomentCard.swift](../../../products/life-clock-ios/Sources/Shared/SupportMomentCard.swift) as a target for lighting-extension; [smoke-test-2026-05-13.md § Sprint B1](smoke-test-2026-05-13.md) verified 6 Today cards (clockCard, mascotHero, driversCard, questsCard, quickLogCard, headline) and paywall product rows carry `cardLighting()`, but did not explicitly list SupportMomentCard. The card appears on Today after a quest completion (Decided constraint 2026-05-13 — A+B+C payoff shipped) and is one of the most emotionally-loaded surfaces in the daily loop.
>
> **Idea:** Open `SupportMomentCard.swift`, grep for `cardLighting` / `lightingDepth` modifier application. If present: visually verify in light + dark scheme that the depth reads on-brand. If absent: apply `.cardLighting()` (the convention extension landed in Sprint B1) using the card's height as the reference size. Same rule: respect the lighting convention's constants (operator memory). If the card is composed inside another surface that already applies the modifier, document the omission with a one-line comment ("parent surface carries the shadow").
>
> **Surfaces:** [SupportMomentCard.swift](../../../products/life-clock-ios/Sources/Shared/SupportMomentCard.swift), [SupportMomentPresenter.swift](../../../products/life-clock-ios/Sources/Shared/SupportMomentPresenter.swift), [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) (presentation site for the post-quest-completion card)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_USE_MOCK_HEALTH=1`, drive a quest completion via the test scaffold (`testTouchpoint*` UITest pattern) to make the card present.
>
> **Prior context:** Yesterday's P5 + Sprint B1. The Sprint B1 6-card list did not explicitly cover SupportMomentCard.
>
> **Success criteria:** SupportMomentCard either carries the lighting modifier directly or has a documented justification for why a parent surface owns the shadow. Light + dark scheme visual confirms the card reads as elevated in both modes. No deviation from the lighting convention's constants.
>
> **Iteration cap:** 3
>
> **Final computer-use checkpoint:** no — single-component check; PR-time review sufficient.

---

### 10. Tone-mode picker label + DayDetailView heading microcopy alignment (freeform-polish)

> **Tier:** microcopy-flab
>
> **Evidence:** [premium-bar.md § Microcopy](premium-bar.md) ("Tone coherence: copy matches the active tone mode … Voice: copy reads like the canonical voice"). [smoke-test-2026-05-13.md § Things noticed in passing](smoke-test-2026-05-13.md): "Tone mode picker label reads 'Default / Average' rather than 'Coach' in the picker chip. The underlying enum is `coach` (default) per ToneMode.swift. The label is a deliberate UX choice — neither a bug nor a microcopy violation. **Worth noting in case a future polish session wants the surfaced label to match the enum name.**" Plus [vision.md Open Q13](vision.md): "DayDetailView / ReflectionCard heading divergence. `ReflectionCard` on Today uses `tone.reflectionHeading` (three variants); the Reflection section in `DayDetailView` uses a hardcoded `'Reflection'`. Trivial to align — file as Polish-tier in the next pass, no vision question." Both are Polish-tier microcopy alignment that yesterday's P12 (terse-sweep) explicitly excluded from scope — bringing them in as a focused alignment prompt today.
>
> **Idea:** Two changes in one focused session. (1) **Tone picker label** — decide between (a) keep "Default / Average" because it reads as a difficulty-tuning chip rather than a personality-tuning chip and that's the right UX framing (no change); (b) align label to the canonical enum name "Coach" so the picker chip matches the rest of the app's vocabulary (visible change). Surface the choice as an in-session decision; do not silently change. (2) **DayDetailView Reflection heading** — replace the hardcoded `Text("Reflection")` with `tone.reflectionHeading` so the heading respects active tone mode (per `ReflectionCard`'s pattern). Trivial diff; no operator decision required (Open Q13 explicitly authorizes this as Polish-tier).
>
> **Surfaces:** [ProfileView.swift](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift) (tone picker section), [ToneMode.swift](../../../products/life-clock-ios/Sources/App/ToneMode.swift) (label source), [DayDetailView.swift](../../../products/life-clock-ios/Sources/Features/History/DayDetailView.swift) (Reflection heading), [ReflectionCard.swift](../../../products/life-clock-ios/Sources/Features/Today/ReflectionCard.swift) or wherever `tone.reflectionHeading` is defined
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_SEED_TONE=gentle|coach|firm_direct` to verify the heading varies across modes.
>
> **Prior context:** Yesterday's P12 (microcopy density terse-sweep) explicitly held both back. [polish-2026-05-09-profile-section-sweep.md](polish-2026-05-09-profile-section-sweep.md) reorganized Profile but did not touch the tone-picker label.
>
> **Success criteria:** (1) Tone-picker label decision logged in the session log with rationale (either "keep Default/Average; the chip is difficulty-coded UX, not personality-coded" or "align to Coach"). (2) `DayDetailView`'s Reflection heading uses `tone.reflectionHeading`. Three-tone screenshot grid confirms variation. Open Q13 closed in the same diff.
>
> **Iteration cap:** 3
>
> **Final computer-use checkpoint:** no — small copy changes; PR-time review sufficient.

---

## 7. Variety check

Declared distribution across modes and tiers:

| Mode | Count | Floor (standard) | Met? | Prompts |
|---|---|---|---|---|
| `fix-list` | 3 | ≥2 | ✓ | P1, P8, P9 |
| `freeform-polish` | 6 | ≥3 | ✓ | P2, P3, P4, P5, P6, P10 |
| `reference-match` | 1 | ≥2 | **⚠️ short by one** | P7 |
| `vision-driven` | 0 | ≥1 | **⚠️ short by one** | none |
| **Total** | **10** | min 10 / max 40 | ✓ count | — |

**Variety-mandate exception logged** (per `shared/recon-scaffolding.md` § "Variety mandate" rule 2). The operator authorized this same-week re-run (24h after the prior standard audit) with cooling-off applied at the slug level. The 2026-05-12 audit consumed the available `reference-match` surface area (Streaks/Strava/Centr paywall, app-icon, premium graphing reference) and the available `vision-driven` surface area (Q14 — now Decided 2026-05-13). The remaining `reference-match` move (Death Clock — P7) and zero remaining `vision-driven` moves are genuinely all the audit found. **No new Vision Open Questions surfaced today**, so emitting a `vision-driven` prompt would be inventing one for variety theater. The operator's call: accept the floor slip or extend depth. Recommended: accept; come back in 2 weeks at the natural cadence for a full-floor audit.

| Tier | Count |
|---|---|
| `loading-bare` | 1 (P1) |
| `motion-incoherence` (verification + elevation) | 2 (P2, P7) |
| `lighting-gap` (verification + extension) | 3 (P3, P5, P9) |
| `premium-gap` | 2 (P4 verification, P8 infrastructure) |
| `microcopy-flab` (verification + alignment) | 2 (P6, P10) |

No `submission-blocker`-tier prompts. Yesterday's audit found none; today's audit finds none — touch-targets and a11y-contrast remain clean per `polish-2026-05-12-trajectory-chart-a11y-colorblind-xxl.md` and the smoke-test verification of Sprint A3 typography roles.

## 8. Recommended sequencing

**Phase A — unblockers** (must run first to unblock other prompts):

1. **P8** (fixture composition gap) — unblocks **P4** (Sprint C3 proFooter visual) and the Future-projection slice of **P7** (Death Clock reference). Without P8 those visual verifications cannot land cleanly.

**Phase B — smoke-test deferral close-outs** (run after A in parallel where independent):

2. **P2** (Sprint A4 reduce-motion visual verify) — independent.
3. **P3** (Sprint D1 dark-mode parity visual verify) — independent.
4. **P5** (Sprint D2 WrapUp clock-face lighting verify) — independent.
5. **P6** (Sprint D3 PaywallPrimaryView onboarding verify) — independent.
6. **P4** (Sprint C3 WhatIfSlider proFooter verify) — depends on P8.

**Phase C — residuals + alignment** (quick wins):

7. **P1** (TodayView.swift:350 `Text("Loading…")` residual) — independent fix-list.
8. **P9** (SupportMomentCard lighting check) — independent fix-list.
9. **P10** (tone-picker + DayDetailView heading alignment) — independent freeform.

**Phase D — high-craft reference** (run last):

10. **P7** (Death Clock reference-match) — depends on P8 + benefits from the smoke-test deferrals closing out so the operator has a clean visual baseline for the comparison.

If you only run three this month: **P1, P5, P7** — close the one remaining residual, verify the most ceremonial moment visually, and ratchet the now-anchored premium reference.

## 9. Readiness flag

**Premium-readiness: yellow** (with green-pending — see below).

Strict-mode green requires:

- [ ] Every `premium-bar.md` category has a polish session log covering it in the last 30 days — **yes** (the seven product specs + Sprints A–D + the smoke test land coverage on every category).
- [ ] Zero unresolved `motion-incoherence` prompts — **partial** (P2 is verification; P7 is elevation; neither is regression).
- [ ] Zero unresolved `typography-drift` prompts — **yes** (typography-spec.md ratified the four numeric-display exception tiers; smoke test confirmed zero drift).
- [ ] Zero unresolved `lighting-gap` prompts — **partial** (P3, P5, P9 are verifications; P5 is the highest-leverage premium moment in the app).
- [ ] Every Decided constraint in `vision.md` has a polish log demonstrating premium-bar compliance — **yes** (Decided 2026-05-12 reveal escalator, Decided 2026-05-13 quest-completion payoff, etc.).
- [ ] Lifecycle-pinned lighting convention applied on every rotating/dial surface — **build-verified for WrapUp clock-face (Sprint D2); visual verification deferred to P5**.

Why not green today: **five smoke-test deferrals (P2, P3, P4, P5, P6) are visual verifications, not new findings**. Each one represents work that has landed at the code level and is awaiting a single operator-eye pass. Until they close, premium-readiness is honestly yellow.

Why not red: zero `submission-blocker`. Zero unaddressed-for-30-days `lighting-gap` / `typography-drift`. Zero motion sites lacking a reduce-motion code path (Sprint A4 closed). The TodayView `Text("Loading…")` residual (P1) is a tiny single-site survival, not a categorical regression.

**The three prompts that would flip yellow → green:**

1. **P5** (Sprint D2 WrapUp clock-face lighting verify) — the most ceremonial premium surface; the visual verification IS the green flag for the rubric's most-visible category.
2. **P3** (Sprint D1 dark-mode parity visual verify) — closes the categorical "light + dark parity" requirement at the visual level.
3. **P2** (Sprint A4 reduce-motion visual verify) — closes Motion category's reduction-respect rubric at the visual level for the wake animation in particular.

After those three land — likely within one focused operator session — re-running this audit should report **green**.

---

> **Cross-cutting elevation themes (one paragraph for the operator):** This week's work moved Life Clock from "individually polished surfaces" to a "system-grounded product." The foundation artifacts (Motion, Lighting extension, LifeClockSpinner, EmptyStateView, DesignTokens) and the seven product specs (motion / lighting / typography / paywall / microcopy / accessibility / reveal-escalator / etc.) now make every future surface inherit the bar by default — a future polish session adding a new card or sheet will pick up `cardLighting`, `Motion.Duration.beat`, `LifeClockSpinner`, and EmptyStateView shape automatically rather than reinventing. The remaining premium-feel work is overwhelmingly **visual verification** of code-level wiring (P2, P3, P4, P5, P6) plus one tiny residual (P1) plus the one genuinely-net-new reference-match against the now-anchored Death Clock premium benchmark (P7). The audit cadence honest call-out: yesterday's standard audit was a full-spread elevation discovery; today's is a close-out + verification cycle. A natural next full standard audit lands in 2 weeks (2026-05-27) when the system has had time to be lived in and either reveal coherence wins or surface drift the bar will catch.
