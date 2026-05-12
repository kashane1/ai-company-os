# Life Clock — Premium Bar

> **Status:** Observer rubric for `premium-feel-audit`. Read-only product policy doc. The skill scores every audited surface against the categories below and emits backlog prompts for gaps. This file is the bar; the audit emits gaps.
>
> **Initialized:** 2026-05-12. Source docs: [vision.md](vision.md), [haptics-spec.md](haptics-spec.md), [brand-guidelines.md](brand-guidelines.md), the lifecycle-pinned lighting convention (operator memory `feedback_life_clock_lighting_convention.md`).
>
> **Editing rule:** the operator owns this file. The audit skill reads it; it does not edit it. New categories added here become new audit dimensions in the next `premium-feel-audit` run.

---

## Why this rubric exists

`premium-feel-audit` is the elevation-framing sibling of `simulator-polish-recon`. Recon diffs against *prior coverage* and skews remedial. Premium-feel-audit diffs against *this rubric* and produces elevation prompts. The rubric is the bar the audit holds the app to.

A surface that has prior polish coverage may still score badly here — and that's the point. "Polished" is not "premium." Premium is a coherent **system** across motion, haptics, typography, transitions, and microcopy. A surface can be individually polished while feeling inconsistent with the surface next door.

This file is product-scoped to Life Clock. Other products would author their own.

## The signals (binding categories)

The audit walks every visible surface and scores it against each category below. A surface that's `weak` or `absent` in any non-trivial category contributes a `premium-gap` prompt to the backlog.

### Motion

- **Animation curves**: every animated transition uses a curve from the brand-approved set (eased cubic for navigation, spring for direct manipulation, linear only for indeterminate progress). Inconsistent curves across screens = `motion-incoherence`.
- **Durations**: every named animation has a duration that fits one of three brand-defined tiers (instant 100ms, beat 250ms, breath 500ms). Random durations = `motion-incoherence`.
- **Hierarchy**: across surfaces, the same kind of event animates the same way (e.g., "value increased by user action" looks identical on Today, History, and Quest screens). Per-screen reinvention = `motion-incoherence`.
- **Reduction respect**: every animation respects `UIAccessibility.isReduceMotionEnabled`. Missing reduction paths = `motion-incoherence`.

### Haptics

- **Density**: every primary action emits a haptic; every system response that earns user attention emits a haptic. Cross-reference: [haptics-spec.md](haptics-spec.md).
- **Semantic correctness**: success/warning/error haptics match the brand intent (e.g., quest completion is `notificationOccurred(.success)`, not `impactOccurred(.light)`). Wrong-haptic-for-meaning = `haptic-thin`.
- **Motion integration**: when a haptic and an animation co-occur, they land on the same beat. Off-by-tens-of-ms = `haptic-thin`.
- **Coverage**: every screen visited by the audit gets walked for haptic moments. A screen with zero haptics for a user action = `haptic-thin`.

### Typography

- **Scale**: one type scale across the app (e.g., 13 / 15 / 17 / 22 / 28 / 34). Random sizes off the scale = `typography-drift`.
- **Weight hierarchy**: at most three weights in active use. More than three = `typography-drift`.
- **Line height**: consistent line-height ratios across body copy. Per-screen ratios = `typography-drift`.
- **Dynamic Type**: every text style scales correctly under accessibility text-size changes. Fixed-size copy outside the brand-approved exceptions = `typography-drift`.

### Transitions

- **Between-screen coherence**: push/pop transitions use the same animation system across the app. Mixed default+custom = `transition-snag`.
- **Return-to-state preservation**: when the user navigates away and back, scroll position, selection, and content state are preserved. Flash-of-default-state on return = `transition-snag`.
- **No flash-of-empty-state**: push transitions don't reveal an empty state before content loads. Empty-then-fill = `transition-snag`.

### Empty states

- **Specificity**: every empty state has copy that addresses the specific empty condition (e.g., "No quests yet — pick one from your Day Plan" vs "No data"). Generic "No data" = `empty-state-flat`.
- **Action affordance**: every empty state offers at least one next-step the user can take. Dead-end empty = `empty-state-flat`.
- **Brand coherence**: empty-state copy matches the active tone mode (Gentle / Coach / Firm-direct). Tone-mismatched empty = `empty-state-flat`.

### Loading states

- **Present**: every operation > 200ms shows a loading state. Bare frozen UI = `loading-bare`.
- **On-brand**: loading states use brand-approved indicators (custom Life Clock spinner or skeleton), not the system spinner. System-default-only = `loading-bare`.
- **Honest**: indeterminate vs determinate matches the actual operation. Fake progress bar = `loading-bare`.

### Color and lighting

- **Light + dark parity**: every surface looks intentional in both modes. Dark-mode afterthought = `lighting-gap`.
- **Lifecycle-pinned lighting**: rotating/dial elements respect the world-fixed lighting convention (opacity 0.22, offset ratio 0.35/0.85, radius ratio 0.55× of reference size; world-fixed via inverse-rotation math). See operator memory `feedback_life_clock_lighting_convention.md`. Lighting drift = `lighting-gap`.
- **Hue restraint**: no surface introduces a hue not in the brand palette. Off-palette hues = `lighting-gap`.

### Microcopy

- **Density**: every label is as short as it can be without sacrificing clarity. Wordy labels in terse contexts = `microcopy-flab`.
- **Tone coherence**: copy matches the active tone mode. Tone-mismatched copy = `microcopy-flab`.
- **Voice**: copy reads like the canonical voice (terse over chatty, confident over hedged, specific over generic — per [vision.md](vision.md)). Hedged or generic copy = `microcopy-flab`.

### Touch targets and a11y (table-stakes — failures escalate)

- Minimum 44×44pt touch targets per Apple HIG.
- Color contrast ≥ WCAG AA on every text-on-background pairing.
- Every interactive element has an accessibility label.

These are not "premium signals" — they are table-stakes correctness. Failures here are `submission-blocker`-tier and route to recon, not premium-feel-audit.

## Surface-level rubric

The audit reads `products/life-clock-ios/Sources/Features/**/*.swift` to enumerate surfaces. Per surface:

- **Today**: motion + haptics + typography + transitions + microcopy. Empty state when no quests selected. Loading when HealthKit recomputes.
- **History**: motion (timeline scroll), typography hierarchy across day/week/month, empty state for day-1 user, dark-mode parity on the dimmed Today entry.
- **Future**: motion (the projection animation), typography hierarchy across the trajectory cards, transition to detail screens.
- **WrapUp**: motion (sequenced reveal), haptics on each reveal beat, microcopy tone, lighting on the clock face.
- **Quest detail / QuickLog**: haptics on completion, transition coherence, microcopy for completion payoff.
- **Profile**: typography scale across the demoted sections, light+dark parity.
- **Paywall**: covered by `pro-value-audit`, NOT this skill. Premium-feel-audit walks the paywall surface for motion/typography/haptics only — value-claim concerns are pro-value-audit's territory.
- **Onboarding**: covered by recon's submission-readiness flag for completeness; premium-feel-audit walks the visual coherence of onboarding screens but doesn't audit the funnel.

## Anti-signals (what is NOT premium)

These appear on the backlog as `premium-gap` prompts whenever encountered:

- Generic system spinners
- Mismatched corner radii within the same surface
- Copy that says "loading..." (use a brand verb)
- Same event animated differently on two screens
- Haptic on tap but no haptic on the response
- Light-mode-only thinking ("we'll fix dark later")
- Copy that's chatty when the active tone mode is terse
- Empty states that end with "no data" and no next step
- Transitions that reveal empty state before content
- Fixed-size copy outside brand-approved exceptions
- Off-palette hues introduced by third-party SDKs

## Cadence

The rubric evolves as Life Clock's brand evolves. Edits happen when:

- A new surface ships (add it to "Surface-level rubric")
- Brand guidelines change (update the named values)
- A new lifecycle-pinned convention enters operator memory (add it under "Color and lighting")
- An anti-signal recurs across audits (add it to "Anti-signals")

Edits are operator-driven, not audit-driven. The audit reads; the operator writes.

## How this rubric is enforced

The audit reads this file and walks the surfaces. Per category:

1. Score `strong` / `partial` / `weak` / `absent`.
2. For every category that scores `weak` or `absent` on a non-trivial surface, draft a `premium-gap` (or category-specific) prompt.
3. Cite this rubric file + the specific category as evidence in the prompt's `Evidence` field.
4. The consuming `simulator-driven-polish` session will tier the fix as Polish / Stretch / Feature / Vision-question per its own decision layer.
