# SafetyNet Spec — Life Clock

> **Status:** Canonical product policy. SafetyNet is the emotional-safety refuge surface — the in-app affordance for users who find Life Clock's mortality framing distressing. It is load-bearing for App Review (medical/treatment + mental-health adjacency) and for trust ([`pro-value-rule.md`](pro-value-rule.md) § Trust). Implementation: [`Sources/Features/SafetyNet/SafetyNetView.swift`](../../../products/life-clock-ios/Sources/Features/SafetyNet/SafetyNetView.swift), reachable from [`ProfileView.swift`](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift) § SafetyNet entry.

## One-line rule

**SafetyNet is always one tap from Profile. It is tone-neutral (Gentle floor) regardless of the user's tone choice. It offers three concrete affordances: switch to Gentle tone, hide the clock, and surface crisis-resource phone numbers. It never gates, never paywalls, never asks why.**

## The three affordances

| Affordance | What it does | Persistence |
|---|---|---|
| **Switch to Gentle tone** | Sets `store.toneMode = .gentle` from anywhere in the app | Persists via `UserProfile.toneMode` SwiftData write |
| **Hide the clock** | Toggles `UserProfile.hideClock`; Today renders the healthspan-score-only variant; History/Future demote the dramatic readout to a quieter form | Persists; user can un-hide via the same toggle in SafetyNet (or Profile if exposed there in the future) |
| **Crisis resources** | Surfaces 988 Suicide and Crisis Lifeline (US) + Crisis Text Line phone numbers as one-tap dial / message links | No persistence — each tap goes through iOS's native phone / messages handoff |

The user gets to all three without leaving SafetyNet. Each is independent — toggling one doesn't toggle the others.

## Entry point (binding)

The only canonical entry is **Profile → "If this app is making you anxious"** (`profile.safetyNet.entry`). The label is intentional:

- Not "Help." (Vague.)
- Not "Crisis." (Stigmatizing.)
- Not "Wellbeing." (Corporate-soft, reads as marketing.)
- "If this app is making you anxious." (Honest, names the cause the user actually has, no judgment.)

The footer subtitle reads: *"Switch to Gentle tone, hide the clock, or get crisis-resource phone numbers. Always available — no questions asked."*

Implementation: `ProfileView.swift` § SafetyNet section + `.sheet(isPresented: $safetyNetPresented) { SafetyNetView() }`.

A `LifeClockLaunchConfiguration.forceSafetyNet` env flag exists for UITest coverage — it auto-presents SafetyNet on Profile mount. Don't repurpose this flag for non-test routing.

## Copy register (binding — Gentle floor regardless of user tone)

SafetyNet copy is **tone-neutral, leans Gentle-register, and is hard-coded inline in `SafetyNetView.swift`** — *not* threaded through `ToneMode`. The reasoning is in the source comment + `microcopy-spec.md` § Safety registers:

- A firmDirect-tone refuge would be hostile to the anxious user the surface exists for.
- A coach-tone refuge would still carry accountability language.

This is an explicit, documented exception to the "all copy via ToneMode" rule from [`microcopy-spec.md`](microcopy-spec.md). Do not refactor SafetyNet copy into ToneMode keys.

## What SafetyNet must never do

- **Never gate.** Free or Pro, every user has access to every SafetyNet affordance.
- **Never paywall.** No upsell anywhere in the surface. Even tone-mode switching from firmDirect → Gentle is free of friction.
- **Never ask why.** No "what's making you anxious?" picker. No journal prompt. No data collection. The user is in SafetyNet because something already triggered them; the surface offers exits, not investigation.
- **Never delay.** No fade-in animation that gates interaction. No "preparing your safety net…" load state. The sheet renders instantly with all three affordances visible.
- **Never claim therapeutic value.** SafetyNet is a *refuge*, not a *treatment*. The crisis-resource phone numbers route to professional services; the in-app affordances are environmental (tone + visibility), not clinical.
- **Never link to off-device content** other than the crisis hotlines. No "10 ways to feel better" blog posts, no "talk to a therapist" matching service.
- **Never bury behind a confirmation.** "Are you sure you want to hide the clock?" — no. One tap.
- **Never re-enable hidden clock automatically.** If the user hid it, only the user un-hides it.

## App Review posture

SafetyNet is the affirmative answer to two App Review concerns:

1. **Medical/Treatment information frequency** (ASC age-rating questionnaire). The app's mortality framing reads as "infrequent" medical/treatment content because SafetyNet's one-tap refuge plus the once-per-onboarding `bigNumberPenalty` reveal bracket the dramatic register on both ends. See [`ASC_CHECKLIST.md`](ASC_CHECKLIST.md) Phase 4 row "Medical/Treatment Information."
2. **Manipulative-fear paywall concern** (§ 5.6.3). Life Clock cannot be read as fear-based monetization because (a) the dramatic register is opt-in via tone-mode, (b) Gentle hides the clock, (c) SafetyNet is one tap to gentler framing, (d) the paywall is reachable but the app is fully usable Free, (e) no notification copy carries the mortality lexicon.

The App Review notes in `ASC_CHECKLIST.md` Phase 7 explicitly cite SafetyNet for the reviewer.

## Hide-the-clock surface coverage

When `UserProfile.hideClock == true`:

- **Today**: the headline signed-minutes (`.system(size: 44)`) is suppressed; the mascot + healthspan score remain. "Today's Plan" + drivers + check-in still render — clock-free framing.
- **History**: per-day signed-minutes are replaced by qualitative "Strong day / Steady day / Heavy day" labels mapping to delta brackets. Day-detail still surfaces the underlying signals; just no numeric mortality readout.
- **Future tab**: trajectory chart hides the years-projection line; the What-If Simulator (Pro) still works but operates on a relative-only "more / less" axis.
- **WrapUp**: ceremony still fires, but the signed-minutes readout suppresses. The ClockHandView's rotation still plays (it's tactile, not numeric); the visible label is qualitative ("Yesterday: a strong day").
- **Notifications**: notification copy was already Gentle-floor (no mortality lexicon); no further change required.
- **Paywall**: header copy stays as-is (paywall is opt-in; user landed there knowing what Pro is).

If a future surface introduces a numeric mortality readout, that surface MUST consult `hideClock` and provide a qualitative fallback. Audit reviewers will look for this.

## Anti-patterns (binding refusals)

- **Do not let `hideClock` decay** silently. There is no expiry; the toggle persists until the user toggles it off.
- **Do not surface SafetyNet in a re-engagement push.** Notifications never carry SafetyNet-related copy. The user comes to SafetyNet voluntarily.
- **Do not promote Pro inside SafetyNet.** Even oblique upsell ("Pro tone modes feel softer") is wrong.
- **Do not collect telemetry on which SafetyNet affordance the user picked.** `screenAppeared("safetyNet")` is fine (presence-only). Internal state changes are private.
- **Do not allow tone-mode regression below Gentle.** Gentle is the floor for SafetyNet's switch; a future "Even gentler" mode would be a vision-question, not a UI change.

## Outstanding (vision Q13)

`vision.md` Open Question #13 ("self-harm-adjacent language / anxious users") is operationally closed by SafetyNet but not enumerated as a Decided constraint. When the operator next ratchets vision, lock SafetyNet's existence + the three affordances + the Gentle-floor copy rule into Decided constraints.

## Cross-references

- Source: [`Sources/Features/SafetyNet/SafetyNetView.swift`](../../../products/life-clock-ios/Sources/Features/SafetyNet/SafetyNetView.swift)
- Entry point: [`ProfileView.swift`](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift) § SafetyNet section
- Tone-mode switch: `Sources/App/ToneMode.swift`
- Hide-clock field: `UserProfile.hideClock` in `Sources/Models/LifeClockSchema.swift`
- App Review: [`ASC_CHECKLIST.md`](ASC_CHECKLIST.md) Phase 4 + Phase 7
- Microcopy exception: [`microcopy-spec.md`](microcopy-spec.md) § Safety registers
- Vision open question: [`vision.md`](vision.md) § Open questions Q13
- Premium-bar emotional-safety category: [`premium-bar.md`](premium-bar.md) § "Microcopy" + § "Anti-signals"

## Validation

The SafetyNet surface is on-spec when ALL of the following hold:

1. The Profile entry point is exactly one tap from Profile root.
2. The sheet renders instantly with all three affordances visible (no progressive disclosure).
3. Copy is inline-Gentle, not ToneMode-keyed.
4. No paywall, no gate, no telemetry on affordance choice.
5. Crisis-resource taps route through iOS native phone/messages (no in-app intermediary).
6. `hideClock == true` propagates to every surface listed under "Hide-the-clock surface coverage" — no regression to dramatic readouts.
7. The 988 + Crisis Text Line numbers are current US numbers (verify before each App Review submission; expand to regional equivalents when international release is on the roadmap).
8. The `forceSafetyNet` env flag exists for UITest coverage and is not consulted by any production code path.

When (1)–(8) hold, SafetyNet meets the emotional-safety + trust precondition for both the premium-feel and pro-value readiness flags, and the App Review § 5.6.3 manipulative-fear-paywall concern has a documented affirmative answer.
