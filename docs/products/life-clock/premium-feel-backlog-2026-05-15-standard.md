# Life Clock — Premium-Feel Backlog (2026-05-15, standard depth)

> **Skill:** `premium-feel-audit` (canonical: `skills/canonical/premium-feel-audit/skill.md`)
> **Inputs:** `product_id=life-clock`, `baseline=origin/main` (HEAD `ec1361e` — `origin/main` does not resolve in this worktree; HEAD is the current main tip), `depth=standard`, `focus=none`, `minimum_prompts=10`
> **Observer:** [`premium-bar.md`](premium-bar.md) + supplementary [`motion-spec.md`](motion-spec.md), [`typography-spec.md`](typography-spec.md), [`haptics-spec.md`](haptics-spec.md)
> **Author:** Claude (Opus 4.7 1M), single read-only pass — every finding re-verified against current source, not against prior-backlog claims
> **Consumed by:** `simulator-driven-polish` — each prompt is copy-pasteable into a fresh session

> **⚠️ Cooling-off note (binding).** Prior premium-feel backlogs exist at [2026-05-12](premium-feel-backlog-2026-05-12-standard.md) and [2026-05-13](premium-feel-backlog-2026-05-13-standard.md); pro-value backlogs at [2026-05-12](pro-value-backlog-2026-05-12-standard.md) and [2026-05-13](pro-value-backlog-2026-05-13-standard.md); ~40 `polish-2026-05-*.md` logs. All within 14 days of 2026-05-15. The 14-day cross-skill rule was enforced **at the source level** — every prior "resolved/closed" claim was re-checked against current code before deciding whether a slug was genuinely closed or still open. Result: the 5/13 backlog leaned heavily on five "smoke-test-deferred visual verifications" (its P2–P6) and a Death-Clock reference-match (P7). Verification of current source shows the **code-level** work is real (loading sweep closed, Lighting/Spinner/EmptyState/Motion artifacts shipped), but several premium-bar categories are **not** closed in code: motion-spec's own migration table is only ~40% applied, and a post-5/14 surface rewrite (SupportMoment → toast) introduced a net-new off-convention shadow. This backlog re-emits only where the gap is verifiably live in source, plus the two explicitly-deferred carry-forwards (Death Clock visual capture; reduce-motion / dark-mode operator visual passes that no log has yet executed).

---

## 1. State summary

Audited HEAD `ec1361e` ("fix(life-clock): onboarding polish + enforce exact 3-item today plan"), the current main tip. Since the 5/13 audit baseline the operator landed onboarding polish, the mascot clock-hand cross-width gradient (`a7d0fac`), and dropped the projected-healthspan card from Today (`e443b56`) — the last directly invalidates 5/13's Death-Clock ratchet #2 ("trajectory-peek ticking on Today"), since the projected-healthspan card it targeted no longer exists on Today. **Clean:** loading states are genuinely premium — zero `Text("Loading…")` / `ProgressView()` literals survive in `Features/`, `LifeClockSpinner` is adopted across six surfaces (5/13 P1 verifiably closed). Haptics policy (`LifeClockHaptics`) and the lighting convention enum are centralized. **Risky:** `motion-spec.md`'s own binding migration table (10 sites → named `Motion.Duration`/`Motion.Curve`) is only partially applied — four files adopted `Motion.Duration` and exactly one site uses `Motion.Curve`; the reveal escalator, trajectory chart, two onboarding reveal screens, the dial, and the lead-in still carry ad-hoc `0.35` / `0.18` / `0.32` / literal `.snappy` durations, and `0.32` isn't even on a defined tier. That is a live `motion-incoherence` gap and a premium-readiness green-blocker. The 5/14 SupportMoment→toast rewrite introduced `SupportMomentToast.swift:63` raw `.shadow(.black.opacity(0.18), radius: 12, y: 6)` — off the world-fixed lighting convention and not `lightingDepth`/`cardLighting`; the 5/14 log itself flagged brand-surface integration as deferred. The three numeric-display sites (`TodayView.swift:289`, `WrapUpSheet.swift:67`, `OverrideSheet.swift:26`) map to `typography-spec.md`'s role families by *value* but use raw `.font(.system(size:))` literals with no named `DesignTokens.Typography` token (DesignTokens has no Typography section) and no documented AccessibilityXXXL clamp — spec-aligned by role, not by hygiene. `OverrideSheet.swift:76` still builds `"No data for this day yet."` as an error string (rubric anti-signal). **Premium-readiness: yellow.** It is honestly *not* green (live motion-incoherence + a net-new lighting-gap), and not red (no submission-blocker; loading category fully premium; nothing categorical unaddressed >30 days).

## 2. Coverage matrix

One row per surface in `premium-bar.md` § "Surface-level rubric." `s/p/w/a` = strong / partial / weak / absent. Scores reflect re-verified current source at `ec1361e`, not prior-backlog claims.

| Surface | Last polish session | Motion | Haptics | Typography | Transitions | Empty states | Loading states | Color and lighting | Microcopy | Open Qs touching | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Today | 2026-05-14 (support-moment-toast-overlay); 2026-05-12 (today-free-vs-pro-and-a11y) | partial (TodayView keyframes 0.40/0.22/0.30 still literal vs Motion tiers) | strong | partial (line 289 raw `.system(size:44)`, role-aligned but un-tokenized) | partial | partial | strong (LifeClockSpinner adopted) | partial (SupportMomentToast:63 raw shadow off-convention) | strong | #1–4 (outside premium-bar) | premium-gap (motion-incoherence + lighting-gap on the new toast) |
| History | 2026-05-14 (history-perf-confidence-swipe-nav); 2026-05-11 (history-day1-empty-state-tones) | partial (HistoryView:241 `easeOut(0.2)` off-tier) | partial | partial | partial | partial (OverrideSheet:76 `"No data…"` error string) | strong | strong | strong | none | premium-gap (empty-state-flat + motion off-tier) |
| Future | 2026-05-13 (smoke-test day0); 2026-05-12 (whatif-slider-scrub-feel) | partial (TrajectoryChart:140 `0.18` literal — should be `Motion.Duration.instant`) | strong | strong | partial | partial | strong | strong (cardLighting on WhatIfSlider + chart) | strong | none | premium-gap (motion-incoherence — un-migrated literal) |
| WrapUp | 2026-05-13 (smoke-test code-level); 2026-05-06 (wrapup-sequencing) | strong (ClockHandView/WrapUpSheet migrated to Motion.Duration) | strong | partial (WrapUpSheet:67 raw `.system(size:44)`, role-aligned, un-tokenized) | partial | n/a | n/a | strong (Sprint D2 lighting, build-verified; visual verify never executed by any log) | strong | none | premium-aligned (lighting visual verify still owed) |
| Quest detail / QuickLog | 2026-05-11 (quicklog-drift-and-q11-narration); 2026-05-09 (quest-completion-payoff) | strong | strong | partial | partial | partial | strong | strong | strong | #11 (Open Stretch) | premium-aligned |
| Profile | 2026-05-09 (profile-section-sweep) | partial | strong | strong | partial | partial | strong (LifeClockSpinner adopted) | strong | strong | none | premium-aligned |
| Paywall (motion / typography / haptics only — value-claim is pro-value-audit) | 2026-05-13 (macrofactor-reference-match); 2026-05-12 (Sprint C2) | strong (`Motion.Duration` on selection ring) | strong | strong | strong | n/a | strong (LifeClockSpinner) | strong | strong | #12 (Open Stretch) | premium-aligned |
| Onboarding (visual coherence only — funnel is recon) | 2026-05-13 (death-clock-reference-match); 2026-05-12 (vision-q9-reveal-escalator-tone-mocks) | partial (RevealEscalator:449 `0.35`; HealthspanReveal:86 + WhatWeDontDo:47/61 `0.32` off-tier; EngineRevealAndDial:95 + LeadIn:337 literal `.snappy`) | partial | partial (onboarding numeric per spec exception) | partial (reveal→paywall is a hard NavigationStack push — Death-Clock ratchet #1 unscoped) | n/a | partial | strong | strong (Decided 2026-05-11/05-12) | #9, #10 (resolved) | premium-gap (motion-incoherence — heaviest un-migrated cluster) |

No empty cells. Every surface carries at least one verdict diagnosis.

## 3. Open Questions ledger

| # | Title | Status | Targeted by this backlog |
|---|---|---|---|
| 1 | Negative-feedback intensity | Open (pools softened 5/7 + 5/10) | none — outside premium-bar |
| 2 | Hide the clock? | Open, strategic | none — feature scope |
| 3 | Minimum daily manual log | Open | none — feature scope |
| 4 | Uncertainty without weakness | Open | none — feature scope |
| 5 | Pro daily-loop differentiation | Open | not this skill (pro-value-audit) |
| 6 | First-paywall placement | Open | not this skill (pro-value-audit) |
| 7 | Streak treatment | **Resolved 2026-05-06** | n/a |
| 8 | Tone-mode discoverability | Open | none |
| 9 | Reveal-escalator tone-awareness | **Resolved 2026-05-12** | n/a |
| 10 | Onboarding lead-in copy register | **Resolved 2026-05-11** | n/a |
| 11 | QuickLogSheet narration | Open (Stretch, needs operator-yes) | none — explicit anti-pattern hold carried since 5/12 P12 |
| 12 | Paywall headline tone | Open (Stretch + marketing review) | none — value-claim is pro-value-audit territory |
| 13 | DayDetailView heading divergence | Open (Polish) | none — 5/13 P10 already scoped it; not re-emitted (cooling-off) |
| 14 | Daily quest completion payoff | **Resolved 2026-05-13** | n/a |
| 15–19 | Notifications (all five) | **Resolved 2026-05-09** | n/a |

No new Open Questions surfaced by this audit. **P10** below is a `vision-driven` prompt that proposes the operator add a new `premium-bar.md` category (Cross-screen reveal continuity) rather than inventing one — it does not append to vision Open Questions (recon-family skills must not).

## 4. Memory ledger

Every operator-memory entry consulted. Hard-refusal check performed: no emitted prompt contradicts any entry.

| Memory file | Relevance | Honored by |
|---|---|---|
| [feedback_life_clock_lighting_convention.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_life_clock_lighting_convention.md) | Binding constants: opacity 0.22, offset 0.35/0.85, radius 0.55× reference, world-fixed via inverse-rotation. | **P1** (SupportMomentToast off-convention shadow) requires migration TO `lightingDepth`/`cardLighting` — it does not invent new shadow values; the fix is to adopt the pinned convention, not deviate from it. **P5** (WrapUp lighting visual verify) re-checks the world-fixed shadow on the rotating hand against these exact constants. |
| [feedback_life_clock_wake_animation.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_life_clock_wake_animation.md) | Wake plays on EVERY app open (cold + foreground); 1.0s envelope; reduce-motion-gated; no per-day gating. | **P3** (Motion.Duration migration sweep) explicitly excludes the 1.0s wake envelope and the >0.8s narrative beats from retiering (motion-spec itself classes these as narrative literals). **P6** (reduce-motion visual verify) preserves the wake gate; no prompt proposes changing wake cadence or reintroducing per-day gating. |
| [feedback_life_clock_notifications_constraints.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_life_clock_notifications_constraints.md) | One notification class; evening; 8…22 clamp; wrap-ups pull-not-push; lock-screen copy follows in-app tone. | No prompt in this backlog touches notifications. |
| [feedback_simulator_polish_recon_calibration.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_simulator_polish_recon_calibration.md) | Recon on polish-saturated products skews remedial → use elevation framing; never pad to floor; surface saturation honestly. | This skill IS the elevation framing. The variety floor is honestly short by one `reference-match` (Death Clock + MacroFactor both consumed 5/13 — see § 7); rather than pad with a manufactured reference, the slip is logged. Calibration honored: this backlog is small and honest, not padded. |
| [feedback_observable_environment_sheets.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_observable_environment_sheets.md) | Re-inject `.environment(observable)` at every sheet/cover/popover boundary. | Tangential to premium-feel; relevant to any consuming session that adds a sheet — flagged for **P1**'s toast work (the toast is an overlay, not a sheet, so the constraint doesn't bite, but the consuming session must keep it in mind if it promotes the toast to a sheet/cover). |
| [feedback_xcode_build_loop.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_xcode_build_loop.md) | Headless `xcodebuild` iteration to green. | Used by consuming sessions, not this backlog. |
| [feedback_xcodegen_preaction_cancels_build.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_xcodegen_preaction_cancels_build.md) | Never wire xcodegen as a scheme preAction. | Used by consuming sessions, not this backlog. |
| [feedback_computer_use_default_apps.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_computer_use_default_apps.md) | Batch Simulator+Xcode+Terminal in one request_access. | Used by consuming sessions (P5, P6, P9 have computer-use checkpoints). |
| [project_life_clock_signing.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/project_life_clock_signing.md) | Team `92SGDZ88FW`; never stale `3YCTPY88Y4`. | Used by consuming sessions if a device build is needed. |
| MEMORY.md | Index of the above. | Read in full. |

No memory entry contradicts any emitted prompt. Vision Decided constraints re-checked — no proposed move contradicts a constraint (Death-Clock ratchets in **P9** are bounded by the binding reject-list already authored in `polish-2026-05-13-death-clock-reference-match.md`).

## 5. Fixture knob catalog

Source: [LifeClockLaunchConfiguration.swift](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift). Same knob surface as prior backlogs; only knobs this backlog's prompts use are listed.

| Knob | Values | Used by |
|---|---|---|
| `LIFECLOCK_UI_TEST_SCENARIO` | `onboarding` / `onboarded` | P1, P2, P3, P5, P6, P7, P8, P9 |
| `LIFECLOCK_USE_MOCK_HEALTH` | `1` | P1, P2, P3, P5, P6, P8 |
| `LIFECLOCK_SEED_TONE` | `gentle` / `coach` / `firm_direct` | P1, P7, P8 |
| `LIFECLOCK_FORCE_COLOR_SCHEME` | `light` / `dark` | P1, P3, P5 |
| `LIFECLOCK_FORCE_PALETTE` | `default-navy` / `aurora-cool` / `sunset-warm` | P3 |
| `LIFECLOCK_SEED_BAD_DAY` | `1` | P5 (negative-delta WrapUp lighting path) |
| `LIFECLOCK_SEED_STREAK` / `LIFECLOCK_SEED_DAYS_SINCE_INSTALL` / `LIFECLOCK_SEED_BASELINE_ADJUSTMENT` | int / int / float | P5 (cold-launch WrapUp present-condition) |
| `LIFECLOCK_INITIAL_TAB` | `today` / `history` / `profile` | P3, P7 |
| Quest-completion test scaffold (`testTouchpoint*` UITest pattern) | — | P1 (drive the toast to present) |

No fixture-composition gap blocks this backlog (the 5/13 `LIFECLOCK_SEED_SNAPSHOTS` gap is not on any prompt's critical path here — the projected-healthspan-on-Today surface that drove Future-tab dependence was removed in `e443b56`).

## 6. The prompts

Ten prompts. Every prompt uses the binding 9-field template from `skills/canonical/shared/recon-scaffolding.md`. Every prompt cites `premium-bar.md` + a specific category as `Evidence`. No slug semantically overlaps a 2026-05-12/05-13 backlog prompt or a 5/13–5/14 polish log unless the prior log explicitly deferred it (carry-forwards: P5, P6, P9 — each cites the explicit deferral).

---

### 1. SupportMomentToast off-convention shadow → lighting convention (fix-list)

> **Tier:** lighting-gap
>
> **Evidence:** [premium-bar.md § Color and lighting](premium-bar.md) ("Lifecycle-pinned lighting: rotating/dial elements respect the world-fixed lighting convention … Lighting drift = `lighting-gap`"; anti-signal: off-palette / afterthought lighting); operator memory [feedback_life_clock_lighting_convention.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_life_clock_lighting_convention.md) (binding constants). Current source: [SupportMomentToast.swift:63](../../../products/life-clock-ios/Sources/Shared/SupportMomentToast.swift) renders `.shadow(color: Color.black.opacity(0.18), radius: 12, y: 6)` — a hand-rolled drop shadow that ignores the world-fixed convention (`opacity 0.22`, offset ratio `0.35/0.85`, radius `0.55×` reference) while six other surfaces use `cardLighting()` / `lightingDepth(referenceSize:)` from [Lighting.swift](../../../products/life-clock-ios/Sources/Shared/Lighting.swift).
>
> **Idea:** This surface was newly created by the 2026-05-14 SupportMoment→toast rewrite; the raw shadow is the only off-convention lighting site in `Shared/`. Replace the literal `.shadow(...)` with `.cardLighting()` (the toast is a card-shaped surface) OR `.lightingDepth(referenceSize:)` keyed to the toast's height if `cardLighting` reads too heavy for a transient overlay. Do **not** invent new shadow values — adopt the pinned convention exactly. The 2026-05-14 log's own "Next pass" note ("consider replacing material with `DesignTokens.Palette` brand surface for tighter integration") explicitly left this open, so this is not a cooling-off re-emit — it's the deferred follow-up the prior log named.
>
> **Surfaces:** [SupportMomentToast.swift](../../../products/life-clock-ios/Sources/Shared/SupportMomentToast.swift):63, [SupportMomentToastModifier.swift](../../../products/life-clock-ios/Sources/Shared/SupportMomentToastModifier.swift), presented from [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) (`.overlay(alignment: .top)`)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_USE_MOCK_HEALTH=1`, `LIFECLOCK_SEED_TONE=coach`, `LIFECLOCK_FORCE_COLOR_SCHEME=light|dark`; drive a quest completion via the `testTouchpoint*` UITest scaffold so the toast presents.
>
> **Prior context:** [polish-2026-05-14-support-moment-toast-overlay.md](polish-2026-05-14-support-moment-toast-overlay.md) — created the toast with the raw shadow; "Next pass" explicitly deferred brand-surface integration. 5/13 P9 targeted a now-deleted `SupportMomentCard.swift` — that prompt is dead; this one targets the surface that actually exists.
>
> **Success criteria:** `SupportMomentToast.swift` carries `.cardLighting()` or `.lightingDepth(referenceSize:)` (no raw `.shadow` literal). Light + dark screenshots confirm the toast reads as one product with the Today cards. Zero deviation from the lighting-convention constants — if a value seems to need tuning, that's a memory-amendment vision-question routed to the operator, not a silent change.
>
> **Iteration cap:** 3
>
> **Final computer-use checkpoint:** no — single-component lighting fix; PR-time review sufficient.

---

### 2. Reveal-escalator + Future-chart Motion.Duration migration (fix-list)

> **Tier:** motion-incoherence
>
> **Evidence:** [premium-bar.md § Motion](premium-bar.md) ("Durations: every named animation has a duration that fits one of three brand-defined tiers … Random durations = `motion-incoherence`"); [motion-spec.md § Migration target](motion-spec.md) (the binding migration table). Current source: `Motion.Duration` is adopted in only four files (ClockHandView, WrapUpSheet, PaywallSheet, LifeGridDotView). The motion-spec migration table lists [RevealEscalatorScreens.swift:449](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift) (`.easeInOut(duration: 0.35)` → `Motion.Duration.beat`) and [TrajectoryChart.swift:140](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift) (`.smooth(duration: 0.18)` → `Motion.Duration.instant`) as explicit un-migrated targets. Both are still literals.
>
> **Idea:** Mechanical, low-risk migration of the two clearest spec-table sites: `RevealEscalatorScreens.swift:449` `0.35` → `.easeInOut(duration: Motion.Duration.beat)` (0.30); `TrajectoryChart.swift:140` `0.18` → `.smooth(duration: Motion.Duration.instant)`. Both already short-circuit on `reduceMotion` — preserve that guard verbatim. This closes the two motion-spec table rows the 5/13 backlog claimed "migrated" but source disproves. One commit per site or one combined commit per operator preference.
>
> **Surfaces:** [RevealEscalatorScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift):449, [TrajectoryChart.swift](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift):140, [Motion.swift](../../../products/life-clock-ios/Sources/Shared/Motion.swift) (read-only — the source of the constants)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarding` (RevealEscalator cycle), `LIFECLOCK_UI_TEST_SCENARIO=onboarded` + `LIFECLOCK_INITIAL_TAB=future` (chart redraw), `LIFECLOCK_USE_MOCK_HEALTH=1`.
>
> **Prior context:** [motion-spec.md](motion-spec.md) is the binding doc; its migration table names exactly these two rows. 5/13 backlog § coverage matrix claimed Future "Motion.Duration migrated" — source at `ec1361e` contradicts this for the chart.
>
> **Success criteria:** Zero numeric duration literals at `RevealEscalatorScreens.swift:449` and `TrajectoryChart.swift:140` — both reference `Motion.Duration`. `reduceMotion` short-circuit preserved at both. RevealEscalator cycle + Future chart redraw look unchanged to the eye (the tier values were chosen to match existing perceived speed). motion-spec migration table updated to strike these two rows.
>
> **Iteration cap:** 3
>
> **Final computer-use checkpoint:** no — mechanical constant substitution; PR-time review sufficient.

---

### 3. Off-tier onboarding animation durations sweep (`0.32` is not a tier) (freeform-polish)

> **Tier:** motion-incoherence
>
> **Evidence:** [premium-bar.md § Motion](premium-bar.md) ("Durations: … one of three brand-defined tiers (instant 100ms, beat 250ms, breath 500ms). Random durations = `motion-incoherence`"; "Hierarchy: across surfaces, the same kind of event animates the same way"). [motion-spec.md § Anti-tier + § Anti-patterns](motion-spec.md) ("Do not invent a new duration. If your use case doesn't fit instant / beat / breath, the use case is wrong, not the spec"). Current source: [HealthspanRevealView.swift:86](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/HealthspanRevealView.swift), [WhatWeDontDoView.swift:47](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/WhatWeDontDoView.swift) and [:61](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/WhatWeDontDoView.swift) all use `.easeOut(duration: 0.32)` — `0.32` is on **no** tier (instant 0.18 / beat 0.30 / breath 0.60). Additionally [EngineRevealAndDialView.swift:95](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/EngineRevealAndDialView.swift) and [LeadInScreens.swift:337](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift) use a bare literal `.snappy` rather than `Motion.Curve.snappy`.
>
> **Idea:** Sweep the onboarding motion cluster for tier coherence. (1) Three `0.32` `.easeOut` sites → decide per-gesture: a reveal-of-single-element is `Motion.Duration.beat` (0.30) per the spec's own use-for column; if any of the three reads as a larger reveal, `Motion.Duration.breath` — but they should NOT all silently collapse to one tier without a per-site judgment (motion-spec anti-pattern: don't pile mismatched durations, but also don't flatten distinct gestures). (2) Two literal `.snappy` sites → `Motion.Curve.snappy` (no behavior change, just the named constant — closes the motion-spec table rows for EngineRevealAndDial + LeadIn). Capture an onboarding walkthrough before/after; the visible motion should be indistinguishable (the point is vocabulary, not re-tuning). This is the heaviest remaining un-migrated cluster and the reason Onboarding scores `partial` on Motion.
>
> **Surfaces:** [HealthspanRevealView.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/HealthspanRevealView.swift):86, [WhatWeDontDoView.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/WhatWeDontDoView.swift):47,61, [EngineRevealAndDialView.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/EngineRevealAndDialView.swift):95, [LeadInScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift):337, [Motion.swift](../../../products/life-clock-ios/Sources/Shared/Motion.swift) (read-only)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarding` (full lead-in → reveal → dial walkthrough), `LIFECLOCK_USE_MOCK_HEALTH=1`.
>
> **Prior context:** [motion-spec.md § Migration target](motion-spec.md) names EngineRevealAndDial + LeadIn `.snappy` rows. The `0.32` sites are genuinely net-new findings (not in any prior migration table — the spec table predates these call sites or missed them; flag that to the operator so the spec table can be extended).
>
> **Success criteria:** Zero `duration: 0.32` literals in onboarding. The three `.easeOut(0.32)` sites each reference a `Motion.Duration` tier chosen by per-gesture judgment (documented one-line-per-site in the polish log). Both `.snappy` literals → `Motion.Curve.snappy`. Onboarding walkthrough video before/after confirms no perceptible motion change. motion-spec migration table extended with the three `0.32` rows (proposed to operator — the audit reads the spec, the operator owns it).
>
> **Iteration cap:** 4
>
> **Final computer-use checkpoint:** yes — onboarding is a first-impression surface; operator-eye on the before/after walkthrough confirms vocabulary migration didn't change felt pacing.

---

### 4. Numeric-display sites → named DesignTokens token + AccessibilityXXXL clamp (fix-list)

> **Tier:** typography-drift
>
> **Evidence:** [premium-bar.md § Typography](premium-bar.md) ("Scale: one type scale … Fixed-size copy outside the brand-approved exceptions = `typography-drift`"; "Dynamic Type: every text style scales correctly"). [typography-spec.md § The numeric-display exception + § Validation](typography-spec.md) — the exception is permitted *by role family* but the spec's validation rule #4 requires the surface to render at `UIContentSizeCategory.accessibilityExtraExtraExtraLarge` without truncation, and the convention is "any new absolute-size site must map to an existing role family." Current source: [TodayView.swift:289](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) and [WrapUpSheet.swift:67](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift) (`.font(.system(size: 44, weight: .semibold, design: .rounded))` = Display-numeric role) and [OverrideSheet.swift:26](../../../products/life-clock-ios/Sources/Features/History/OverrideSheet.swift) (`.font(.system(size: 32, …))` = Inline-numeric role) are *role-aligned by value* but use raw literals; `DesignTokens.swift` has **no** Typography section, so the exception lives only in the spec doc, not in code, and there is no AccessibilityXXXL clamp on the Display-numeric sites.
>
> **Idea:** Codify the typography-spec role families as a `DesignTokens.Typography` enum (`displayNumeric` = 44/.semibold/.rounded, `inlineNumeric` = 32, etc.) and migrate the three sites to reference it. Add the spec-mandated AccessibilityXXXL safety: `.minimumScaleFactor` + a `dynamicTypeSize(... .accessibility3)` clamp (or `ViewThatFits` degradation) so validation rule #4 is structurally guaranteed, not just asserted. This is the 5/12 P1 finding (typography-drift) — it was *partially* addressed by authoring `typography-spec.md` (which documents the exception conceptually) but the **code** side (named token + clamp) was never landed; this is the deferred residual, not a cooling-off re-emit of a closed item.
>
> **Surfaces:** [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift):289, [WrapUpSheet.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift):67, [OverrideSheet.swift](../../../products/life-clock-ios/Sources/Features/History/OverrideSheet.swift):26, [DesignTokens.swift](../../../products/life-clock-ios/Sources/Shared/DesignTokens.swift) (add Typography enum)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_USE_MOCK_HEALTH=1`; screenshot grid across `dynamicTypeSize` `.xSmall`, `.large`, `.accessibility3`, `.accessibility5`.
>
> **Prior context:** [premium-feel-backlog-2026-05-12-standard.md § P1](premium-feel-backlog-2026-05-12-standard.md) (typography-drift) — the spec doc shipped, the code token + clamp did not. [typography-spec.md § Cross-references](typography-spec.md) names this exact prompt as the open item.
>
> **Success criteria:** `DesignTokens.Typography` enum exists with the spec's role families. All three sites reference it (zero raw `.font(.system(size:))` for numeric-display in `Features/`). AccessibilityXXXL screenshot (`.accessibility5`) shows the delta number does not truncate, overlap, or clip; `.xSmall` doesn't shrink it below ~30pt visual. typography-spec validation #1–#4 verifiably hold for the three sites.
>
> **Iteration cap:** 3
>
> **Final computer-use checkpoint:** yes — the brand-presence vs a11y trade-off on the hero number at `.accessibility5` is operator-grade; review the XXXL vs xSmall screenshot pair.

---

### 5. WrapUp clock-face lighting visual verify against app icon (freeform-polish)

> **Tier:** lighting-gap (verification — explicitly deferred carry-forward)
>
> **Evidence:** [premium-bar.md § Color and lighting + § Surface-level rubric](premium-bar.md) ("WrapUp: motion (sequenced reveal), haptics on each reveal beat, microcopy tone, lighting on the clock face"); operator memory [feedback_life_clock_lighting_convention.md](../../../../../.claude/projects/-Users-simons-ai-company-os/memory/feedback_life_clock_lighting_convention.md). The 5/13 backlog's P5 framed this and the 5/13 readiness flag named it the single highest-leverage premium surface — but no polish log dated 5/13 or 5/14 actually executed the visual verification (the smoke test was code-level only; the 5/14 log was the unrelated SupportMoment toast). The deferral is real and uncashed.
>
> **Idea:** Stand up the cold-launch WrapUp present-condition (`LIFECLOCK_SEED_STREAK=7` + `LIFECLOCK_SEED_DAYS_SINCE_INSTALL=8` + `LIFECLOCK_SEED_BASELINE_ADJUSTMENT=0` per [polish-2026-05-06-wrapup-sequencing-foreground-cycles.md](polish-2026-05-06-wrapup-sequencing-foreground-cycles.md), Monday-return weekly). Capture the WrapUp clock-face render side-by-side with the app icon (the icon is the canonical lighting reference per operator memory). Verify: (a) world-fixed light source reads upper-left, matching the icon; (b) rim depth visible in both light + dark; (c) when the hand rotates during the sequenced reveal the shadow stays world-fixed (inverse-rotation math working, not rotating with the hand); (d) negative-delta path (`LIFECLOCK_SEED_BAD_DAY=1`) also captured. No source change expected — this VERIFIES Sprint D2's wiring. If a constant seems to need tuning, that's a memory-amendment vision-question to the operator, never a silent change.
>
> **Surfaces:** [ClockHandView.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift), [WrapUpSheet.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift), reference at `products/life-clock-ios/Assets.xcassets/AppIcon.appiconset/`
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_SEED_STREAK=7`, `LIFECLOCK_SEED_DAYS_SINCE_INSTALL=8`, `LIFECLOCK_SEED_BASELINE_ADJUSTMENT=0`, `LIFECLOCK_USE_MOCK_HEALTH=1`, `LIFECLOCK_FORCE_COLOR_SCHEME=light|dark`, second run `LIFECLOCK_SEED_BAD_DAY=1`.
>
> **Prior context:** [premium-feel-backlog-2026-05-13-standard.md § P5](premium-feel-backlog-2026-05-13-standard.md) framed it; it was the #1 green-flipping prompt on the 5/13 readiness flag and remains uncashed two days later. Cooling-off exception: explicitly deferred by the prior log's own readiness section.
>
> **Success criteria:** WrapUp clock-face side-by-side with app icon, both schemes + negative-delta path, captured into a `polish-2026-05-15-wrapup-lighting-visual-verify.md`. Operator-confirmable statement: "the icon, the Today mascot hand, and the WrapUp clock face read as one lighted artifact." Inverse-rotation world-fixed shadow confirmed during the rotating reveal. Zero constant deviation.
>
> **Iteration cap:** 4
>
> **Final computer-use checkpoint:** yes — reference-match against the icon is operator-only; this IS the verification.

---

### 6. Reduce-Motion system-toggle visual verify across all animated surfaces (freeform-polish)

> **Tier:** motion-incoherence (verification — explicitly deferred carry-forward)
>
> **Evidence:** [premium-bar.md § Motion](premium-bar.md) ("Reduction respect: every animation respects `UIAccessibility.isReduceMotionEnabled`. Missing reduction paths = `motion-incoherence`"). [motion-spec.md § Anti-patterns](motion-spec.md) ("Do not animate motion for users with `reduceMotion`. Every modifier must short-circuit"). Current source: only 10 files under `Features/` reference `reduceMotion`. The 5/13 backlog's P2 framed an RM visual pass as the #3 green-flipping prompt; no polish log has executed it (the smoke test was build-only by its own admission). Build-green ≠ visually-correct under the system toggle.
>
> **Idea:** One simulator session with Settings → Accessibility → Motion → Reduce Motion ON. Walk every `withAnimation` / `.animation` / `KeyframeAnimator` site and produce a one-row-per-site table: animation suppressed = ✅ / still firing = ✗ / haptic+state-change-only = ✅(correct). Critical site per operator memory `feedback_life_clock_wake_animation.md`: with RM ON the wake's haptic must still fire while the scale/opacity transition is suppressed (cold launch specifically). Cross-check the sites this backlog's P2/P3 touch (RevealEscalator, TrajectoryChart, the three `0.32` onboarding sites, EngineRevealAndDial, LeadIn) plus TodayView mascot keyframes, WrapUpSheet sequencing, ClockHandView reveal, PaywallSheet selection ring. Any ✗ triggers an immediate fix-list follow-up before that surface's premium-readiness can be claimed.
>
> **Surfaces:** [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift), [WrapUpSheet.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift), [ClockHandView.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/ClockHandView.swift), [RevealEscalatorScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift), [TrajectoryChart.swift](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift), [PaywallSheet.swift](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift), [HealthspanRevealView.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/HealthspanRevealView.swift), [LeadInScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded` (Today/WrapUp/chart) + `=onboarding` (reveal cluster), `LIFECLOCK_USE_MOCK_HEALTH=1`. Reduce Motion toggled via Simulator → Settings → Accessibility → Motion.
>
> **Prior context:** [premium-feel-backlog-2026-05-13-standard.md § P2](premium-feel-backlog-2026-05-13-standard.md) framed it as a green-flipping verification; never executed. [polish-2026-05-05-today-screen-morning-greeting.md](polish-2026-05-05-today-screen-morning-greeting.md) pinned the wake's RM gate. Cooling-off exception: explicitly deferred by the prior log's readiness section.
>
> **Success criteria:** A per-site RM-on table in a `polish-2026-05-15-reduce-motion-visual-verify.md`. Each site: ✅ suppressed / ✗ still firing / ✅ haptic-only. Wake-haptic-without-animation confirmed for cold-launch. Any ✗ filed as an immediate fix-list follow-up. The 10 `reduceMotion`-guarded files cross-checked against the full animated-site inventory to confirm no animated site lacks a guard.
>
> **Iteration cap:** 3
>
> **Final computer-use checkpoint:** yes — RM verification IS the operator visual checkpoint.

---

### 7. OverrideSheet error-state copy → on-brand, tone-aware, actionable (fix-list)

> **Tier:** empty-state-flat
>
> **Evidence:** [premium-bar.md § Empty states](premium-bar.md) ("Specificity: every empty state has copy that addresses the specific empty condition … Generic 'No data' = `empty-state-flat`"; "Action affordance: every empty state offers at least one next-step"; "Brand coherence: empty-state copy matches the active tone mode"). Anti-signal: "Empty states that end with 'no data' and no next step." Current source: [OverrideSheet.swift:76](../../../products/life-clock-ios/Sources/Features/History/OverrideSheet.swift) sets `errorMessage = "No data for this day yet."` in the `snapshotMissing` catch — rendered at [:33](../../../products/life-clock-ios/Sources/Features/History/OverrideSheet.swift) as a bare red string with no next-step and no tone variation, while sibling errors at :72 already use `store.toneMode.overrideNotEntitledMessage`.
>
> **Idea:** Replace the hardcoded `"No data for this day yet."` with a tone-aware, actionable string consistent with the `overrideNotEntitledMessage` pattern already in the same file. Add a `ToneMode.overrideNoSnapshotMessage` (or equivalent) with gentle/coach/firmDirect variants that name the condition AND the next step (e.g., coach: "Nothing logged for this day — there's nothing to override yet. Pick a day with data."). This is the lowest-effort, highest-rubric-clarity item: it's been carried as a known micro-residual in the 5/12 and 5/13 state summaries but never emitted as its own prompt — so it is cooling-off-clear (no prior prompt slug owns it).
>
> **Surfaces:** [OverrideSheet.swift](../../../products/life-clock-ios/Sources/Features/History/OverrideSheet.swift):76 (+ :33 render site), [ToneMode.swift](../../../products/life-clock-ios/Sources/App/ToneMode.swift) (add the tone keys, mirroring `overrideNotEntitledMessage`)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarded`, `LIFECLOCK_SEED_TONE=gentle|coach|firm_direct` (verify all three variants); reach the `snapshotMissing` path by opening Override on a day with no snapshot (History → a no-data day → override).
>
> **Prior context:** Carried as a known residual in [premium-feel-backlog-2026-05-12-standard.md § 1 state summary](premium-feel-backlog-2026-05-12-standard.md) and [2026-05-13 § 1](premium-feel-backlog-2026-05-13-standard.md) ("anti-signal-positive on rubric grounds, even though it's a catch branch") — explicitly noted as not-yet-emitted, so eligible now.
>
> **Success criteria:** Zero `"No data for this day yet."` literal in `Features/`. `OverrideSheet` renders a tone-aware string (3 variants) that names the condition and a next step. Three-tone screenshot grid confirms variation. The other catch-branch literals (`"Out of range."`, `"Couldn't save."`) reviewed for the same treatment in the same diff if cheap (note them; don't scope-creep if not).
>
> **Iteration cap:** 3
>
> **Final computer-use checkpoint:** no — copy + tone-key change; PR-time review sufficient.

---

### 8. Cross-surface "value increased by user action" motion-hierarchy coherence sweep (freeform-polish)

> **Tier:** motion-incoherence
>
> **Evidence:** [premium-bar.md § Motion](premium-bar.md) ("Hierarchy: across surfaces, the same kind of event animates the same way (e.g., 'value increased by user action' looks identical on Today, History, and Quest screens). Per-screen reinvention = `motion-incoherence`"). [motion-spec.md § One-line rule](motion-spec.md) ("Pick the duration that matches the conceptual weight of the gesture"). Current source: the same conceptual event — *a tracked number changes in response to the user* — animates differently per surface: Today quest-completion uses `displayedDelta` + a `.bouncy` SpringKeyframe at 0.22/0.30 ([TodayView.swift:475–477](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift)); the Future chart uses `.smooth(duration: 0.18)` ([TrajectoryChart.swift:140](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift)); the dial uses literal `.snappy` ([EngineRevealAndDialView.swift:95](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/EngineRevealAndDialView.swift)); the lead-in reactive slider uses literal `.snappy` ([LeadInScreens.swift:337](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift)). Four different motion signatures for one conceptual event.
>
> **Idea:** This is the elevation prompt the rubric's Motion-hierarchy clause exists for — it is NOT a duplicate of P2/P3 (which migrate individual literals to tiers); this asks the higher question: *does "a number the user moved" feel like the same gesture everywhere?* Produce a one-page motion-hierarchy map: for each surface, what event class fires, what curve+duration, is it `Motion.Curve.snappy`-celebratory or `Motion.Curve.smooth`-informational? Then propose (do not unilaterally ship — this is freeform-polish that lands in Stretch tier per the adapter's decision-tier reminder) a single coherent rule: e.g., "user-caused value change that is a *win* → `Motion.Curve.snappy` + `Motion.Duration.beat`; user-caused value change that is *informational* (chart scrub) → `Motion.Curve.smooth` + `Motion.Duration.instant`." Respect operator memory `feedback_life_clock_wake_animation.md` — the daily wake is a *greeting*, a different event class, explicitly out of this sweep. Respect Decided 2026-05-13 (quest-completion A+B+C layered) — the quest payoff choreography is ratcheted; this sweep aligns the *vocabulary* it uses, never removes a layer.
>
> **Surfaces:** [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift):459–477, [TrajectoryChart.swift](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift):140, [EngineRevealAndDialView.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/EngineRevealAndDialView.swift):95, [LeadInScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift):337, [Motion.swift](../../../products/life-clock-ios/Sources/Shared/Motion.swift) (read-only)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarding` (dial + lead-in slider), `=onboarded` (Today quest-completion via `testTouchpoint*` scaffold + Future chart), `LIFECLOCK_USE_MOCK_HEALTH=1`, `LIFECLOCK_SEED_TONE=coach`.
>
> **Prior context:** No prior prompt addressed motion *hierarchy* (5/12 P3 was a duration-tier sweep, not a hierarchy map; 5/13 P7 was Death-Clock reference, not internal coherence). Genuinely net-new elevation surface.
>
> **Success criteria:** A motion-hierarchy map in `polish-2026-05-15-motion-hierarchy-sweep.md`: per-surface event-class + curve/duration table, the proposed single coherent rule, and a scoped diff list (which call sites change to satisfy the rule). No source change required in this prompt if the operator wants to review the rule first (freeform-polish → Stretch tier). Decided 2026-05-13 quest-payoff layers explicitly preserved; wake explicitly excluded with a one-line rationale citing the operator memory.
>
> **Iteration cap:** 4
>
> **Final computer-use checkpoint:** yes — cross-surface motion coherence is a felt-quality judgment; operator reviews the before-state captures and the proposed rule.

---

### 9. Death Clock reveal — on-device visual frame capture (the deferred half) (reference-match)

> **Tier:** motion-incoherence (elevation via reference — explicitly deferred carry-forward)
>
> **Evidence:** [premium-bar.md § Motion + § Surface-level rubric](premium-bar.md) (Today motion + reveal-escalator + WrapUp sequenced reveal are the three ceremonial moments). [vision.md § References — Decided 2026-05-13](vision.md) ("Premium-feel reference app: Death Clock: The Life Lab … *Match the craft, reject the framing*"). [polish-2026-05-13-death-clock-reference-match.md § Limitations](polish-2026-05-13-death-clock-reference-match.md): "**Text-only capture.** Visual side-by-side frame captures of the actual reveal sequences would be a stronger comparison. Recommended operator follow-up: install Death Clock from the App Store, capture the reveal sequence and the daily-headline tick on screen (10-second video each); compare against Life Clock's RevealEscalator + Today wake." The framing-reject guardrails are already binding; the visual half is explicitly, named-ly deferred.
>
> **Idea:** Execute exactly the deferred operator follow-up: (with operator approval to install a third-party app) capture Death Clock's reveal sequence + daily-headline tick on-device, 10s each; capture Life Clock's RevealEscalator + Today wake + Future chart redraw at matched duration; produce a frame-by-frame side-by-side. Score against the 5/13 log's existing 3-axis matrix (number-animation craft / reveal pacing / transition feel) but now with real motion data instead of inferred. Output 1–3 *concrete* ratchet recommendations that supersede the 5/13 log's inferred ones — note that 5/13 ratchet #2 ("trajectory-peek ticking on Today") is now **void** because `e443b56` removed the projected-healthspan card from Today; do not resurrect it. **Binding:** import zero items from the 5/13 reject-list (mortality lexicon, prophecy framing, AI concierge, bloodwork, 8-SKU ladder, trial framing, continuous death-countdown, mortality-ending reveal). The reject-list in the 5/13 log is the brake and stays in force.
>
> **Surfaces:** [RevealEscalatorScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift), [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) (wake), [TrajectoryChart.swift](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift), reference recordings under `docs/products/life-clock/research/death-clock-visual-2026-05-15/`
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarding` (RevealEscalator), `=onboarded` (Today wake + Future chart), `LIFECLOCK_USE_MOCK_HEALTH=1`.
>
> **Prior context:** [polish-2026-05-13-death-clock-reference-match.md](polish-2026-05-13-death-clock-reference-match.md) — text-only; its § Limitations explicitly names this visual capture as the recommended follow-up. Cooling-off exception: prior log explicitly deferred this exact work.
>
> **Success criteria:** `polish-2026-05-15-death-clock-visual-reference-match.md` with real frame-by-frame side-by-side, the 3-axis matrix re-scored with motion data, 1–3 concrete ratchets, an explicit "void: 5/13 ratchet #2 (projected-healthspan removed in `e443b56`)" note, and the binding reject-list re-affirmed. Zero source change in this prompt. Vision Decided 2026-05-04 + 2026-05-13 cited verbatim.
>
> **Iteration cap:** 5
>
> **Final computer-use checkpoint:** yes — reference-match against a real installed app is the whole point.

---

### 10. Vision-question: should "Cross-screen reveal continuity" be a premium-bar category? (vision-driven)

> **Tier:** vision-question
>
> **Evidence:** [premium-bar.md § Transitions](premium-bar.md) covers *between-screen coherence*, *return-to-state*, and *no-flash-of-empty-state* — but NOT whether a *ceremonial* moment carries continuity across a screen boundary (e.g., the mascot/number anchoring across reveal→paywall instead of blinking). [polish-2026-05-13-death-clock-reference-match.md § Ratchet #1](polish-2026-05-13-death-clock-reference-match.md) identified that `RecoveryPreviewView` → `PaywallPrimaryView` is a hard NavigationStack push with no anchored element, and proposed a `Motion.Duration.breath` crossfade with the mascot scale held stable across the transition — but flagged this as needing an operator decision because changing onboarding flow is high-leverage. This gap doesn't fit any existing `premium-bar.md` category cleanly (Transitions is about *not breaking* state, not about *ceremonial continuity*). Per the skill's anti-pattern rule ("Do NOT introduce a new category not in `premium-bar.md`; escalate to `vision-question` proposing the operator add the category"), this is escalated, not silently scored.
>
> **Idea:** Two valid directions, operator-pick required: **(A) Add a "Cross-screen reveal continuity" category to `premium-bar.md`** — a named premium signal that ceremonial moments (reveal→paywall, Today→WrapUp, quest-completion→payoff) carry an anchored element across the boundary rather than hard-cutting; this would make the Death-Clock ratchet #1 a `premium-gap` the audit can score going forward. **(B) Keep the rubric as-is and treat reveal→paywall continuity as a one-off Stretch polish** under the existing Transitions category, accepting that the rubric doesn't systematically cover ceremonial continuity. Trade-off: (A) raises the bar permanently and makes future ceremonial surfaces inherit the expectation, at the cost of a new audit dimension to score every run; (B) keeps the rubric lean but lets ceremonial-continuity gaps slip through un-systematized. The skill cannot edit `premium-bar.md` (operator owns the rubric) — this prompt produces the decision memo + the exact category text to paste if (A); it does not append to vision Open Questions (recon-family skills must not).
>
> **Surfaces:** [premium-bar.md](premium-bar.md) (operator-owned — proposed category text only), [OnboardingCoordinator.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/OnboardingCoordinator.swift) (the reveal→paywall transition site), [RevealEscalatorScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/RevealEscalatorScreens.swift), [PaywallPrimaryView.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift)
>
> **Fixture knobs:** `LIFECLOCK_UI_TEST_SCENARIO=onboarding` (walk reveal→paywall to capture the current hard-cut), `LIFECLOCK_USE_MOCK_HEALTH=1`.
>
> **Prior context:** [polish-2026-05-13-death-clock-reference-match.md § Ratchet #1](polish-2026-05-13-death-clock-reference-match.md) named the reveal→paywall hard-cut and proposed the crossfade but gated it on operator approval; no rubric category covers ceremonial continuity. Net-new vision-question (no prior backlog raised the rubric-category question).
>
> **Success criteria:** A decision memo `polish-2026-05-15-cross-screen-continuity-vision-question.md` with: a capture of the current reveal→paywall hard-cut, options A vs B with the trade-off articulated, the exact `premium-bar.md` category prose to paste if the operator picks A, and an explicit statement that the skill did NOT edit `premium-bar.md` or `vision.md`. No source change. If operator picks A in-session, the rubric edit is the operator's to make, then a future audit scores against it.
>
> **Iteration cap:** 3
>
> **Final computer-use checkpoint:** yes — the operator reviews the current hard-cut capture to make the A/B call.

---

## 7. Variety check

Declared distribution across modes and tiers:

| Mode | Count | Floor (standard) | Met? | Prompts |
|---|---|---|---|---|
| `fix-list` | 4 | ≥2 | ✓ | P1, P2, P4, P7 |
| `freeform-polish` | 4 | ≥3 | ✓ | P3, P5, P6, P8 |
| `reference-match` | 1 | ≥2 | **⚠️ short by one** | P9 |
| `vision-driven` | 1 | ≥1 | ✓ | P10 |
| **Total** | **10** | min 10 / max 40 | ✓ count | — |

**Variety-mandate exception logged** (per `shared/recon-scaffolding.md` § "Variety mandate" rule 2, and consistent with operator memory `feedback_simulator_polish_recon_calibration.md` rule 3: never pad to the floor). The standard floor is **≥2 `reference-match`**; this backlog emits **one** (P9). The two operator-anchored premium references — Death Clock (premium-feel) and MacroFactor (pro-value) — were both consumed on 2026-05-13 (`polish-2026-05-13-death-clock-reference-match.md`, `polish-2026-05-13-macrofactor-reference-match.md`). MacroFactor is pro-value-audit's reference, not this skill's. Death Clock's *text-only* pass is done; its *visual* half is the explicitly-deferred carry-forward emitted as P9. There is no second sanctioned premium-feel reference in `vision.md § References` or `reference-apps.md` to author a second `reference-match` against. Inventing one (a random App Store competitor not anchored by the operator) would be variety theater and would violate the cooling-off + reference-anchor discipline. **The slip is honest, not lazy.** Operator's call: accept the one-short slip (recommended — the audit found exactly one legitimate reference move), OR anchor a second premium-feel reference in `reference-apps.md` and re-run. This is materially the same slip the 5/13 backlog logged; the polish-saturation calibration memory predicts this and says surface it rather than pad.

| Tier | Count | Prompts |
|---|---|---|
| `lighting-gap` | 2 | P1 (net-new), P5 (deferred verification) |
| `motion-incoherence` | 4 | P2, P3 (live un-migrated), P6 (deferred verification), P8 (hierarchy elevation), P9 (reference) — note P9 counted once under its mode; tier-wise it is motion-incoherence-via-reference |
| `typography-drift` | 1 | P4 |
| `empty-state-flat` | 1 | P7 |
| `vision-question` | 1 | P10 |

(P9 appears in both the `motion-incoherence` tier conceptually and the `reference-match` mode row — mode and tier are orthogonal axes per the schema.)

No `submission-blocker`-tier prompts. Touch-targets and a11y-contrast remain clean (no regression found in the source walk; `polish-2026-05-12-trajectory-chart-a11y-colorblind-xxl.md` + accessibility-spec coverage stand). The premium-readiness flag is therefore not auto-red on submission grounds.

## 8. Recommended sequencing

**Phase A — quick, independent, high-clarity fixes** (run first, parallelizable):

1. **P1** (SupportMomentToast lighting) — net-new lighting-gap; isolated single-component fix.
2. **P7** (OverrideSheet error copy) — lowest-effort, highest-rubric-clarity; isolated.
3. **P2** (RevealEscalator + chart Motion.Duration) — mechanical; closes two motion-spec table rows.

**Phase B — motion vocabulary depth** (run after P2 so the migrated sites are stable):

4. **P3** (off-tier `0.32` + `.snappy` onboarding sweep) — extends P2's discipline; should follow P2 so the migration pattern is established.
5. **P4** (numeric-display token + clamp) — independent of motion work; can run parallel to P3.

**Phase C — verifications** (run after A+B so the visual baseline is clean):

6. **P5** (WrapUp clock-face lighting visual verify) — depends on nothing but benefits from P1 closing so all lighting reads coherent.
7. **P6** (Reduce-Motion visual verify) — should run AFTER P2/P3/P4 land so it verifies the migrated state, not the pre-migration state (else it must be re-run).

**Phase D — elevation + decisions** (run last):

8. **P8** (motion-hierarchy sweep) — benefits from P2/P3 done so the hierarchy map reflects migrated vocabulary.
9. **P9** (Death Clock visual reference) — benefits from P5/P6 closing so the operator compares against a clean visual baseline.
10. **P10** (cross-screen continuity vision-question) — benefits from P9's visual reference so the A/B decision is informed by the Death-Clock ceremonial-continuity comparison.

Dependency arrows: **P2 → P3** (establish migration pattern first); **P2/P3/P4 → P6** (verify the migrated state, not the old one); **P9 → P10** (the reference informs the rubric-category decision); **P1 → P5** (all lighting coherent before the icon-match verification).

**If you only run three this month:** **P5, P2, P1.** P5 closes the single highest-leverage premium surface (the WrapUp ceremony) that has been "build-verified, visual-deferred" for two audit cycles — it is the #1 green-flipping move. P2 closes the most-cited live `motion-incoherence` (the motion-spec's own table contradicting the 5/13 "migrated" claim). P1 closes the only net-new regression — an off-convention shadow the 5/14 rewrite introduced — before it sets a precedent for future overlays.

## 9. Readiness flag

**Premium-readiness: yellow.**

Strict-mode green requires ALL of:

- [x] Every `premium-bar.md` category has a polish session log covering it in the last 30 days — **yes** (the seven product specs + Sprints A–D + smoke test + the 5/13–5/14 logs land coverage on every category).
- [ ] Zero unresolved `motion-incoherence` prompts — **NO.** P2 + P3 are *live* un-migrated literals (motion-spec's own binding table, not closed in source); P8 is an elevation gap; P6 is an uncashed verification. This is the primary green-blocker.
- [x] Zero unresolved `typography-drift` prompts — **partial→no.** P4 is open (named token + AccessibilityXXXL clamp never landed; spec doc exists but code doesn't). One prompt, not categorical; contributes to yellow not red.
- [ ] Zero unresolved `lighting-gap` prompts — **NO.** P1 is a net-new off-convention shadow (5/14 rewrite); P5 is the uncashed highest-leverage verification.
- [x] Every Decided constraint in `vision.md` has a polish log demonstrating premium-bar compliance — **yes** (Decided 2026-05-12 reveal escalator, 2026-05-13 quest payoff, 2026-05-13 references all have logs).
- [ ] Lifecycle-pinned lighting convention applied on every rotating/dial surface — **build-verified for WrapUp (Sprint D2); visual verification still uncashed (P5); and SupportMomentToast (P1) is verifiably off-convention in source.**

**Why not green:** two categories have *live in-source* gaps, not just deferred verifications. The 5/13 backlog flagged itself "yellow→green pending five verifications" — but source inspection at `ec1361e` shows the motion-spec migration table is only ~40% applied (the 5/13 coverage matrix's "Motion.Duration migrated" claim for Future is contradicted by `TrajectoryChart.swift:140`), and the 5/14 SupportMoment rewrite introduced a net-new off-convention shadow. Green was never actually reachable by "just running the five verifications" — there is real code work (P1–P4) plus the verifications (P5, P6).

**Why not red:** zero `submission-blocker`. Loading category is fully premium (a 5/13 gap genuinely closed). Nothing categorical has gone unaddressed >30 days — the motion + lighting gaps are days old (motion-spec authored 5/12, SupportMoment rewrite 5/14). Touch-targets / a11y-contrast clean.

**The three prompts that would flip yellow → green:**

1. **P2** (RevealEscalator + chart Motion.Duration migration) + **P3** (off-tier onboarding sweep) — together these close the live `motion-incoherence` count to zero (the spec table fully applied). Counting as the motion pair.
2. **P1** (SupportMomentToast → lighting convention) — closes the net-new `lighting-gap` regression.
3. **P5** (WrapUp clock-face lighting visual verify) — closes the last uncashed lighting verification on the highest-leverage premium surface.

After P1, P2, P3, P5 land (P4 + P6 close the typography + RM-verification residuals shortly after), re-running this audit should report **green**.

---

> **Cross-cutting elevation themes (one paragraph for the operator):** The dominant theme is **claim-vs-source drift**. The 5/13 backlog declared "yellow→green pending five visual verifications," but the verifications were never executed (no 5/13 or 5/14 polish log carries them out) and, more importantly, source inspection at `ec1361e` shows the underlying code work was only *partially* done: `motion-spec.md` authored a binding 10-site migration table, but only ~4 sites adopted `Motion.Duration` and exactly one uses `Motion.Curve` — the reveal escalator, the trajectory chart, two onboarding screens, the dial, and the lead-in still carry ad-hoc literals, and `0.32` isn't even on a defined tier. The system spine (Motion / Lighting / Spinner / EmptyState / DesignTokens) exists, which is genuine progress — loading states are now authentically premium — but a spine only elevates the product if every surface adopts it, and adoption stalled around 40% for motion. Compounding this, the 2026-05-14 SupportMoment→toast rewrite shipped a hand-rolled `.shadow` that bypasses the world-fixed lighting convention entirely: the first new surface built *after* the spine landed didn't inherit it, which is exactly the failure mode the spine was meant to prevent. The honest read per the polish-saturation calibration memory: Life Clock is not polish-saturated on premium-feel — it has a real, finishable elevation backlog (finish the motion migration, make new surfaces inherit the conventions, cash the two long-deferred visual verifications). This is a "finish what the spine started" cycle, not a "find new gaps" cycle. The reference-match floor slip is honest (no second operator-anchored premium reference exists; padding would be theater). A natural next full standard audit lands ~2026-05-29 once P1–P6 close and the spine adoption is verifiably complete.
