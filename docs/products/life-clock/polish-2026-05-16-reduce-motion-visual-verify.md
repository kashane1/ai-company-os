# Polish Session — life-clock — 2026-05-16 — reduce-motion-visual-verify

## Mode

freeform-polish (VERIFICATION). Consumes PF-P6 from
`premium-feel-backlog-2026-05-15-standard.md` § 6 — "Reduce-Motion
system-toggle visual verify across all animated surfaces". Verifies the
post-migration motion state (PF-P2/PF-P3 `Motion.Duration`/`Motion.Curve`
migrations + PF-P4 typography clamp already landed; HEAD `5b01c38`).
Default outcome: per-site RM-on table; ✗ rows → follow-ups or
unambiguous Polish-tier guard fixes shipped.

## Environment

- Branch `claude/dazzling-roentgen-dfcc33`, baseline HEAD `5b01c38`.
- Sim: iPhone 17 Pro Max, UDID `942B6264-62E2-4663-8230-80E9133C824E`
  (prompt-specified device; it was *Shutdown* at session start despite
  the prompt saying "booted" — a different 17 Pro Max `8491AD48…` was
  the booted one. I booted the prompt-specified UDID to honor the input
  contract).
- **Reduce Motion toggled via** `xcrun simctl spawn <udid> defaults
  write com.apple.Accessibility ReduceMotionEnabled -bool true` then a
  full app relaunch. The `simctl ui` subcommand on this runtime does
  NOT expose a `reduce_motion` option (only appearance / increase_contrast
  / content_size), so the defaults-domain method is the lock-independent
  path. Verified `ReduceMotionEnabled = 1` before and after the fix
  build.
- **Capture method:** `xcrun simctl io <udid> screenshot` (framebuffer,
  lock-independent fallback). computer-use was NOT used — the
  framebuffer screenshots were sufficient and lock-independent, matching
  the prompt's stated fallback. Screen lock state not relevant to this
  method.
- Build: `xcodegen generate` (standalone) → `xcodebuild` scheme
  `LifeClock`, signing team `92SGDZ88FW`. **BUILD SUCCEEDED** baseline
  and post-fix.
- Captures: `docs/products/life-clock/research/reduce-motion-2026-05-16/`
  (`today-rm-on.png`, `today-rm-on-after-fix.png`, `onboarding-rm-on.png`).

## RM-on per-site table

Legend: ✅ suppressed/RM-aware · ✗ still firing (no/incorrect guard) ·
✅(haptic) haptic+state-change only, correct under RM.

| # | Site | File:line | Mechanism | Guard | Verdict |
|---|---|---|---|---|---|
| 1 | Today wake sweep (`wakeProgress` 0→1) | TodayView.swift:228–231 | `withAnimation(.easeOut)` | `guard !reduceMotion` (pre-fix whole-fn; post-fix split) | ✅ suppressed |
| 2 | Today wake mascot scale keyframe | TodayView.swift:453–464 | `.keyframeAnimator(trigger: mascotWakeTrigger)` | trigger only incremented when `!reduceMotion` | ✅ suppressed |
| 3 | **Today wake HAPTIC (cold-launch)** | TodayView.swift:232 → :482 | `.sensoryFeedback(morningWake, trigger:)` | **PRE-FIX: killed by `guard !reduceMotion` ✗** → **POST-FIX: fires under RM ✅(haptic)** | **✗→✅ FIXED** |
| 4 | Today quest-completion pulse keyframe | TodayView.swift:469–480 | `.keyframeAnimator(trigger: questCompletionPulseTrigger)` | trigger only incr. when `!reduceMotion` (:205) | ✅ suppressed |
| 5 | Today quest-completion HAPTIC | TodayView.swift:481 | `.sensoryFeedback(.success, trigger: questCompletionHapticTrigger)` | separate trigger, fires under RM by design (:36–40) | ✅(haptic) |
| 6 | Today monthly-milestone HAPTIC | TodayView.swift:616 | `.sensoryFeedback(monthlyMilestone, trigger:)` | state-change haptic, no motion | ✅(haptic) |
| 7 | Mascot minutesDelta spring | LifeClockMascotView.swift:127 | `.animation(value: minutesDelta)` | `reduceMotion ? nil :` | ✅ suppressed |
| 8 | Mascot heartbeat hub pulse | LifeClockMascotView.swift:288 | `TimelineView(.animation)` | `frozen = reduceMotion \|\| !isVisible` → static Circle | ✅ suppressed |
| 9 | ClockHandView rotation reveal | ClockHandView.swift:88,99 | `withAnimation` rotation | RM branch: short `.easeInOut(beat)` + opacity cross-fade (:60); reduced, not eliminated | ✅ RM-aware (note↓) |
| 10 | ClockHandView reveal HAPTIC | ClockHandView.swift:69 | `.sensoryFeedback(haptic, trigger: rotated)` | fires under RM (rotated still flips) | ✅(haptic) |
| 11 | WrapUpSheet Pro-signal reveal | WrapUpSheet.swift:116–122 | `withAnimation(.smooth(beat))` | `if reduceMotion { …instant }` | ✅ suppressed |
| 12 | TrajectoryChart redraw | TrajectoryChart.swift:139–142 | `.animation(value: points)` | `(isScrubbing \|\| reduceMotion) ? nil :` | ✅ suppressed |
| 13 | RevealEscalator lever spring | RevealEscalatorScreens.swift:428 | `.animation(value: leverValue)` | `reduceMotion ? nil :` | ✅ suppressed |
| 14 | RevealEscalator cycling index | RevealEscalatorScreens.swift:449 | `.animation(value: cyclingIndex)` | `reduceMotion ? nil :` | ✅ suppressed |
| 15 | EngineRevealAndDial year tick | EngineRevealAndDialView.swift:95 | `.animation(value: displayedYears)` | `reduceMotion ? nil : Motion.Curve.snappy` | ✅ suppressed |
| 16 | EngineRevealAndDial reveal HAPTIC | EngineRevealAndDialView.swift:67 | `.sensoryFeedback(firstReveal, trigger:)` | state-change haptic | ✅(haptic) |
| 17 | LeadIn reactive slider | LeadInScreens.swift:337 | `.animation(value: aggregate)` | `reduceMotion ? nil : Motion.Curve.snappy` | ✅ suppressed |
| 18 | HealthspanReveal lever rows stagger | HealthspanRevealView.swift:85 | `.animation(value: visibleRows)` | `reduceMotion ? nil :` | ✅ suppressed |
| 19 | WhatWeDontDo bullet stagger | WhatWeDontDoView.swift:46 | `.animation(value: visibleCount)` | `reduceMotion ? nil :` | ✅ suppressed |
| 20 | WhatWeDontDo footer fade | WhatWeDontDoView.swift:60 | `.animation(value: visibleCount)` | `reduceMotion ? nil :` | ✅ suppressed |
| 21 | PaywallSheet scroll-to | PaywallSheet.swift:65–71 | `withAnimation(.smooth(instant))` | `if reduceMotion { …instant scrollTo }` | ✅ suppressed |
| 22 | PaywallProductsView selection ring (PV-P2 extracted core) | PaywallProductsView.swift:217 | `.animation(value: selectedProductID)` | `reduceMotion ? nil : .smooth(instant)` | ✅ suppressed |
| 23 | LifeGridDot draw-in | LifeGridDotView.swift:65,71 | `withAnimation(.easeInOut(breath))` | `if reduceMotion { progress = 1 }` both onAppear + onChange | ✅ suppressed |
| 24 | **SupportMomentToast slide+spring** | SupportMomentToastModifier.swift:31 | `.animation(value: supportMoment)` + `.move+.opacity` transition | **PRE-FIX: NO reduceMotion guard ✗** → **POST-FIX: `reduceMotion ? nil`/`.opacity` ✅** | **✗→✅ FIXED** |

**Totals: 24 sites checked** — 18 ✅ suppressed · 5 ✅(haptic, correct) ·
1 ✅ RM-aware-reduced (site 9, note below) · **2 ✗ found and FIXED this
session** (sites 3 + 24). Zero remaining ✗.

### Cold-launch wake haptic-without-animation — CONFIRMED (post-fix)

Per operator memory `feedback_life_clock_wake_animation.md` (and PF-P6's
binding requirement): with RM ON the cold-launch wake HAPTIC must STILL
fire while the scale/opacity transition is SUPPRESSED. **Pre-fix this
was BROKEN** — `triggerWakeIfPossible()` had a single
`guard !reduceMotion` at the top that returned before
`morningWakeHapticTrigger &+= 1`, so under RM the cold-launch greeting
fired NO haptic at all. This contradicted both the prompt's binding
requirement and the codebase's own established quest-completion
split-trigger pattern (TodayView.swift:36–40, which explicitly documents
"iOS's Reduce Motion accessibility setting does not disable haptics").
**Post-fix:** the haptic trigger is incremented BEFORE the
`guard !reduceMotion`; the visual sweep + mascot keyframe remain
suppressed. Behavior now matches the ratchet. (Haptics are non-visual;
confirmed by source — the screenshot confirms the *visual* half:
mascot/sweep at rest under RM, no regression pre vs post fix.)

## Iterations

- `33716f4` — fix(life-clock): wake haptic survives Reduce Motion (split trigger out of the RM guard) — Polish — TodayView
- `88e36d8` — fix(life-clock): Reduce-Motion guard for SupportMomentToast slide-in — Polish — SupportMomentToastModifier
- (this log) — docs(life-clock): PF-P6 reduce-motion visual-verify table

## Stretch decisions (operator review)

None. Both shipped changes are unambiguous Polish-tier missing/incorrect
RM-guard fixes (per the prompt's "if it's an unambiguous missing
`reduceMotion` guard that's a clear Polish-tier fix you may ship it").
No passing animation was retuned.

## Asks

### Resolved this session

None requiring operator input.

### Outstanding (cycle-end batch)

- **Note, not a blocking Ask — site 9 (ClockHandView).** Its doc comment
  (lines 9–10) claims RM "replaces rotation with a 250ms cross-fade",
  but the RM branch (line 88) still runs
  `withAnimation(.easeInOut(duration: Motion.Duration.beat)) { rotated
  = true }` — i.e. the `.rotationEffect` *still animates* over a short
  beat under RM; only the opacity does a true cross-fade. This is a
  *reduced* motion path (short, single-shot, lands final state), not a
  hard short-circuit, and is arguably acceptable under RM (it is not a
  large continuous sweep). Flagging as a doc/behavior mismatch for
  operator judgement — NOT auto-changed because (a) it's a deliberate
  designed RM path, not a missing guard, and (b) "RM-aware reduced
  motion vs hard suppression" is a felt-quality call above Polish tier.
  Options: (1) leave as-is, update the doc comment to say "reduced to a
  single short beat + opacity cross-fade"; (2) make the RM branch set
  `rotated = true` with NO `withAnimation` (instant, pure cross-fade) to
  match the doc; (3) keep behavior, no change. Recommend (1) — the
  reduced beat is gentle and the haptic+final-state still land.

## Regressions caught

- Today screen (RM-on): pre-fix vs post-fix captures
  (`today-rm-on.png` vs `today-rm-on-after-fix.png`) are visually
  identical — mascot at rest, wake suppressed, layout intact. No
  regression. Intended change (haptic timing) is non-visual.
- `onboarding` scenario relaunch landed on the Today screen rather than
  the reveal cluster (persisted onboarded state; scenario knob did not
  reset a completed onboarding without a fresh install). The
  reveal-cluster verdicts (sites 13–20) therefore rest on source
  inspection of the inline `reduceMotion ? nil :` guards, which is the
  canonical verification for `.animation(value:)` modifiers. Noted as a
  fixture limitation, not a finding.

## A11y identifiers added

None (no AX-tree driving required this session; verification was
source-inventory + framebuffer capture).

## Vision updates

None. The wake haptic-survives-RM behavior is already ratcheted in
operator memory `feedback_life_clock_wake_animation.md`; this session
brought the code back into compliance with that ratchet.

## Next pass

- Operator decision on site 9 (ClockHandView RM doc/behavior mismatch) —
  see Outstanding.
- If a reveal-cluster *visual* RM capture is wanted, a fresh-install
  fixture (uninstall + install + `LIFECLOCK_UI_TEST_SCENARIO=onboarding`)
  is needed; this pass verified those sites by source.
