# Death Clock: The Life Lab — Premium Reference-Match

> **Skill:** none (premium-feel-audit follow-through; resolves [premium-feel-backlog-2026-05-13-standard.md § P7](premium-feel-backlog-2026-05-13-standard.md)).
> **Reference anchor:** [vision.md § References — Decided 2026-05-13](vision.md). Match the craft, reject the framing.
> **Source material:** [App Store listing](https://apps.apple.com/us/app/death-clock-the-life-lab/id6499554412) (id `6499554412`) — fetched via WebFetch 2026-05-13.
> **In-app comparison:** Life Clock at commit `79a10fe` (post-Sprint-D + smoke-test + Sprint-E close-out).
> **Capture method:** text-only (App Store description, pricing structure, subtitle, version notes). Visual frame-by-frame motion comparison deferred to operator (see § Limitations).
> **Author:** Claude (single-pass synthesis).

---

## Why this reference

Death Clock: The Life Lab is the operator-anchored premium-feel reference per `vision.md § References` (Decided 2026-05-13). It sits in the **same adjacent category** as Life Clock (longevity / countdown / Apple-Health-driven), occupies the App Store position Life Clock explicitly avoids (per [APP_STORE_ASO.md § Naming strategy](APP_STORE_ASO.md): "Avoid launching as 'Death Clock' because a direct competitor already uses that territory strongly"), and has shipped at a level of finish (4.8★ on 15K ratings) that makes it a craft benchmark.

The binding rule from `vision.md`:

> **"Match the craft, reject the framing."** Life Clock's vision Decided constraints (trajectory-not-prophecy, no AI concierge, no bloodwork, no mortality-heavy lexicon) supersede any reference pattern.

This document scores craft we may import and explicitly enumerates the framing we will NOT.

## Reference material captured

From the App Store listing (verbatim from `WebFetch 2026-05-13`):

- **Subtitle:** "Improve your health with AI"
- **Description lead:** "Powered by advanced AI and grounded in medical science, Death Clock reveals not just when you might die—but how to live better, longer. The Life Lab turns your health data into a personalized plan for longevity."
- **Feature claims (excerpts):**
  - "AI-driven longevity model, built from CDC data, global mortality research"
  - "Comprehensive blood testing" included with subscription
  - "Evidence-backed recommendations for diet, exercise, supplements, and screenings"
  - "24/7 AI health concierge interprets lab results"
  - "Sync your Apple Health data, or activity metrics from wearables"
  - "Your data is fully encrypted and never sold"
- **Pricing tier landscape (raw — many SKUs):**
  - Death Clock Membership: $39.99, $59.99, $79.99, $99.99
  - Death Clock AI Membership: $9.99, $39.99, $69.99
  - Death Clock Digital Membership: $69.99
  - "$49/yr Digital Only": $49.99
  - "$99 Baseline, 3-Day Trial": $99.99
- **Reception:** 4.8 stars / 15,000 ratings
- **Latest update:** Version 4.0.13, "Stability improvements and bug fixes," 6 days ago

## Scoring matrix (3 axes)

| Axis | Death Clock | Life Clock (current) | Gap & importable craft | What we WILL NOT import |
|---|---|---|---|---|
| **Number-animation craft (countdown / headline)** | Inferred — App Store name + subtitle ("Improve your health with AI" + the "countdown" framing across the App Store strip) point at a continuously-ticking death-date countdown as the headline UI element. 4.8★ reception suggests this lands as polished, not gimmicky. | Today screen renders signed-minute delta ("+1h 8m" hero) in Display numeric (44pt rounded semibold) + wake animation 1.0s with the operator-pinned envelope. Quest-completion payoff Decided 2026-05-13 layered A (mascot pulse) + B (clock-hand advance via `displayedDelta`) + C (tone-aware micro-copy). Plays on every app open per `feedback_life_clock_wake_animation.md`. | Death Clock's headline is a **continuously updating** number; Life Clock's headline updates per cold-launch/foreground + on quest completion. Ratchet candidate: consider whether the trajectory peek on Today (projected healthspan year-count) should tick *visually* during ceremonial moments rather than just snap to value. NOT a continuous death-second counter — that would import the prophecy framing. | A literal countdown to a death date. Any continuously-decreasing clock toward zero. Vision Decided 2026-05-04 ("Trajectory, not prophecy") is binding. |
| **Reveal pacing & ceremony** | Inferred from the App Store positioning of "reveal not just when you might die—but how to live better, longer." The category convention — supported by the App Store preview-strip pattern across this app and "Life Countdown: Death Clock" et al. (per search results) — is a dramatic single-headline reveal with the date as the punch. | Onboarding `RevealEscalatorScreens` (5-screen sequence: AnalyzingView → ArchetypeRevealView → LifeGridRemainingView → BigNumberPenaltyView → RecoveryPreviewView) is the closest ceremonial-reveal moment, plus the WrapUp ceremony (Sprint D2 full lighting on the clock face, weekly 2.2s + yesterday 1.4s animationDuration). | Death Clock's single-shot reveal is structurally simpler than Life Clock's 5-screen escalator. Possible ratchet: review whether the escalator's 5-beat structure earns each beat or whether a tighter 3-beat (Analyzing → BigNumber → RecoveryPreview) would land harder. Currently held by vision Decided 2026-05-12 (softens only on PSS + UCLA threshold) — any structural tightening is a vision-question, not a polish move. | A reveal that ENDS on death-date prediction. Life Clock's reveal ends on Recovery — that's the deliberate inversion of the genre. The escalator's "lives back" framing (per Sprint D series) is the rejection of Death Clock's "time gone" framing. |
| **Transition feel between major moments** | App Store preview-strip evidence (limited via text-only fetch) suggests a fairly linear flow: onboarding → reveal → daily check-in → buy. Pricing tier complexity (8 SKUs across membership tiers) suggests a paywall that's prominent post-reveal. | Onboarding terminal paywall (`PaywallPrimaryView`) is the post-reveal paywall slot, currently using 3-tier StoreKit catalog ($7.99/$49.99/$129.99) per [MONETIZATION.md § As shipped](MONETIZATION.md). PaywallSheet (re-engagement) renders 5 verbatim bullets via `ProPerks` (Sprint A2 + Sprint E close-out). Transitions: `Motion.Duration.{instant,beat,breath}` enum landed Sprint A; reveal-to-paywall transition is direct (no intermediate "summary" screen). | Death Clock's 8-SKU complexity is **NOT** a ratchet candidate — it's pricing fragmentation that Apple's 3.1.2(c) equal-prominence guidance disfavors. Life Clock's 3-tier ladder is the right number. Importable: the conviction with which Death Clock commits to the post-reveal paywall as a single dramatic moment. Life Clock's `PaywallPrimaryView` is already dramatic (`"Earn time, every day."` headline); ratchet candidate is whether the reveal-to-paywall *transition* (currently a screen swap) deserves the same `.breath`-tier crossfade ceremony as the WrapUp reveal. | Death Clock's SKU ladder. The "3-Day Trial" framing on the $99 tier (Life Clock vision: no trial in v1 per [MONETIZATION.md § Trial stance](MONETIZATION.md)). Any version of bundle-with-bloodwork pricing. |

## Concrete ratchet recommendations

Three changes worth scoping. None requires source change in *this* prompt — all feed into specific simulator-driven-polish sessions or vision-question raises.

### 1. Reveal-to-paywall transition ceremony (Polish-tier, post-Sprint-E)

The reveal escalator's final screen (`RecoveryPreviewView`) currently transitions to the terminal paywall via standard NavigationStack push. Death Clock's similar slot (post-reveal → paywall) reads (per App Store positioning) as ONE continuous dramatic beat. Life Clock could ratchet by:

- Crossfading `RecoveryPreviewView` → `PaywallPrimaryView` over `Motion.Duration.breath` (500ms) with the mascot scale staying stable across the transition (anchor across screens) rather than blinking.
- Verifying with the operator that the resulting "single dramatic moment" feel doesn't break the Reduce-Motion path (it shouldn't — both screens have RM fallbacks already).

This is a 30-line diff in `OnboardingCoordinator.swift` and a polish session log. Operator approval gate: yes, because changing onboarding flow is high-leverage.

### 2. Trajectory-peek ticking on Today (Stretch-tier, vision-adjacent)

Today's projected-healthspan card renders a static "Projected healthspan: 82.9 years" string. Death Clock's analogous element (per App Store positioning) is a continuously-ticking countdown that earns its drama by being *alive*. Life Clock can ratchet by introducing a brief tick-up animation on the year-count when the value changes (e.g., after a logged habit, after a quest completion) — bringing the existing quest-completion Option-B `displayedDelta` choreography to the trajectory peek.

Constraints:

- Must respect Decided 2026-05-04 "Confidence is shipped, not hidden" — the tick shouldn't invent precision the engine doesn't have. The animation reveals the existing confidence-band value, not a more-precise number.
- Must respect operator memory `feedback_life_clock_wake_animation.md` — no second wake-style animation that could read as competing for attention with the daily wake. The trajectory tick is a *response* to user action (quest tap), not an opening greeting.
- Must NOT introduce a continuous-counting visual. Drama-not-cruelty + trajectory-not-prophecy together rule out a real-time death-second counter.

Scope: 50-line diff in TodayView + a new Motion choreography helper. Operator gate: yes (Feature-adjacent — touches the ceremonial daily moment).

### 3. Recovery preview density on `RecoveryPreviewView` (Polish-tier)

Death Clock's "evidence-backed recommendations for diet, exercise, supplements, and screenings" descriptor implies the post-reveal screen is dense with specific recommendations. Life Clock's `RecoveryPreviewView` (per Decided 2026-05-12 architecture) frames recovery in motivational copy but the specific drivers / specific actions for that user are reserved for the daily loop. **Hold the line.** This is NOT a ratchet candidate — it's an example of where Death Clock's framing wins more density for less behavior change, and the Life Clock vision is right to keep recovery framing *promise-of-the-loop* rather than *here's-your-supplement-stack*.

Logged here as a deliberate non-import.

## What we are NOT importing

Binding reject-list (each maps to a `vision.md` Decided constraint):

1. **AI-driven prediction framing.** "Death Clock reveals... when you might die" — rejected by vision Decided 2026-05-04 "Trajectory, not prophecy." Life Clock's clock is a trajectory mirror, not a prediction oracle. Any UI that asserts a specific date or specific years-remaining is forbidden.
2. **AI health concierge.** "24/7 AI health concierge interprets lab results" — rejected by vision Decided 2026-05-04 ("No AI health concierge in v1"). v1 ships zero AI-chat / AI-interpretation surfaces.
3. **Bloodwork interpretation.** "Comprehensive blood testing" — rejected by vision Decided 2026-05-04 ("No bloodwork interpretation in v1"). Calorie tracking and photo meals are out of scope until the daily loop has proven retention.
4. **Mortality-heavy lexicon.** Death Clock's name and subtitle lean into the "die" / "death" / "mortality" register. Rejected by [vision.md § Tone](vision.md) ("Drama is allowed; cruelty is not") + Decided 2026-05-09 ("Lock-Screen copy follows in-app tone; mortality lexicon is the only contextual override"). The `NotificationsServiceTests.testNoMortalityLexiconInAnyToneCopy` test guards this in code.
5. **8-SKU pricing ladder.** Rejected by vision Decided 2026-05-04 ("Annual-first pricing") + `MONETIZATION.md § As shipped` (3-tier: monthly / annual / lifetime). Apple 3.1.2(c) equal-prominence guidance also disfavors high-SKU paywalls.
6. **3-Day Trial framing on a high-priced tier.** Rejected by `MONETIZATION.md § Trial stance` — v1 ships without an introductory trial because any trial language must be backed by an App Store Connect provisioned offer.
7. **Continuous death-date countdown.** Inferred genre convention. Rejected by Decided 2026-05-04 ("Trajectory, not prophecy") and Decided 2026-05-04 ("Currency is time, not points or XP" — time-as-currency framing forward-pulls; a countdown framing backward-loses).
8. **Dramatic single-headline reveal that ends on mortality.** Rejected. Life Clock's escalator deliberately inverts the genre: the punchline is the RecoveryPreviewView, not the BigNumberPenaltyView.

## Limitations of this audit

- **Text-only capture.** Visual side-by-side frame captures of the actual reveal sequences would be a stronger comparison. Recommended operator follow-up: install Death Clock from the App Store, capture the reveal sequence and the daily-headline tick on screen (10-second video each); compare against Life Clock's RevealEscalator + Today wake using the same recording duration.
- **Motion specifics inferred.** Animation curves, duration tiers, and lighting conventions used by Death Clock are not extractable from text — direct app installation needed.
- **Pricing UX inferred from SKU list.** Whether Death Clock's 8 SKUs are presented as a flat list, a tier-card grid, or a comparison table is not visible from the App Store listing description alone.

These limitations don't invalidate the framing-reject guardrails (§ "What we are NOT importing") — those are derived from Decided constraints in `vision.md` and are binding regardless of capture fidelity. The 3 ratchet recommendations also stand because each is grounded in a current Life Clock implementation observation, not in Death Clock specifics.

## Cross-references

- [premium-feel-backlog-2026-05-13-standard.md § P7](premium-feel-backlog-2026-05-13-standard.md) — the audit prompt
- [premium-bar.md § Motion + § Surface-level rubric](premium-bar.md) — the rubric
- [vision.md § References — Decided 2026-05-13](vision.md) — the binding reference anchor + reject rule
- [vision.md § Decided constraints](vision.md) — the framing-rejection backstops (Trajectory-not-prophecy / No AI concierge / No bloodwork / Drama-not-cruelty / Mortality-lexicon-only-as-contextual-override)
- [reference-apps.md](reference-apps.md) — operator-side reference doc
- [APP_STORE_ASO.md § Naming strategy](APP_STORE_ASO.md) — "Avoid launching as 'Death Clock'"
- [MONETIZATION.md § Trial stance](MONETIZATION.md) — no-trial v1 rationale
- Source: [Death Clock: The Life Lab on the App Store](https://apps.apple.com/us/app/death-clock-the-life-lab/id6499554412)
