# Reference Apps — Life Clock

> **Status:** Canonical product policy. Codifies the two reference apps the audit's reference-match prompts compare against. Both choices were operator-ratcheted 2026-05-13 in response to the post-Sprint-D audit-prompt review. The reference apps differ by domain on purpose: premium-feel (craft) and pro-value (paywall craft + emotional register) each have their own benchmark.

## One-line rule

**Match the craft, reject the framing.** Life Clock studies premium iOS apps to learn motion / transitions / paywall design — never to import their product worldview.

## Premium-feel reference — **Death Clock: The Life Lab**

App Store: <https://apps.apple.com/us/app/death-clock-the-life-lab/id6499554412>

### Why Death Clock

- **Direct category competitor** — self-described "#1 longevity app." Validates the category and the willingness-to-pay band Life Clock is targeting (see [`BUSINESS_PLAN.md`](BUSINESS_PLAN.md) §4 + [`MONETIZATION.md`](MONETIZATION.md) [S1]).
- **Same problem space** — health-data-in, projected-lifespan-out. Their reveal animations, projection visualizations, and trajectory transitions are the closest direct comparison for Life Clock's equivalent surfaces.
- **Established craft floor** — they've shipped multiple versions, including the 2025 "Life Lab" pivot to AI concierge. Their motion and transition vocabulary is reference-grade for the category.

### What to study — and what to NOT study

**Match (craft-level):**

- Reveal-animation timing + curve choice for the projected-lifespan reveal.
- Transition coherence between the prediction view and the supporting-detail views.
- Number-animation patterns (the way "predicted death date" counts up or animates into place).
- How they pace dramatic moments (their app is more dramatic than ours by design — observe the *pacing technique* even where we'd tone it down).

**Reject (framing-level):**

- AI-concierge framing — vision Decided constraint "No AI health concierge in v1" ([`vision.md`](vision.md)).
- Bloodwork-upload + lab-result integration — vision Scope (v1 non-goals).
- "Predicted death date" as the headline — Life Clock's wedge is *trajectory, not prophecy* (vision Decided constraint).
- Mortality-lexicon-heavy copy — Life Clock has its own tone system per [`microcopy-spec.md`](microcopy-spec.md) § Safety registers.
- Hard paywall before first value — Life Clock's onboarding skip path is binding.

## Pro-value reference — **MacroFactor**

App Store: <https://apps.apple.com/us/app/macrofactor-workouts-tracker/id6737156524>

### Why MacroFactor

- **Direct philosophical alignment.** MacroFactor's stated design philosophy is "adherence-neutral — no guilt-based interfaces, no red warning zones when users exceed calories." This maps verbatim to Life Clock's "drama, not cruelty" + "orange not red" rules ([`palettes-spec.md`](palettes-spec.md) § Orange-not-red invariant + [`microcopy-spec.md`](microcopy-spec.md) § Anti-patterns).
- **Same price band.** $71.99/yr vs Life Clock's $49.99/yr — comparable enough that the value-claim math reads in the same register.
- **Top-quartile paywall craft.** ~$1M/mo revenue. Six documented paywall iterations since 2021 — sophisticated A/B-tested baseline.
- **Premium-only model** (different from Life Clock's freemium) is a *useful* divergence: it forces the paywall to do all the convincing, so their copy + visual structure are reference-grade for value-claim density. Life Clock's paywall doesn't have to convince as hard (Free is real) but the craft floor applies.

### What to study — and what to NOT study

**Match (craft + voice):**

- Adherence-neutral copy — how they describe Pro features without shame or scarcity.
- Pricing presentation — the ratio of price + period + monthly-equivalent + savings copy. Life Clock now has these in place (Sprint A1); compare for refinement.
- Hierarchy of the paywall: title → subhead → bullets → product list → CTA → fineprint. Life Clock's `PaywallSheet.header` should match the cadence.
- How they justify per-feature value without overpromising — every claim maps to a delivered surface.

**Reject (model-level):**

- Hard paywall before first value — Life Clock has a real free tier (vision Decided).
- Mandatory subscription — Life Clock ships a freemium with reachable Free.
- Trial-required onboarding — Life Clock v1 ships without a trial ([`MONETIZATION.md`](MONETIZATION.md) § Trial stance).

---

## Per-prompt comparison framework

These tables anchor the audit's reference-match prompts. When the operator (or a `simulator-driven-polish` session in `reference-match` mode) has the reference app open, walk these dimensions.

### Premium-feel P8 — Future projection-reveal vs. Death Clock projection animation

Target surface: [`FutureView.swift`](../../../products/life-clock-ios/Sources/Features/Future/FutureView.swift) headline projection + [`TrajectoryChart.swift`](../../../products/life-clock-ios/Sources/Features/Future/TrajectoryChart.swift) reveal.

Death Clock equivalent: the moment after the 29-question onboarding when the predicted date(s) animate into place.

| Dimension | Look for in Death Clock | Compare to Life Clock |
|---|---|---|
| **Total duration** | How many seconds does the headline number resolve? | `HealthspanEngine` projection text uses `.snappy` content transition (see `FutureView.swift:94` for the 52pt hero numeric). Compare resolve speed. |
| **Easing curve** | Linear / spring / overshoot? | Currently `.snappy` (`Motion.Curve.snappy`). Per `motion-spec.md`, snappy is for celebratory moments. Is Death Clock's reveal celebratory or solemn? |
| **Number animation shape** | Roll-counter / fade-and-replace / digit-by-digit? | We use `.contentTransition(.numericText(...))` — does Death Clock match? |
| **Trajectory line draw-in** | Stroke-from-left / fade-in / segment-by-segment? | `TrajectoryChart` uses `.animation(.smooth(duration: 0.18), value: ...)` per chart spec |
| **Context appearance** | When do supporting paragraphs appear (synchronous / sequential)? | Free narrative line + slider section in `FutureView`. Sequencing? |
| **Negative-delta treatment** | Does their UI flinch / pause / highlight on a bad result? | Life Clock has the `rescueLine` softener; Death Clock probably doesn't. |
| **Reduce-Motion fallback** | What happens on Reduce Motion? | Already guarded in `EngineRevealAndDialView` + `FutureView` (Sprint A4) |

**Goal:** identify 1–3 specific motion tweaks that elevate Life Clock's reveal toward Death Clock's craft floor without importing the prophecy framing.

### Premium-feel P13 — Today first-reveal motion vs. Death Clock first daily check

Target surface: [`TodayView.swift`](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) `wakeProgress` animation + mascot wake + `headline` signed-minutes appear.

Death Clock equivalent: their daily check-in / progress-update sequence.

| Dimension | Look for in Death Clock | Compare to Life Clock |
|---|---|---|
| **Wake-on-foreground timing** | How fast does the screen orient after foregrounding? | `Self.wakeDuration = 1.0s` `.easeOut` (above the `breath` tier — narrative beat) |
| **Hero number entrance** | Slide / fade / scale? | `.system(size: 44)` headline — appearance is tied to wake but not animated discretely |
| **Mascot / icon animation** | What's their identity-mark equivalent (if any)? | LifeClockMascotView heartbeat + hand-sweep ratio |
| **Driver / detail card cadence** | Do supporting cards appear synchronously with the headline or after a beat? | Today renders in document order — no staggered reveal |
| **First-day-of-use special-case** | Different sequence for fresh install? | `day0` state on Future is recognized; Today's first-reveal isn't differentiated |
| **Tap-feedback density** | Haptics on first reveal? | `morningWakeHapticTrigger` + `mascotWakeTrigger` per [`haptics-spec.md`](haptics-spec.md) |

**Goal:** identify whether a staggered-reveal pattern on Today would lift the first-impression moment without slowing down day-2-onward use.

### Premium-feel P14 — Transition coherence across primary nav (Today / History / Future / Profile)

Reference: Death Clock's primary nav transitions.

| Dimension | Look for in Death Clock | Compare to Life Clock |
|---|---|---|
| **Tab-switch crossfade** | Cross-dissolve / push / instant? | Default SwiftUI `TabView` — no custom transition |
| **Shared element morphs** | Does the projected-lifespan number persist across tabs? | Life Clock's Life Clock value is recomputed per tab; not visually persistent |
| **Header / mascot behavior** | Does an identity-mark span all tabs? | Persistent mascot header is a vision Decided constraint |
| **Direction conventions** | Left-to-right for forward, right-to-left for back? | Default iOS conventions; no overrides |
| **Mid-task tab switches** | What happens to in-progress state (Plan Editor open, etc.)? | Standard SwiftUI sheet behavior |

**Goal:** decide whether Life Clock's default tab transitions are intentionally restrained ("calm, not flashy") or under-crafted. The audit's prompt allows either — but we need a Decided answer to stop the prompt recurring.

### Pro-value P5 — PaywallSheet vs. MacroFactor paywall (Justification depth)

Target surface: [`PaywallSheet.swift`](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift) (and [`PaywallPrimaryView.swift`](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift) for onboarding terminus).

MacroFactor equivalent: their premium-only paywall (one of six iterations on `paywallscreens.com/apps/macrofactor-mobile-paywall-065b`).

| Dimension | Look for in MacroFactor | Compare to Life Clock |
|---|---|---|
| **Header hierarchy** | Title → subhead → bullets density | `PaywallSheet.header`: "Unlock the full Life Clock" + "Pro adds depth:" + 5 bullets (per [`paywall-spec.md`](paywall-spec.md) § Header contract) |
| **Bullet specificity** | How concrete is each promise? Are deliverables named, or fluffy ("AI-powered insights")? | Sprint C2 tightened these. Compare specificity. |
| **Visual structure** | Are bullets a list / chips / cards? Glyph treatment? | We use `checkmark.circle.fill` + tone-neutral title + tinted detail per `paywall-spec.md` § Visual-signal vocabulary |
| **Pricing presentation** | Single price / multiple plans / annual prominence | 3-tier with annual pre-selected + savings badge + monthly equivalent (Sprint A1) |
| **Anchor pricing** | Strikethrough monthly-equivalent / "save N%" / lifetime-vs-annual | Life Clock now has "Save ~48%" + "$4.17/mo equivalent" + "Best value" |
| **Trial framing** | Trial timeline UI / no-trial pitch | Life Clock has no trial; MacroFactor uses 7-day trial. **Cannot import trial-specific patterns** |
| **Restore + manage subs** | Where do these live? Above/below the fold? | Sprint A pro-value P1 + restore-button-in-toolbar |
| **Fine print** | Density of auto-renew disclosure | App Review § 3.1.2 required; we have it inline |
| **Empty / loading state** | When products are loading | Life Clock uses `LifeClockSpinner(.regular)` (Sprint B2) |
| **Adherence-neutral copy** | No "before it's too late" / no shame framing | Life Clock's copy is on-spec; verify against MacroFactor's voice baseline |

**Goal:** identify 1–3 specific paywall refinements (a bullet density tweak, an anchor-pricing nuance, a justification-copy specificity bump) that would close the craft-gap with MacroFactor without changing Life Clock's freemium model or no-trial stance.

---

## How to run a reference-match

When the operator next opens Death Clock or MacroFactor:

1. Walk the comparison framework table for the target prompt.
2. Capture screenshots of the reference moments (Apple frame-perfect screenshots via Xcode simulator are usable for documentation but App Store screenshots from the reference are sufficient).
3. Note 1–3 specific deltas where Life Clock should converge (and 0–N where Life Clock should *diverge* intentionally — those go into vision-question candidates).
4. File the convergence deltas as polish-tier prompts in the next `premium-feel-backlog-*` / `pro-value-backlog-*` cycle.

The reference doesn't dictate; it informs. Life Clock has its own decided constraints and they win when in conflict.

## Anti-patterns (binding refusals)

- **Do not blanket-clone a reference pattern.** Match the craft, reject the framing — for both apps.
- **Do not import Death Clock's mortality-heavy lexicon** anywhere in Life Clock copy, even in firmDirect tone.
- **Do not import MacroFactor's hard-paywall onboarding.** Life Clock's free tier is a vision Decided constraint.
- **Do not import MacroFactor's trial pattern** while Life Clock v1 ships without a trial.
- **Do not silently re-pick references.** Changing either reference is a vision-ratchet — surface as an Open Question first.
- **Do not split-vote the references.** Use Death Clock for premium-feel reference-matches and MacroFactor for pro-value reference-matches; don't use Death Clock for paywall comparison or MacroFactor for motion comparison. The reference apps were chosen for category-specific reasons.

## Cross-references

- Death Clock — [App Store listing](https://apps.apple.com/us/app/death-clock-the-life-lab/id6499554412)
- MacroFactor — [App Store listing](https://apps.apple.com/us/app/macrofactor-workouts-tracker/id6737156524)
- Premium-feel rubric: [`premium-bar.md`](premium-bar.md)
- Pro-value rubric: [`pro-value-rule.md`](pro-value-rule.md)
- Paywall rules: [`paywall-spec.md`](paywall-spec.md)
- Microcopy safety registers: [`microcopy-spec.md`](microcopy-spec.md)
- Vision constraints: [`vision.md`](vision.md)
- Original audit prompts: `premium-feel-backlog-2026-05-12-standard.md` Prompts 7, 8, 13, 14; `pro-value-backlog-2026-05-12-standard.md` Prompt 5
