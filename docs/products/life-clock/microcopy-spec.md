# Microcopy Spec — Life Clock

> **Status:** Canonical product policy. Closes the floating-tone-pools gap surfaced by the 2026-05-12 premium-feel audit (2 `microcopy-flab` prompts). Tone-pool architecture is real and substantial — it lives across [`Sources/App/ToneMode.swift`](../../../products/life-clock-ios/Sources/App/ToneMode.swift), [`future-tab-tone-pools-spec.md`](future-tab-tone-pools-spec.md), [`quest-pool-vocab.md`](quest-pool-vocab.md), `polish-2026-05-*.md` log fragments — but no doc says *what makes a Life Clock copy line on-spec.* That's the gap this fills.

## One-line rule

**Every user-facing string must (a) be tone-aware via the existing `ToneMode` pools, (b) honor the safety register for its surface, and (c) refer to "time" — never points, scores, XP, or streaks.** Surfaces that need new copy add a `ToneMode` method; surfaces never inline a fourth voice.

## The three tones (binding — vision Decided 2026-05-04)

| Tone | Shipped enum | Register |
|---|---|---|
| **Gentle** | `gentle` | No death-date language. Future-self framing. "Steady progress." Default for users with high PSS-10 / UCLA-3 (Q9 inferred-softer rule). |
| **Coach** | `coach` | Default. Direct but supportive. "Today moved you forward by 18 minutes." Avoids harsh, but won't sugar-coat negative days either. |
| **Firm/Direct** | `firmDirect` | Opt-in dramatic register. Short, specific, no hedging. "Today: −22. Sleep was the lever." Carries the Brainrot reveal-escalator voice into daily use. |

The dropped `mementoMori` tone is gone — do not reintroduce. The previous "Earn time **back**" framing is also gone (vision Decided 2026-05-11). Use the forward-pull "Earn time" across all surfaces.

## Safety registers (binding — by surface)

Different surfaces enforce different safety floors regardless of the user's tone choice:

| Surface | Floor | Why |
|---|---|---|
| Notification copy (daily reminder) | **Gentle floor — no mortality lexicon, ever** | Lock-screen visibility. Vision Decided + `feedback_life_clock_notifications_constraints.md`. |
| WrapUp body (yesterday + weekly) | Tone-aware via `ToneMode.wrapUpPositiveBody / wrapUpNegativeBody / wrapUpZeroBody` | Reflective moment; primacy goes to ceremony, not framing |
| SafetyNet copy | **Gentle floor regardless of `store.toneMode`** | Refuge surface; firmDirect would be hostile to the anxious user it exists for. Implemented in `SafetyNetView`'s inline strings (do NOT wire through ToneMode keys for this surface). |
| Today drivers + Today's Plan | Tone-aware via `ToneMode.todayInterpretation` / `todayDriversHeading` | Daily-loop primary surface |
| History day-detail + override sheet | Tone-aware but quieter — uses `coach` register copy even when tone is `firmDirect` | Correction surface; needs neutral feel |
| Reveal escalator dramatic beats | `firmDirect` permitted; **softens automatically under Q9** | This is where dramatic framing lives, and only here |
| Paywall + Pro signal | Tone-aware via `weeklyWrapUpProSignal*` etc. — quotes the Free/Pro rule honestly | Value-claim accuracy is App Review territory |
| Microcopy on chips, badges, buttons | Tone-neutral OR tone-aware via dedicated keys (`wrapUpDismissCTA`, `adjustedChipLabel`) | Pick one and document |

## How a new copy line gets added

When a new surface needs user-facing copy, follow this order:

1. **Identify the safety register** for the surface (table above). If it's a floor surface, write Gentle-register inline.
2. **Check ToneMode for an existing key.** Repurpose if a close match exists.
3. **Add a new `ToneMode` method** if not. The method returns a `String` and switches over `self`; supplies one variant per tone. Naming convention: surface-noun + role (e.g., `wrapUpDismissCTA`, `todayInterpretation`, `weeklyWrapUpProSignalTitle`).
4. **Cross-reference the spec.** The new method's comment cites this file + the surface using it.
5. **No silent placeholders.** Every variant ships final-quality copy — don't ship `"TODO copy"` to land the structural change.

## The "earn time" rule (forward, not back)

Every copy site that frames the wedge uses the forward-looking "**earn time**" phrasing — never "earn time **back**." Marketing copy aligns with in-app voice (vision Decided 2026-05-11). The rule applies to:

- App Store subtitle, screenshots, description.
- Onboarding lead-in screens.
- Wedge mentions in any tone pool.
- Paywall pitch lines.
- All cross-doc references (founder pack docs were updated 2026-05-13).

## The "time, not points" rule

Life Clock's currency is **time**. Microcopy must never:

- Use "points," "coins," "XP," "score" (except `healthspanScore` which is an internal model name, never user-facing copy).
- Use "streak" — vision Decided 2026-05-06 dropped the concept; the equivalent surface is the monthly logging banner (calendar-month count).
- Use medal/badge/rank language (the badge surface in Profile uses a non-gamified "Completion badges" framing).
- Use "level up," "unlock," or other game-board metaphors when describing daily progress (the Pro feature list legitimately "unlocks" — that's a different domain).

## Anti-patterns (binding refusals)

- **Do not invent a fourth voice.** If a surface needs copy that doesn't fit gentle / coach / firmDirect, the *surface* is wrong, not the tone catalog.
- **Do not interpolate user variables into the dramatic register.** "Your sleep cost you 12 minutes" in firmDirect is on-spec; "Your sleep was BAD" with a value judgment is not. Drama is about being specific and direct, not about being mean.
- **Do not use "should" copy.** ("You should sleep more.") The app reflects, it doesn't prescribe. Replace with descriptive ("Sleep was the biggest drag today") + actionable ("Get 30 more minutes tonight to break even.").
- **Do not capitalize for emphasis** (`"YOU EARNED TIME"`). The numeric display does emphasis with size + weight; copy doesn't shout.
- **Do not use exclamation points** outside celebratory micro-moments (purchase success, badge unlock — and even then sparingly). The app's voice is calm, not enthusiastic.
- **Do not introduce time-back-recovery framing.** "Lost time" / "stolen time" / "buy back" are off-spec.
- **Do not use clinical jargon** in user-facing copy. The engine uses terms like `lifestyleAdjustmentYears`; user-facing surfaces translate to "habits that move your trajectory."
- **Do not use copy that depends on a screenshot** to make sense. Each line should read coherently from VoiceOver alone.

## Cross-references

- Tone pool source (binding implementation): [`Sources/App/ToneMode.swift`](../../../products/life-clock-ios/Sources/App/ToneMode.swift)
- Future-tab tone pools: [`future-tab-tone-pools-spec.md`](future-tab-tone-pools-spec.md)
- Quest-pool vocabulary: [`quest-pool-vocab.md`](quest-pool-vocab.md)
- Vision Decided constraints: [`vision.md`](vision.md) (tone modes 2026-05-04, "earn time" 2026-05-11, "monthly count, no streak" 2026-05-06)
- Premium-bar rubric: [`premium-bar.md`](premium-bar.md) § Microcopy
- Audit prompts: `premium-feel-backlog-2026-05-12-standard.md` Prompts 10, 11, 12, 14 (microcopy + tone-pool drift candidates)
- Reveal-escalator copy rule: [`reveal-escalator-spec.md`](reveal-escalator-spec.md) § "Mortality lexicon ban"
- Notification copy rule: [`TECHNICAL_ARCHITECTURE.md`](TECHNICAL_ARCHITECTURE.md) § Notifications constraints

## Validation

A copy line is on-spec when ALL of the following hold:

1. The line lives in `ToneMode.swift` (or is intentionally hard-coded in a Gentle-floor refuge surface — currently SafetyNet only).
2. The line's tone variants don't contradict the surface's safety floor.
3. The line uses "earn time" forward-pull, never "earn time back."
4. The line never references points / coins / XP / streaks / medals.
5. The line works under VoiceOver — no copy that requires visual context.
6. New `ToneMode` methods cite this spec + the surface in the doc comment.

When (1)–(6) hold across all shipped strings, the premium-readiness `microcopy-flab` count stays at zero.
