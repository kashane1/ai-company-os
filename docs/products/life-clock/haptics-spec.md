# Life Clock Haptics Spec

Status: draft for operator approval. Produced by a `simulator-driven-polish`
vision-question pass on 2026-05-09. No app code changes are authorized by this
document until the operator chooses the policy.

## Audit summary

This pass did not run on-device. Haptics are not visible in Simulator, so the
audit used source inspection for SwiftUI sensory feedback and UIKit feedback
generators.

Search terms:

- `UIImpactFeedbackGenerator`
- `UINotificationFeedbackGenerator`
- `UISelectionFeedbackGenerator`
- `sensoryFeedback`
- `impactOccurred`
- `notificationOccurred`
- `selectionChanged`
- `haptic`

Current implementation:

| Surface | Current coverage | Evidence | Audit note |
|---|---:|---|---|
| Morning Wake | None | `TodayView.triggerWakeIfPossible()` drives `wakeProgress` + `mascotWakeTrigger`, but no sensory feedback. | The visual greeting is present; touch feedback is undecided. |
| Quest completion | Success | `TodayView` increments `questCompletionHapticTrigger` on overlay increase and attaches `.sensoryFeedback(.success, trigger:)` to the mascot. | Best-covered path. It deliberately still fires under Reduce Motion and suppresses uncheck celebration. |
| Clock-hand advancing on first reveal | None | `EngineRevealAndDialView.runRevealPulse()` changes `mascotOverride.minutes`; no sensory feedback. | This is the first true engine reveal, so silence is a meaningful choice. |
| WrapUp positive vs negative delta | Generic selection | `ClockHandView` attaches `.sensoryFeedback(.selection, trigger: rotated)` regardless of positive, negative, zero, yesterday, or weekly. | Existing feedback says "the animation started," not "this was good/bad/neutral." |
| Monthly milestone banner crossing | None | `TodayView.monthlyLoggingBanner` renders milestone copy from `MonthlyLogging.milestone`; no sensory feedback. | The banner is a reward surface but currently quiet. |
| Paywall purchase success | None | `PaywallSheet` and `PaywallPrimaryView` dismiss when `subscriptions.isPro` flips; `SubscriptionStore.purchase` grants entitlement on verified transaction. | Purchase success is externally high-signal and should not feel like a silent disappearance. |
| Negative / bad-day surfaces | None beyond generic WrapUp selection | Today negative copy, rescue line, and negative WrapUp body have no dedicated warning or impact haptic. | Vision has no decided constraint here; this is the key open question. |

## Product principles

Haptics should make Life Clock feel responsive, not punitive. They should mark
moments of agency: reveal, completion, confirmation, and meaningful progress.
They should not make a bad day feel like punishment.

Tone caps:

| Tone mode | Maximum routine intensity | Allowed exception |
|---|---|---|
| Gentle | `light`, `selection`, `success` | No `medium`, `heavy`, or `warning` unless tied to purchase success from StoreKit. |
| Coach | `light`, `medium`, `selection`, `success` | `warning` only for confirmed negative summaries, never on every bad-day screen render. |
| Firm/Direct | `light`, `medium`, `selection`, `success`, restrained `warning` | `heavy` should remain out of v1 unless the operator explicitly wants mortality-grade drama. |

Accessibility:

- Haptics are independent from Reduce Motion. Suppressing animation should not
  automatically suppress haptics.
- Add an in-app haptics toggle only if user feedback shows sensitivity; do not
  create settings complexity preemptively.
- Prefer SwiftUI `.sensoryFeedback` where available for local view triggers.
  Use UIKit generators only if a path cannot be expressed cleanly in SwiftUI.

## Surface recommendations

### 1. Morning Wake

Recommendation: `light` impact at the start of a successful wake animation.

Rationale: This is a greeting, not a score reveal. It should feel like the app
has woken with the user. Gentle stays `light`; Coach stays `light`; Firm/Direct
may use `medium` only if the operator wants Today to feel more physical.

Trigger: when `triggerWakeIfPossible()` starts from settled state and
`store.todayEstimate != nil`.

Do not fire when:

- Reduce Motion bypasses the wake animation.
- Running under UI test.
- Returning to Today by tab switch inside the same active session.

### 2. Quest Completion

Recommendation: keep `.success`.

Rationale: The current implementation matches the vision question #14 direction:
completion feels positive, haptic feedback survives Reduce Motion, and unchecking
is silent. This is the strongest existing behavior.

Optional refinement after approval: if quest completion later splits into
"tap acknowledged" and "time landed," use `selection` on the row tap and
`success` when the mascot/count-up lands. Do not double-fire until the animation
timing is finalized.

Tone interaction: same for all tones. Completion is agency, not judgment.

### 3. Clock-Hand Advancing On First Reveal

Recommendation: `light` impact when the first reveal pulse starts, then no
second haptic during the automatic settle.

Rationale: The first reveal should land. A single light impact gives the moment
a physical beat without turning onboarding into a scare beat.

Firm/Direct option: `medium` can be justified only if the operator wants the
first reveal to be more dramatic. Gentle should remain `light`.

Do not use `warning` here. The reveal is foundational product identity, not an
error state.

### 4. WrapUp Positive Vs Negative Delta

Recommendation:

- Positive delta: `success`.
- Zero delta: `selection`.
- Negative delta: pending operator decision.

Rationale: Positive WrapUp is earned time and deserves a clean success. Zero is
informational. Negative is emotionally delicate because WrapUp is a retrospective
summary shown on launch.

Recommended negative default: `light` impact, not `warning`.

Alternative negative policy: `warning` only for Coach/Firm-Direct when the delta
crosses a material threshold, such as at least 60 minutes negative for yesterday
or at least 180 minutes negative for weekly. Gentle remains `light`.

Avoid `heavy`. It reads as punishment.

### 5. Monthly Milestone Banner Crossing

Recommendation: `success` on milestone days only; otherwise silent.

Rationale: The monthly banner replaced brittle streaks. Milestones are a kind
reward, and success feedback reinforces "you are building a month" without
punishing missed days.

Trigger: first Today render in a session where `monthly.milestone != nil` and
`monthly.daysLogged >= 1`.

Do not fire:

- On every app foreground while the same milestone is still visible.
- On non-milestone monthly banner displays.
- When the banner appears solely because old seeded data loaded in UI tests.

Tone interaction: same for all tones, but if Gentle feels too celebratory in
testing, downgrade Gentle to `light`.

### 6. Paywall Purchase Success

Recommendation: `success`.

Rationale: Purchase success is a system-level confirmation. The user has just
completed a high-intent action involving money; a success haptic reduces the
"did it work?" ambiguity before the sheet disappears.

Trigger: first transition from not Pro to Pro caused by a verified purchase or
restore path inside an active paywall surface.

Do not fire:

- On Debug simulator auto-entitlement at launch.
- On entitlement refresh that happens before the paywall is visible.
- On product selection row changes. Selection rows can use `selection` later,
  but that is polish, not part of this spec.

Tone interaction: same for all tones. This is commerce confirmation, not product
voice.

### 7. Negative / Bad-Day Surfaces

Recommendation: bad-day surfaces should be silent by default, except for a
single `light` impact when a negative WrapUp animation begins.

Rationale: The vision says "Drama is allowed; cruelty is not" and every negative
delta must be paired with an actionable next step. A haptic on every bad-day
Today render risks making the app feel like it is physically scolding the user.
Silence lets the copy and rescue line do the emotional work. WrapUp is the one
place where a single tactile beat can say "pay attention" without piling on.

Firm/Direct option: allow `warning` for material negative WrapUps only, never
for Today bad-day render, rescue line, or negative driver rows.

Gentle cap: no `warning`; max `light`.

## Proposed open question for vision.md

Do not append this automatically without operator approval:

> **Haptics intensity on negative surfaces.** Should bad-day surfaces remain
> silent by default, with only a single light impact for negative WrapUps, or
> should Coach/Firm-Direct use a warning haptic for materially negative summaries?
> Recommended policy: silent Today/rescue/driver rows; negative WrapUp gets
> light in all tones, with an optional warning threshold only for Coach and
> Firm/Direct.

## Approval checklist

- [ ] Approve Morning Wake as `light`.
- [ ] Keep quest completion as `success`.
- [ ] Approve first reveal as `light`, or upgrade Firm/Direct to `medium`.
- [ ] Choose negative WrapUp policy: `light` for all tones, or thresholded
      `warning` for Coach/Firm-Direct.
- [ ] Approve monthly milestones as `success` only on milestone days.
- [ ] Approve paywall purchase success as `success`.
- [ ] Approve bad-day Today/rescue/driver surfaces as silent.
