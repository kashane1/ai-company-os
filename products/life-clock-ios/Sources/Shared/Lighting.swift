import SwiftUI

/// Shared lighting convention for Life Clock surfaces.
///
/// Single source of truth for the depth-shadow constants that
/// appear on the mascot hand, the trajectory chart container, and
/// (eventually) any future surface that needs the same world-fixed
/// depth read.
///
/// Convention (per
/// `~/.claude/projects/-Users-simons-ai-company-os/memory/feedback_life_clock_lighting_convention.md`):
///   * Shadow color: `.black.opacity(0.22)`
///   * Offset ratios: `(0.35 × referenceSize, 0.85 × referenceSize)`
///     — slight rightward bias + drop-down
///   * Radius ratio: `0.55 × referenceSize`
///   * World-fixed: for rotating elements, inverse-rotate the offset
///     so the shadow stays oriented to the world (light source above)
///     rather than rotating with the element.
///
/// Two modifiers:
///   * `.lightingDepth(referenceSize:)` — for non-rotating surfaces.
///     The shadow lands directly at the offset ratios.
///   * `.lightingRotatedDepth(referenceSize:angle:)` — for rotating
///     surfaces (clock hands). Applies the inverse-rotation math so
///     the shadow stays world-fixed:
///
///       world (Wx, Wy) ← rotation(angle) ← local (Lx, Ly)
///       ⇒ Lx = Wx·cos(θ) + Wy·sin(θ)
///         Ly = -Wx·sin(θ) + Wy·cos(θ)
///
///     The modifier must be applied BEFORE `.rotationEffect(angle)`
///     in the view chain (the local-space offset becomes world-fixed
///     once the parent rotation transforms it).
///
/// Existing call sites:
///   * `LifeClockMascotView.hand`  — rotating (uses RotatedDepth)
///   * `TrajectoryChart` container — non-rotating (uses Depth)
///
/// Future call sites earn the modifier; ad-hoc copies of the magic
/// numbers should be replaced via `Lighting.Constants` where possible.
enum Lighting {
    /// Shared numeric constants. Source of truth — do not duplicate.
    enum Constants {
        static let shadowOpacity: Double = 0.22
        static let offsetXRatio: CGFloat = 0.35
        static let offsetYRatio: CGFloat = 0.85
        static let radiusRatio: CGFloat = 0.55
    }
}

extension View {
    /// Apply the depth-shadow convention to a non-rotating surface.
    /// `referenceSize` is typically the surface's primary dimension
    /// (height for a chart card, thickness for a UI bar). The shadow
    /// reads as a static drop falling toward bottom-right.
    func lightingDepth(referenceSize: CGFloat) -> some View {
        self.shadow(
            color: .black.opacity(Lighting.Constants.shadowOpacity),
            radius: referenceSize * Lighting.Constants.radiusRatio,
            x: referenceSize * Lighting.Constants.offsetXRatio,
            y: referenceSize * Lighting.Constants.offsetYRatio
        )
    }

    /// Convenience for the most common case: a card-shaped surface
    /// that wants a subtle world-fixed depth shadow. Uses `referenceSize:
    /// 6` — small enough to read as a lift, not a drop. This is the
    /// "third call site fires the DRY trigger" convenience from
    /// `docs/products/life-clock/lighting-spec.md`. Use this on Today
    /// cards, Paywall product rows, and similar elevated surfaces.
    func cardLighting() -> some View {
        self.lightingDepth(referenceSize: 6)
    }

    /// Apply the depth-shadow convention to a heading or title.
    /// Tuned for **bold or semibold heading-tier text only** — `.headline`,
    /// `.title`, `.title2`, `.title3` with bold/semibold weight, and the
    /// large rounded-display deltas (`.system(size: 22+, weight: .semibold)`).
    /// Do NOT apply to body text (`.callout`, `.subheadline`, `.caption`),
    /// non-bold headings, or button labels. The reference size (3pt) keeps
    /// the shadow tight against the glyph stroke so the depth reads as a
    /// subtle lift rather than a generic drop-shadow.
    func headingLighting() -> some View {
        self.lightingDepth(referenceSize: 3)
    }

    /// Canonical "section card" — single definition for the elevated,
    /// rounded, padded card surface used across Today, History, and
    /// other VStack-based screens. Bundles the four modifiers that
    /// previously had to be repeated at every call site: inner padding,
    /// max-width flush-left frame, elevated rounded background, and the
    /// shared `.cardLighting()` shadow. Use this anywhere you would
    /// otherwise write the four-line incantation by hand.
    ///
    /// Profile uses iOS `Form` + `Section` instead — Form's native row
    /// styling doesn't compose with a per-section shadow, so the
    /// modifier intentionally does not apply there.
    func sectionCard() -> some View {
        self
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                DesignTokens.Palette.elevated,
                in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
            )
            .cardLighting()
    }

    /// Apply the depth-shadow convention to a rotating surface.
    /// The offset is inverse-rotated so the shadow stays oriented to
    /// the world (light from above-right) regardless of the surface's
    /// rotation. Apply BEFORE `.rotationEffect(angle)`.
    func lightingRotatedDepth(referenceSize: CGFloat, angle: Angle) -> some View {
        let worldDx = referenceSize * Lighting.Constants.offsetXRatio
        let worldDy = referenceSize * Lighting.Constants.offsetYRatio
        let theta = angle.radians
        let localDx = worldDx * cos(theta) + worldDy * sin(theta)
        let localDy = -worldDx * sin(theta) + worldDy * cos(theta)
        return self.shadow(
            color: .black.opacity(Lighting.Constants.shadowOpacity),
            radius: referenceSize * Lighting.Constants.radiusRatio,
            x: localDx,
            y: localDy
        )
    }
}
