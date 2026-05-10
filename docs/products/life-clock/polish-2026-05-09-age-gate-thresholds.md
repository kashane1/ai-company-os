# Polish Session — life-clock — 2026-05-09 — age-gate-thresholds

## Mode

`fix-list`. Operator's idea: AgeGateTests.swift exists, which means there's an age-gate surface, but the operator doesn't know what it does or where it presents. App Store concern: the under-13 (and arguably under-18) flow has to be honest, not just a checkbox. Walk every threshold; Polish-tier fix any inconsistent copy; queue Vision-questions for any gaps that intersect privacy compliance ([PRIVACY_COMPLIANCE.md](PRIVACY_COMPLIANCE.md)).

Iteration cap: 8 (used 1). Final-check: yes.

Seed: none required — audit was code-and-routing first; visual checkpoint via fresh-install launch on iPhone 17 (1A88AF54).

## Surface map (what the gate currently is)

`AgeGate.isAdult(birthDate:asOf:calendar:)` — pure function in [Sources/Engines/AgeGate.swift](../../../products/life-clock-ios/Sources/Engines/AgeGate.swift). Returns `true` iff the reported age is ≥ 18. There is no other age check anywhere in the product.

Three call sites BEFORE this session:

1. [LifeClockStore.swift:101](../../../products/life-clock-ios/Sources/App/LifeClockStore.swift) — `var isAdultUser: Bool` reads the persisted profile's `birthDate`.
2. [QuickLogSheet.swift:67](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift) and [:143](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift) — hides the alcohol level + smoking/vaping daily-check-in pickers for minors.
3. [OnboardingCoordinator.swift:240](../../../products/life-clock-ios/Sources/Features/Onboarding/OnboardingCoordinator.swift) (private `isAdultBirthDate`) — suppresses the `bigNumberPenalty` reveal screen for minors.

Four new call site after this session — see Iterations.

### (a) Where the age gate presents in onboarding

DOB is collected at `BaselineDOBView` ([DataCollectionScreens.swift:183](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/DataCollectionScreens.swift)), the **5th** screen in the flow:

```
coldOpen → welcome → meetYourClock → reactiveSlider → goalPick
        → BASELINE-DOB ← (here)
        → baselineSex → bodyComp → smoking → alcohol → strength
        → cardio → sleep → diet
        → sensitiveConsent (skip-able) → familyMother → familyFather → stress → social
        → tone → priorAttempts
        → analyzing → archetypeReveal → lifeGridRemaining → bigNumberPenalty
        → engineRevealAndDial → recoveryPreview
        → healthKitAuth → paywallPrimary
```

It is **pre-HealthKit** and **pre-paywall**. It is **post-goal-pick**, so the user has already self-selected one of `liveLonger`, `moreEnergy`, `beThereForFamily`, `beatFamilyHistory`, `justCurious` before declaring their age — the goal copy is age-blind.

**The picker is `DatePicker(... in: ...Date(), ...)` — `.wheel` style, no minimum.** A user can pick today's date. There is no upper bound on age either (a 2026-05-09 picker resolution allows centuries-old DOBs).

### (b) <13 / <16 / <18 branch behavior (BEFORE this session)

| Threshold | What changes? |
|---|---|
| < 13 | **Nothing.** No COPPA gate, no parental-consent gate, no warning, no rejection. Flow proceeds identically to an adult except for the < 18 branches below. |
| < 16 | **Nothing.** No GDPR-Article-8 (16-year EU age-of-digital-consent) gate. |
| < 18 | `bigNumberPenalty` mortality-framing reveal screen is suppressed (skipped to `engineRevealAndDial`). In QuickLog (post-onboarding daily check-in), alcohol level + smoking/vaping pickers are hidden. **In onboarding itself, smoking + alcohol screens are still shown.** This was the load-bearing inconsistency this session fixed — see Iterations. |

### (c) Tone auto-shift

**No.** `firmDirect` is selectable by anyone. The `ToneView` ([DataCollectionScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/DataCollectionScreens.swift)) presents three buttons (`gentle | coach | firmDirect`) with no age-aware filter or default-shift. A 12-year-old who reports DOB 2014 can pick firmDirect and receive copy like "Today's reckoning" / "On the clock" / "What moved the needle".

### (d) Death-date language softening

The literal word "death" appears nowhere in user-facing strings. But the death-adjacent vocabulary persists irrespective of reported age:

- `LifeGridRemainingView` — "This is what's still ahead. / Each dot is a week your habits get to shape." (every user)
- `RecoveryPreviewView` — "{N} more years" / "of living, loving, exploring" (every user, modulated by goal not age)
- `EngineRevealAndDialView` — `projectedAgeYears` — anchor dial that sets a personal lifespan adjustment (every user)
- `BigNumberPenaltyView` — "~{N} years on the table." — explicitly suppressed for minors via `shouldShowPenaltyScreen()`

Vision §"Tone" already specifies: *"Gentle — healthspan score, time earned, future-self framing. **No death-date language**."* This applies to the tone surface, not the age surface. There is no rule that minors get the gentle-tone reveal even if they pick another tone.

### (e) Paywall + parental consent

`PaywallPrimaryView` ([Screens/PaywallPrimaryView.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift)) presents three tiers (`annual | monthly | lifetime`) at the end of onboarding. **No parental-consent gate** at any threshold. A 12-year-old who reaches this screen sees the same Continue / Restore / per-tier buttons. The real gate is iOS Family Sharing's "Ask to Buy" (set up at the Apple-ID level by the parent), not anything in our code.

## Iterations

| Time | Commit | Type | Tier | Surface | Result |
|---|---|---|---|---|---|
| 18:51 | `35fdd54` | fix | Polish | Onboarding routing + AgeGate tests | Minors skip smoking + alcohol onboarding screens; 5 new tests pin the routing decision. |

### `35fdd54` — fix(life-clock): skip smoking + alcohol screens in onboarding for minors

**What changed:**
- New `OnboardingScreen.afterBodyComp(birthDate:asOf:calendar:)` — single source of truth for the bodyComp-Continue branch. Adult → `.smoking`. Minor (or `nil` DOB) → `.strength`.
- `OnboardingCoordinator` consults the new helper from `BodyCompView`'s `onContinue` (replacing the unconditional `.smoking` jump).
- `AgeGate` docstring updated to enumerate all four call sites (was three).
- `AgeGateTests` gains 5 cases: adult-goes-to-smoking, exactly-18-goes-to-smoking, 17-skips-to-strength, 12-skips-to-strength, nil-DOB-skips-to-strength. All 10 tests in the suite pass.

**Why:**
The pre-fix flow contradicted the explicit ASC age-rating questionnaire claim ([ASC_CHECKLIST.md:54](ASC_CHECKLIST.md)): *"Alcohol, Tobacco, or Drug Use or References — Infrequent/Mild (user self-reports; under-18 users don't see these prompts)."* QuickLog hid the prompts. Onboarding did not. A submission reviewer who tapped through onboarding with a 14-year-old DOB would have found the alcohol screen and the questionnaire claim would not have held up. This is one of the cleanest possible Polish-tier fixes — pure consistency, no policy change, no copy invented.

The `nil` branch falls through as "skip" deliberately. The picker should always populate `birthDate` before this transition runs, but if it ever doesn't (state corruption, a future jump-fixture), the safer default for unknown age is to suppress alcohol/tobacco — same direction the rest of the gate leans.

## Stretch decisions (operator review)

None this session. Every other observation classified as Vision-question and is in the batch below.

## Asks

### Resolved this session

- None.

### Outstanding (cycle-end batch)

The five Vision-questions below are the through-line of the operator's idea: *"the under-13 (and arguably under-18) flow has to be honest, not just a checkbox."* They cluster naturally and should probably be answered together so the policy is coherent.

> **2026-05-10 update — operator-resolved.** Best-practices research (delegated to `compound-engineering:research:best-practices-researcher`, conducted 2026-05-09 evening) reframed every question below. Key surprises: (i) "12+" no longer exists in Apple's taxonomy — auto-mapped to **13+** in the July 2025 overhaul, deadline Jan 31 2026; (ii) age ratings are content advisories, not download gates; (iii) asking DOB creates COPPA "actual knowledge" the moment a <13 DOB is entered, but the [FTC Feb 2026 policy statement](https://www.ftc.gov/news-events/news/press-releases/2026/02/ftc-issues-coppa-policy-statement-incentivize-use-age-verification-technologies-protect-children) explicitly blesses "ask DOB → block" as a safe harbor; (iv) Cal AI's April 2026 removal was paywall-design (§3.1.1/§3.1.2), not age-related — but it's the active rejection vector for wellness apps; (v) parental gate before paywall is NOT Apple-required for general-availability apps. Full synthesis at [09b_AGE_COMPLIANCE.md](09b_AGE_COMPLIANCE.md). Operator chose to ship **only items 1, 2, 5** from the recommendations — risk-mitigation items deferred. Resolution per question below.

#### Q1 — DOB picker lower bound. Should the DOB picker have a minimum age?

**Today.** None. Picker accepts any past date including yesterday.

**Why this is a Vision-question.** The 12+ App Store rating sets a floor on who can *download* the app, not who can *report a birthday inside it*. Three policy options that carry different tradeoffs:

- **(a) No bound, accept the truth.** Whatever DOB the user enters, propagate the under-18 gates we already have. The honest stance is "we trust the picker; the gates do their job." Lowest-effort, most-honest, but it lets a 6-year-old enter a 6-year-old DOB and proceed through onboarding minus alcohol/smoking + the bigNumberPenalty. Are the remaining reveal screens (`lifeGridRemaining`, `recoveryPreview`, `engineRevealAndDial`) appropriate for a 6-year-old?
- **(b) Hard-clamp to 13+ and require parental consent below.** Match COPPA's threshold. Block flow at `BaselineDOBView` if DOB resolves to < 13; show a parental-consent / "ask a grown-up" affordance. Heaviest, but defensible to a privacy-skeptical reviewer.
- **(c) Soft-clamp the picker's `in:` range to ≥ 12 years ago.** Treat the picker as advisory — minors *can* be honest, but the picker doesn't *invite* a kindergartener-DOB. Light-touch.

**Recommendation hold pending operator answer.** This is the most policy-laden of the five.

> **Resolved 2026-05-10:** Option (b) — hard-block under-13 at the DOB picker. Driven by COPPA actual-knowledge doctrine + the FTC Feb 2026 safe harbor for "ask DOB → block." Implementation in [polish-2026-05-10-under-13-block-and-asc-update.md](polish-2026-05-10-under-13-block-and-asc-update.md). Lower picker bound (option c) deferred — the block screen is the policy answer, not picker geometry.

#### Q2 — Reveal escalator softening for under-18. Should `lifeGridRemaining` / `recoveryPreview` / `engineRevealAndDial` be tone-shifted (or suppressed) for minors the way `bigNumberPenalty` already is?

**Today.** Only `bigNumberPenalty` is gated. Minors still see `lifeGridRemaining` ("This is what's still ahead. / Each dot is a week your habits get to shape."), `recoveryPreview` ("{N} more years"), and `engineRevealAndDial` (anchor dial pre-set from a projected lifespan).

**Tradeoff.** The reveal escalator earns a lot of the product's emotional weight. Suppressing it for minors leaves them with a thinner version of onboarding; making it tone-shifted would be redundant with `ToneView` (which they reach two screens after the reveal). The cleanest answer ties to vision Open Question #9 ("Reveal-escalator tone-awareness") — answer that, then this falls out.

> **Resolved 2026-05-10:** Deferred. With under-13 hard-blocked (Q1 resolution), the only minors reaching the reveal escalator are 13–17 — who Apple's age-rating taxonomy permits to see this content. No Apple rule mandates softening. Pure product/tone question; revisit alongside vision Open Question #9.

#### Q3 — Tone auto-shift for under-18. Should `firmDirect` be unselectable (or non-default) for minors?

**Today.** Anyone can pick firmDirect. Copy includes "Today's reckoning", "Owed", "On the clock", "Pick one. Do it."

**Tradeoff.** firmDirect is a deliberate aesthetic — the "respected trainer" voice the vision champions. Restricting it for minors signals safety. Forcing a softer default risks a 17-year-old who explicitly came for the firmer voice feeling like the app underestimated them. Possible middle: gentle defaults selected for under-18, with firmDirect still pickable but not the visual default in `ToneView`.

> **Resolved 2026-05-10:** Deferred. Apple has no published rule restricting tone variants by age. §1.1.1 ("mean-spirited / distressing") risk is theoretical with no precedent. Operator priority is compliance, not press resilience.

#### Q4 — Paywall + parental consent. Should the paywall require a "ask a grown-up" gate below some threshold?

**Today.** No code-level gate. Family Sharing's "Ask to Buy" is the only consent layer, and it lives at the Apple-ID level outside our app.

**Tradeoff.** Apple's IAP infrastructure already handles the kid-safety side via Ask-to-Buy. Adding our own affordance is belt-and-suspenders. If we add it, it needs a clear policy: "skip-paywall for under-18", "show paywall but disable purchase button", "show a separate kid-friendly free-tier copy"? Each carries different App Store risk profiles.

> **Resolved 2026-05-10:** Deferred. Confirmed by research that parental gate before paywall is **NOT Apple-required** for general-availability apps — Apple delegates to Family Sharing's [Ask to Buy](https://support.apple.com/en-us/105055). Self-imposed gate is press-defense, not Apple-compliance. The real present rejection vector for wellness paywalls is Cal-AI-style deceptive billing design (§3.1.1/§3.1.2), and [PaywallPrimaryView.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift) was already built against that precedent.

#### Q5 — DOB picker maximum date. Should the picker reject DOBs in the recent past (e.g., < 4 years ago)?

**Today.** `in: ...Date()` — any past date including yesterday.

**Tradeoff.** A "yesterday" DOB is implausible for a real user; it's either fat-finger or stress-testing. Light validation (DOB must be ≥ 4 years ago, the youngest plausible self-reporting age) would catch the fat-finger case without policy implications. Pure Polish if approved; left as Vision-question because the operator may want zero validation here.

> **Resolved 2026-05-10:** Deferred. With Q1's under-13 hard block in place, the implausible-recent-DOB case (under-4) is captured as "under 13 → block" — same exit. Adding a separate picker max bound is cosmetic, not compliance.

## Regressions caught

- None observed in commit 1. Build green pre and post; AgeGate test suite (5 pre-existing + 5 new = 10 cases) passes.
- Cold-open render unchanged on iPhone 17 — confirmed via `simctl io ... screenshot` after install of the rebuilt app. No new console errors / faults / exceptions in the post-launch 30s window.

## A11y identifiers added

- None this session. The DOB picker (`onboarding.baselineDOB.picker`) is already labeled.

## Vision updates

- **Open Questions to APPEND to vision.md** (operator review before commit):
  - **Age-gate honesty.** What does the product owe a user who reports under-13 / under-16 / under-18? Today: under-18 hides smoking + alcohol pickers (in QuickLog and now in onboarding) and suppresses `bigNumberPenalty`. Everything else — reveal escalator, tone selection, paywall, DOB picker bounds — is age-blind. See [polish-2026-05-09-age-gate-thresholds.md](polish-2026-05-09-age-gate-thresholds.md) Asks Q1–Q5 for the cluster of decisions.
- **Decided constraints proposed (operator-only edit):**
  - **2026-05-09 — Onboarding alcohol/tobacco prompts are gated by `AgeGate.isAdult` everywhere.** Source: this session. Smoking + alcohol screens are hidden in onboarding for minors (added [OnboardingCoordinator.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/OnboardingCoordinator.swift)) and in QuickLog ([QuickLogSheet.swift](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift)). Adding a third surface that asks for these signals is a Vision-question.

## Final check

Lighter-weight pass than full computer-use given this is a routing fix with strong test coverage:

- 10/10 tests in `AgeGateTests` pass (5 existing + 5 new pinning the bodyComp routing for adult / exactly-18 / 17 / 12 / nil DOB branches).
- `xcodebuild build` and `build-for-testing` both succeed; only pre-existing warning is the unrelated `SubscriptionStore` Swift 6 actor-isolation note.
- App installed and launched cleanly on iPhone 17 (1A88AF54). Cold-open screen matches the existing golden visually.
- No new console errors, faults, or exceptions in the launch window.

Computer-use checkpoint **deferred** — both iPhone 17 Pros (73298B82, DD6A5A7B) were occupied by a parallel `OnboardingTerminalsRecon` matrix run on the `kind-dubinsky-fb7862` worktree, and a routing fix that's covered by 5 deterministic unit tests doesn't surface a feel/motion question that AX-tree driving misses. Documented honestly here per the skill's "if you can't drive, say so explicitly" clause. Operator can re-run the visual leg post-merge if desired.

## Next pass

The Vision-questions above (Q1–Q5) should be answered as a cluster — the policy is incoherent if Q1 says "no bound" and Q2 says "soften everything for minors". A short brainstorm session before the next polish pass would resolve them. Once decided, the implementation pass would be:

- **If Q1 = (b) hard-clamp 13+:** new `MinorBlockedView` in onboarding; gate at `BaselineDOBView.onContinue`.
- **If Q2 = soften reveal:** add `isMinor` branches in `LifeGridRemainingView`, `RecoveryPreviewView`, `EngineRevealAndDialView` matching the existing `shouldShowPenaltyScreen()` pattern.
- **If Q3 = no firmDirect for minors:** filter the options list in `ToneView`.
- **If Q4 = paywall gate:** new `PaywallParentalGateView` between `recoveryPreview` and `paywallPrimary` for minors.
- **If Q5 = picker max:** one-line `in: ...Calendar.current.date(byAdding: .year, value: -4, to: Date())!` change to `BaselineDOBView`.
