# Lighting Spec — Life Clock

> **Status:** Canonical product policy. The shipped code in [`Sources/Shared/Lighting.swift`](../../../products/life-clock-ios/Sources/Shared/Lighting.swift) is the implementation. This doc explains the WHY and is the source-of-truth before any future surface adopts the convention. The numeric constants below must match `Lighting.Constants` exactly — if you change one, change both in lockstep.
>
> Previously the convention lived only in operator memory (`feedback_life_clock_lighting_convention.md`). The 2026-05-12 premium-feel audit flagged three lighting-gap prompts because the convention was visible to two surfaces only (mascot hand + bezel; trajectory chart container) while other surfaces — WrapUp's ceremony clock face, the Today cards, Paywall product rows — diverged. Promoting this to a canonical spec is the first step in the elevation backlog.

## One-line rule

**Every Life Clock surface is lit from one coherent light source: upper-left, world-fixed.** Shadows fall slightly right and mostly down. Rotating surfaces inverse-rotate their shadow offset so the shadow stays world-fixed even as the parent rotates.

## Why

The iOS app icon is a 3D-rendered clock with an implied light source above. Every UI surface should read as lit by the same light, so the app feels cohesive rather than slapped-together. As more small animations and mascot variants ship, a single convention prevents shadow chaos.

## Numeric constants (binding)

These must match `Lighting.Constants` in [`Sources/Shared/Lighting.swift`](../../../products/life-clock-ios/Sources/Shared/Lighting.swift):

| Constant | Value | Used as |
|---|---|---|
| `shadowOpacity` | **0.22** | Outer-shadow color opacity |
| `offsetXRatio` | **0.35** | Horizontal offset multiplier of reference size |
| `offsetYRatio` | **0.85** | Vertical offset multiplier (heavier — light is above) |
| `radiusRatio` | **0.55** | Shadow blur radius multiplier of reference size |

**"Reference size"** = the element's thickness or smaller dimension. Examples:

- Bar/underline → bar height
- Clock hand → capsule width
- Card / panel → height
- Mascot bezel → ring thickness

## The two SwiftUI modifiers

Both shipped in [`Sources/Shared/Lighting.swift`](../../../products/life-clock-ios/Sources/Shared/Lighting.swift).

### `.lightingDepth(referenceSize:)` — non-rotating surfaces

Plain drop-shadow with the convention constants. Use on titles, underline bars, cards, badges, mascot bezels, chart containers — anything that doesn't rotate.

```swift
SomeCard()
    .lightingDepth(referenceSize: cardHeight)
```

SwiftUI's native `.shadow(...)` is already world-fixed for non-rotating views, so the modifier just supplies the right constants.

### `.lightingRotatedDepth(referenceSize:angle:)` — rotating surfaces

For anything with `.rotationEffect(...)`. The modifier pre-rotates the local offset by the inverse of the rotation angle so that *after* the parent rotation applies, the shadow lands in world coordinates.

```swift
ClockHand()
    .lightingRotatedDepth(referenceSize: capsuleWidth, angle: handAngle)
    .rotationEffect(handAngle)  // ← lightingRotatedDepth comes BEFORE this
```

The math is `Lx = Wx·cos(θ) + Wy·sin(θ); Ly = -Wx·sin(θ) + Wy·cos(θ)`, encoded directly in the modifier body — call sites never need to compute it.

### Inner shadows (recessed surfaces)

A face/panel set below a rim (e.g., the mascot's clock face below its outer rim) uses SwiftUI's `ShapeStyle.shadow(.inner(...))` with the same offset ratios. Use **depth × 1.0** as the radius, **depth × 0.35** as the x-offset, and **depth × 0.85** as the y-offset, where `depth` is the recess depth (e.g., the rim thickness):

```swift
Circle().fill(
    Color(.systemBackground).shadow(
        .inner(
            color: .black.opacity(0.20),
            radius: depth * 1.0,
            x: depth * 0.35,
            y: depth * 0.85
        )
    )
)
```

Inner-shadow opacity is **0.20** (one notch lower than outer's 0.22) because inner light reads as more diffuse.

## Where the convention currently lives

| Surface | File | Mode |
|---|---|---|
| Mascot clock hand | `Sources/Shared/LifeClockMascotView.swift` `hand()` | `lightingRotatedDepth` (rotating) |
| Mascot bezel | `Sources/Shared/LifeClockMascotView.swift` `bezel()` | Inner shadow (recessed) + outer (drop) |
| Trajectory chart container | `Sources/Features/Future/TrajectoryChart.swift` | `lightingDepth` (non-rotating) |

## Where the convention should be applied next

Premium-feel audit 2026-05-12 surfaced three lighting-gap prompts; these are the elevation candidates (Prompt 5 in particular asks for the DRY trigger plus extending the modifier across cards and WrapUp):

- **WrapUpSheet's ceremony clock face** — currently uses ad-hoc shadow constants; should adopt `lightingRotatedDepth` to read as a member of the same lighted family as the mascot hand.
- **Today cards** (`headline`, `clockCard`, `mascotHero`, `driversCard`, `questsCard`, `quickLogCard`, `ReflectionCard`, `monthlyLoggingBanner`) — currently use system-default or no shadow; should adopt `lightingDepth(referenceSize:)` to elevate from "flat list" to "lit cards" per the premium-bar.md "Color and lighting" rubric.
- **Paywall product rows** (`PaywallSheet.productRow`) — currently a plain stroke; should adopt `lightingDepth` when selected so the chosen product row "lifts" toward the light.

## Anti-patterns (binding refusals)

- **Do not invent shadow constants.** If you find yourself reaching for `0.15`, `0.30`, `0.5` opacity, you're off-convention. Use `Lighting.Constants.shadowOpacity`.
- **Do not flip the offset signs.** Light is always upper-left → shadow always falls toward lower-right (`+x`, `+y` in screen-space).
- **Do not apply `lightingRotatedDepth` to non-rotating views.** It's a noop and confuses future readers.
- **Do not apply the convention to interactive-state shadows** (pressed-button lift, focus ring, modal scrim). Those have their own SwiftUI/HIG defaults and live outside this convention.
- **Do not preemptively extract** a new helper when only one new call site exists. Wait for the third call site to fire the DRY trigger — that's when a `liftedShadow(size:)` / a generic `.cardLighting()` modifier earns its place.

## Cross-references

- Operator memory: `feedback_life_clock_lighting_convention.md` (point-in-time observation; this spec supersedes it for "rule" purposes).
- Premium-bar: `premium-bar.md` § "Color and lighting".
- Premium-feel audit findings: `premium-feel-backlog-2026-05-12-standard.md` Prompts 5, 11, 13.
- Implementation: `Sources/Shared/Lighting.swift`.

## Validation

Three conditions hold once a surface is on-convention:

1. **Cohesion test.** In light *and* dark mode, the surface's shadow reads as part of the mascot's same lighted scene.
2. **Constants test.** Searching `grep -rE '\.shadow\(.*0\.[0-9]+' Sources/` returns only `Lighting.swift` plus inner-shadow call sites — every other shadow uses the modifier.
3. **Rotation test.** Any surface with `.rotationEffect(...)` calls `.lightingRotatedDepth(...)` *before* the rotation modifier in the view chain.

When all three hold, the surface is lighting-aligned. The premium-readiness flag in `premium-bar.md` requires every rotating/dial surface to pass.
