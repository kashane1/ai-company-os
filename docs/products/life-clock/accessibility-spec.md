# Accessibility Spec — Life Clock

> **Status:** Canonical product policy. Accessibility failures in Life Clock escalate to `submission-blocker` per [`premium-bar.md`](premium-bar.md) § "Touch targets and a11y" + cross-sibling escalation tier in [`skills/canonical/shared/recon-scaffolding.md`](../../../skills/canonical/shared/recon-scaffolding.md). The 2026-05-12 premium-feel audit didn't flag any a11y blockers, but several polish logs converged on partial rules (`polish-2026-05-06-accessibility-color-matrix.md`, `polish-2026-05-12-trajectory-chart-a11y-colorblind-xxl.md`, `polish-2026-05-09-day-1-post-onboarding-tones.md` VoiceOver passes). This spec consolidates them so future drift is caught at the rule layer, not at submission time.

## One-line rule

**Every Life Clock surface is usable by every iOS user — touch, voice, screen, larger text, reduced motion, dark mode, color-blind palette, voice-over.** The app holds the iOS-native accessibility line; nothing is opt-in or off-by-default.

## The five binding axes

| Axis | Rule | Verification |
|---|---|---|
| **Touch targets** | Every interactive element has a hit-target ≥ 44×44 pt. | Visual inspection + UITest `tap()` on small affordances. |
| **VoiceOver** | Every interactive element has an `.accessibilityLabel` (and `.accessibilityHint` if action is non-obvious). Decorative elements use `.accessibilityHidden(true)`. Computed values (like the signed minutes) are announced via the parent container's label, not by the visual `Text`. | XCUITest with `XCUIApplication().accessibilityElement` walks. |
| **Dynamic Type** | Surfaces render at `UIContentSizeCategory.accessibilityExtraExtraExtraLarge` without truncation, overlap, hidden controls, or broken layout. Numeric-display exceptions (per [`typography-spec.md`](typography-spec.md)) stay fixed — they're figures, not labels. | UITest with `XCUIApplication().launchArguments += ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]`. |
| **Reduce Motion** | Every animation site short-circuits to `nil` (instant transition) or a static equivalent when `@Environment(\.accessibilityReduceMotion)` is true. No site stacks two animations on reduceMotion. | Unit test paths that mock the environment + visual verification with the system toggle. |
| **Color & contrast** | Every signal uses (a) color + (b) glyph or text, never color alone. WCAG AA contrast on every text run. Color-blind palette: positive/negative/elevated colors are distinguishable on protanopia + deuteranopia (per `polish-2026-05-06-accessibility-color-matrix.md`). Dark-mode contrast holds at the same ratios. | Color-blind simulator + Xcode Accessibility Inspector. |

## Common patterns

### "Connect Apple Health" honest status

`HealthKitServiceProtocol.authorizationKnown` returns one of three values surfaced as user copy: **"Not configured"** (haven't asked) / **"Available"** (asked, granted, data flowing) / **"No data"** (asked, granted, but no samples in window). Never "Denied" or "Connected" — Apple's privacy model doesn't let us know denied state, and "Connected" implies a live link the app doesn't actually maintain. This is a load-bearing honesty pattern; rule lives here, implementation in `Sources/Services/HealthKitServiceProtocol.swift`.

### Signed-minutes announcement

The Today + WrapUp signed-minutes readout (`.system(size: 44…)`) is **`.accessibilityHidden(true)`** — already announced by the parent container's `.accessibilityLabel` to avoid double-reading via VoiceOver. See `WrapUpSheet.swift` for the canonical pattern (the visual `Text` is hidden; the parent `ClockHandView` carries the label `"Clock showing plus 18 minutes"`).

### Numeric display + screen reader

VoiceOver reads numbers character-by-character unless you give it a phrase. Use `.accessibilityLabel("plus 18 minutes")` not the raw "+18 min" string for signed deltas. `ClockHandView.accessibleDelta` is the canonical formatter (sign-word + digits + unit-word).

### Tone-aware copy + VoiceOver

Tone-pool copy must work under VoiceOver without visual context (per [`microcopy-spec.md`](microcopy-spec.md) § Validation). "Today moved you forward by 18 minutes" reads correctly in isolation; "Today: +18" depends on visual context and is a VoiceOver miss for the same tone variant.

### Charts + color

`TrajectoryChart` carries the protanopia/deuteranopia-safe palette per `polish-2026-05-12-trajectory-chart-a11y-colorblind-xxl.md`. The past-vs-future line distinction is also encoded as a stroke-dash pattern, not color alone. Don't regress to color-only encoding when adding new chart layers.

### Reduce Motion + the reveal escalator

The escalator's narrative animations (analyzing screen, archetype reveal, life grid, big-number-penalty) must each provide a non-animated equivalent under reduceMotion. The flow doesn't shorten — the user still sees every screen — but transitions go instant. `EngineRevealAndDialView` is the canonical example: `.animation(.snappy, value: displayedYears)` becomes `.animation(nil, value: displayedYears)` under reduceMotion.

### Reduce Motion + the heartbeat

`LifeClockMascotView`'s heartbeat (`TimelineView(.animation(...))`) does NOT continuously animate under reduceMotion — it swaps to a static heart-glyph variant. Continuous animation on lock-screen lift is the worst case for vestibular sensitivity.

## Under-18 minor surfaces

Under-18 users (per [`AGE_COMPLIANCE.md`](AGE_COMPLIANCE.md) + `Sources/Engines/AgeGate.swift`) have alcohol + smoking pickers hidden across onboarding (`OnboardingScreen.afterBodyComp`) and daily (`QuickLogSheet` via `store.isAdultUser`). This is a content-rating decision, not an accessibility one — but the same principle holds: the app reshapes itself per the user's documented identity, not the user's working around it.

## Anti-patterns (binding refusals)

- **Do not use color alone to convey a signal.** Every "Today moved positive vs negative" surface pairs color with text/glyph.
- **Do not stack `Image` + visible `Text` without `.accessibilityHidden(true)` on one of them.** VoiceOver will read both.
- **Do not break Dynamic Type with fixed `.frame` heights on text containers.** Use `minHeight:` or let SwiftUI size.
- **Do not animate motion-sensitive elements** (parallax, large transforms, continuous loops) without a reduceMotion short-circuit. Vestibular-trigger animations have crashed App Review submissions in the past.
- **Do not auto-advance critical screens** (paywall, age-gate, sensitive-consent block) on a timer. Auto-advance with reduceMotion off is bad; with reduceMotion on it's a trap.
- **Do not require a long-press** for primary actions. Long-press is a secondary affordance only.
- **Do not place tappable elements within 8 pt** of each other without expanding tap targets, even if the visual sizes are small.

## Cross-references

- Premium-bar: [`premium-bar.md`](premium-bar.md) § "Touch targets and a11y" (binding submission-blocker)
- Color-blind matrix: `polish-2026-05-06-accessibility-color-matrix.md`
- Trajectory chart a11y + XXL: `polish-2026-05-12-trajectory-chart-a11y-colorblind-xxl.md`
- HealthKit honest-state pattern: [`HEALTH_DATA_STRATEGY.md`](HEALTH_DATA_STRATEGY.md) § Permission flow
- Reduce-Motion conventions: [`motion-spec.md`](motion-spec.md) § Anti-patterns
- VoiceOver microcopy: [`microcopy-spec.md`](microcopy-spec.md) § Validation
- Under-18 + under-13: [`AGE_COMPLIANCE.md`](AGE_COMPLIANCE.md), [`PRIVACY_COMPLIANCE.md`](PRIVACY_COMPLIANCE.md)

## Validation (submission-blocker preconditions)

A surface is accessibility-aligned when ALL of the following hold:

1. Every interactive element has a hit-target ≥ 44×44 pt.
2. Every interactive element has a meaningful `.accessibilityLabel` (and `.accessibilityHint` when action is non-obvious).
3. Decorative or duplicate-read elements use `.accessibilityHidden(true)`.
4. The surface renders correctly at `UICTContentSizeCategoryAccessibilityXXXL`.
5. Every animation respects `reduceMotion`.
6. No signal is color-only; every signal pairs color + text or glyph.
7. Contrast meets WCAG AA on every text run, in both light and dark mode.
8. The surface works under VoiceOver — every action is reachable, every value announced.

When (1)–(8) hold, the surface clears the submission-blocker escalation gate. The premium-readiness flag in [`premium-bar.md`](premium-bar.md) requires every shipped surface to pass.
