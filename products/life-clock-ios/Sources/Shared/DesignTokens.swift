import SwiftUI

enum DesignTokens {
    /// Maximum readable content width for scrollable surfaces. Locks cards
    /// to a comfortable column on iPad and Mac Catalyst (when supported);
    /// effectively a no-op on iPhone where the screen is already narrower.
    /// 720pt matches Apple's HIG "long-form reading" target.
    static let readableColumnWidth: CGFloat = 720

    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 16
        static let lg: CGFloat = 24
        static let xl: CGFloat = 32
    }

    enum Radius {
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 18
    }

    enum Palette {
        static let surface = Color(.systemBackground)
        static let elevated = Color(.secondarySystemBackground)
        static let positive = Color.green.opacity(0.85)
        static let negative = Color.orange // muted, never alarming red
        static let muted = Color.secondary
    }

    /// Numeric-display type scale. Mirrors `docs/products/life-clock/typography-spec.md`
    /// § "The numeric-display exception (binding — role-based size families)"
    /// **exactly** — do not invent new sizes here. Any new absolute-size site
    /// must map to one of these role families; a site that doesn't is a
    /// `typography-drift` vision-question, not a new case.
    ///
    /// These are the ONLY sanctioned `.font(.system(size:))` figures. All text
    /// (labels, titles, body, captions) uses Dynamic Type semantic tokens.
    enum Typography {
        /// Healthspan dial center — Future tab headline, Engine reveal,
        /// Lead-in reactive slider demo. 56 → 52 → 36 → 28 fallback chain
        /// (degrade via `ViewThatFits(in: .horizontal)`).
        static let heroNumericChain: [CGFloat] = [56, 52, 36, 28]

        /// Today + WrapUp signed-minutes readout. The brand headline figure.
        static let displayNumeric = Font.system(size: 44, weight: .semibold, design: .rounded)

        /// History weekly net / yesterday delta, InstallSummarySection,
        /// Day-detail metric. 40 → 36 → 28 → 22 fallback chain.
        static let sectionNumericChain: [CGFloat] = [40, 36, 28, 22]

        /// Override input field, archetype reveal label.
        static let inlineNumeric = Font.system(size: 32, weight: .semibold, design: .rounded)

        /// Day-row delta, History compact rows.
        static let compactNumeric = Font.system(size: 22, weight: .semibold, design: .rounded)

        /// Functional icon glyph — `EmptyStateView` icon. Plain weight, no design.
        static let iconGlyphFunctional = Font.system(size: 32, weight: .regular)

        /// Splash icon — Lead-in / data-collection screen. No weight/design.
        static let iconGlyphSplash = Font.system(size: 48)

        /// Largest accessibility size a Display-numeric figure is allowed to
        /// scale up to before it starts truncating the dial / sheet. The
        /// figure is a *visual figure*, not body text, so per
        /// typography-spec.md § Anti-patterns it does not scale unbounded;
        /// instead it clamps and shrinks-to-fit. Validation rule #4 requires
        /// it render at `.accessibility5` without truncation/overlap/clip.
        static let displayNumericMaxDynamicType: DynamicTypeSize = .accessibility3

        /// Floor for `minimumScaleFactor` on the Display-numeric figure so it
        /// never visually drops below ~30pt at `.xSmall` (44 * 0.68 ≈ 30).
        static let displayNumericMinScale: CGFloat = 0.68
    }
}

// MARK: - Numeric-display modifiers

extension View {
    /// Applies the Display-numeric role (Today + WrapUp signed-minutes) with
    /// the typography-spec § Validation #4 AccessibilityXXXL safety baked in:
    /// a dynamic-type clamp + shrink-to-fit so the figure renders at
    /// `.accessibility5` without truncation/overlap/clip and stays a single
    /// line. Use this instead of a raw `.font(.system(size: 44, …))`.
    func displayNumericFigure() -> some View {
        self
            .font(DesignTokens.Typography.displayNumeric)
            .dynamicTypeSize(...DesignTokens.Typography.displayNumericMaxDynamicType)
            .lineLimit(1)
            .minimumScaleFactor(DesignTokens.Typography.displayNumericMinScale)
    }
}

// MARK: - Readable column

extension View {
    /// Constrains scrolling content to a readable column on wide screens.
    /// Centers the content via `.frame(maxWidth:)`, leaving padding outside
    /// the column to mimic native iPad readability. No-op on narrow screens.
    func readableColumn() -> some View {
        self.frame(maxWidth: DesignTokens.readableColumnWidth)
            .frame(maxWidth: .infinity)
    }
}
