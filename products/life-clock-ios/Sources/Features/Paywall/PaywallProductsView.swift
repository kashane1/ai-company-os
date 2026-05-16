import SwiftUI
import StoreKit

/// Shared paywall core extracted from `PaywallSheet` (re-engagement from
/// Profile / History / Future / WrapUp) and `PaywallPrimaryView` (the
/// onboarding-terminal wrapper) — the Phase 6 follow-up TODO that lived
/// at the top of `PaywallPrimaryView`.
///
/// **Why a per-surface variant rather than one merged rendering:** the
/// two paywall shells render the product list with deliberately
/// different presentation today —
///
/// - `PaywallSheet` iterates `subscriptions.products`, shows savings
///   badges, an "Auto-renews yearly/monthly" period label, a "$x.xx /
///   month equivalent" line, and selects by `productID`. It has no
///   `paywall.tier.*` identifiers.
/// - `PaywallPrimaryView` renders a fixed three-row Yearly / Lifetime /
///   Monthly toggle, "≈ $x.xx / mo equivalent", "One-time purchase",
///   selects by product id, and exposes `paywall.tier.annual / monthly
///   / lifetime`.
///
/// PV-P2 is a **structural refactor with a strict no-behavior-change
/// contract**: pricing strings, per-month-equivalent, Restore behavior,
/// and the auto-renew fineprint must be byte-identical before/after on
/// BOTH surfaces. Forcing one shared rendering would change the strings
/// and identifiers on one surface — a user-visible behavior change under
/// a refactor commit, which the contract forbids. So the core encodes
/// BOTH renderings behind a `Surface` variant. The value the extraction
/// delivers is structural: the perks block, the Restore semantics, and
/// the product list / price / per-month math now live in ONE place and
/// cannot silently diverge between the two pitch surfaces again (the
/// divergence the prior PV-P1 perks gap was the first symptom of).
///
/// **Environment:** every constituent view reads `SubscriptionStore` via
/// its own `@Environment` so the store resolves through the SwiftUI
/// graph of whichever shell composes it. Per
/// `feedback_observable_environment_sheets.md` (commit `5b0b397`
/// precedent) every call site that presents a paywall in a sheet/cover
/// already re-injects `.environment(subscriptions)`; the shared views
/// inherit it from there — they do not own that boundary.
enum PaywallProductsView {
    /// Which shell is composing the core. Selects the exact per-surface
    /// rendering + identifiers so both stay byte-identical to the
    /// pre-extraction code.
    enum Surface {
        /// Re-engagement sheet (Profile / History / Future / WrapUp).
        case reengagement
        /// Onboarding-terminal wrapper.
        case onboarding
    }

    // MARK: - Restore (semantics shared; the surrounding chrome —
    // toolbar button vs inline button — stays in the shell).

    /// Restore semantics shared by both surfaces so they cannot diverge:
    /// clear any prior error → restore → report whether the call
    /// succeeded but granted no entitlements. Both shells keep their own
    /// surrounding chrome (the sheet's spinner / disabled / empty-hint;
    /// the onboarding plain button). The sheet auto-dismisses on the
    /// `isPro` flip via its existing `onChange`, so a successful restore
    /// needs no extra path. The onboarding shell calls
    /// `subscriptions.refreshEntitlements()` directly (its prior
    /// behavior, unchanged) — only the re-engagement sheet uses this.
    /// `@MainActor` because it reads `SubscriptionStore`'s
    /// MainActor-isolated `lastError` / `isPro` after the restore. Both
    /// call sites already run on the main actor (SwiftUI `View` methods),
    /// so the isolation is observed, not changed — no behavior delta.
    @MainActor
    static func runReengagementRestore(_ subscriptions: SubscriptionStore) async -> Bool {
        await subscriptions.clearLastError()
        await subscriptions.restore()
        return subscriptions.lastError == nil && !subscriptions.isPro
    }
}

// MARK: - Perks (byte-identical content on both surfaces — the
// genuinely shared core; was previously hand-rolled twice as
// `PaywallSheet.proBullet` + `PaywallPrimaryView.proPerks`).

/// Concrete 5-perk enumeration sourced verbatim from `ProPerks.perks`
/// (the single source of truth kept in lockstep with MONETIZATION.md §
/// Pro Annual — never re-type the strings; App Review's value-claim
/// guard requires a verbatim match).
///
/// **A11y parity:** the onboarding surface exposes the perks block as
/// its own combined `paywall.perks` element (the existing onboarding
/// UITest asserts it). The re-engagement sheet did NOT — its perks
/// bullets lived inside the `paywall.header` combined element with no
/// nested `paywall.perks`. To keep BOTH surfaces' AX trees
/// byte-identical to the pre-extraction code, the combined
/// `paywall.perks` wrapper + the PV-P1 `.fixedSize(vertical:)` wrap
/// guarantee are applied only on the onboarding surface; the
/// re-engagement sheet renders byte-identically to its prior
/// hand-rolled `proBullet` loop.
struct PaywallPerksView: View {
    let surface: PaywallProductsView.Surface

    var body: some View {
        let onboarding = surface == .onboarding
        return VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            ForEach(ProPerks.perks, id: \.title) { perk in
                HStack(alignment: .firstTextBaseline, spacing: DesignTokens.Spacing.sm) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.tint)
                        .font(.footnote)
                    (Text(perk.title).fontWeight(.semibold)
                        + Text(" — ")
                        + Text(perk.detail).foregroundStyle(.secondary))
                    .font(.subheadline)
                    .fixedSize(horizontal: false, vertical: onboarding)
                }
            }
        }
        .modifier(OnboardingPerksA11y(active: onboarding))
    }

    /// Applies the combined `paywall.perks` accessibility element only
    /// on the onboarding surface (the re-engagement sheet never had a
    /// nested `paywall.perks` — its perks lived inside `paywall.header`).
    private struct OnboardingPerksA11y: ViewModifier {
        let active: Bool
        func body(content: Content) -> some View {
            if active {
                content
                    .accessibilityElement(children: .combine)
                    .accessibilityIdentifier("paywall.perks")
            } else {
                content
            }
        }
    }
}

// MARK: - Product list

/// Product list. Renders the re-engagement `ForEach(products)` list or
/// the onboarding fixed three-tier toggle depending on `surface`,
/// byte-identical to the pre-extraction code. Selection is bound to the
/// shell's `selectedProductID` so the Continue / subscribe button stays
/// consistent with the chosen tier.
struct PaywallProductListView: View {
    let surface: PaywallProductsView.Surface
    @Binding var selectedProductID: String?

    @Environment(SubscriptionStore.self) private var subscriptions
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        switch surface {
        case .reengagement:
            reengagementProductList
        case .onboarding:
            onboardingTierToggle
        }
    }

    // MARK: re-engagement product list (was PaywallSheet.productList)

    private var reengagementProductList: some View {
        VStack(spacing: DesignTokens.Spacing.sm) {
            ForEach(subscriptions.products, id: \.id) { product in
                reengagementProductRow(product)
            }
            if subscriptions.products.isEmpty {
                LifeClockSpinner("Loading subscription options…", size: .regular)
                    .padding()
            }
        }
    }

    private func reengagementProductRow(_ product: Product) -> some View {
        let isSelected = product.id == selectedProductID
        return Button {
            selectedProductID = product.id
        } label: {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    HStack(spacing: DesignTokens.Spacing.sm) {
                        Text(product.displayName).font(.headline)
                        if let badge = savingsBadge(for: product) {
                            Text(badge)
                                .font(.caption.weight(.semibold))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(
                                    Color.accentColor.opacity(0.18),
                                    in: Capsule()
                                )
                                .foregroundStyle(Color.accentColor)
                                .accessibilityIdentifier("paywall.product.\(productSlug(product.id)).savings")
                        }
                    }
                    Text(periodLabel(product))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    if let equivalent = monthlyEquivalent(for: product) {
                        Text(equivalent)
                            .font(.caption2.monospacedDigit())
                            .foregroundStyle(.tertiary)
                    }
                }
                Spacer()
                Text(product.displayPrice)
                    .font(.headline.monospacedDigit())
                Image(systemName: isSelected ? "largecircle.fill.circle" : "circle")
                    .foregroundStyle(isSelected ? Color.accentColor : Color.secondary)
            }
            .padding(DesignTokens.Spacing.md)
            .background(
                RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
                    .stroke(isSelected ? Color.accentColor : Color.clear, lineWidth: 2)
                    .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
            )
            .cardLighting()
            // Smooth selection-ring transition. reduceMotion short-circuits
            // to instant per motion-spec.md § Reduce Motion.
            .animation(reduceMotion ? nil : .smooth(duration: Motion.Duration.instant), value: selectedProductID)
        }
        .buttonStyle(.plain)
    }

    /// Savings copy on annual + lifetime against the monthly baseline.
    /// Computed against shipped SKU prices in `Products.storekit`:
    /// monthly $7.99 × 12 = $95.88/yr; annual ships $49.99; lifetime $129.99.
    /// Annual saves ~48% vs monthly cadence over 12 months.
    /// Lifetime breaks even against monthly at ~16 months.
    private func savingsBadge(for product: Product) -> String? {
        switch product.id {
        case PaywallProductID.annual.rawValue: return "Save ~48%"
        case PaywallProductID.lifetime.rawValue: return "Best value"
        default: return nil
        }
    }

    /// Monthly-equivalent breakdown for the annual product.
    /// $49.99 / 12 ≈ $4.17/mo.
    private func monthlyEquivalent(for product: Product) -> String? {
        guard product.id == PaywallProductID.annual.rawValue else { return nil }
        let monthly = NSDecimalNumber(decimal: product.price / 12)
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = product.priceFormatStyle.currencyCode
        formatter.maximumFractionDigits = 2
        formatter.minimumFractionDigits = 2
        guard let formatted = formatter.string(from: monthly) else { return nil }
        return "\(formatted) / month equivalent"
    }

    private func productSlug(_ id: String) -> String {
        if id == PaywallProductID.annual.rawValue { return "annual" }
        if id == PaywallProductID.monthly.rawValue { return "monthly" }
        if id == PaywallProductID.lifetime.rawValue { return "lifetime" }
        return "unknown"
    }

    private func periodLabel(_ product: Product) -> String {
        switch product.id {
        case PaywallProductID.annual.rawValue: return "Auto-renews yearly"
        case PaywallProductID.monthly.rawValue: return "Auto-renews monthly"
        case PaywallProductID.lifetime.rawValue: return "One-time purchase"
        default: return ""
        }
    }

    // MARK: onboarding tier toggle (was PaywallPrimaryView.tierToggle)

    private enum Tier: CaseIterable {
        case annual, monthly, lifetime
        var productID: PaywallProductID {
            switch self {
            case .annual: return .annual
            case .monthly: return .monthly
            case .lifetime: return .lifetime
            }
        }
    }

    private var onboardingTierToggle: some View {
        VStack(spacing: 8) {
            onboardingTierRow(
                tier: .annual,
                title: "Yearly",
                primaryPrice: onboardingPriceString(for: .annual),
                secondaryPrice: onboardingPerMonthEquivalent()
            )
            onboardingTierRow(
                tier: .lifetime,
                title: "Lifetime",
                primaryPrice: onboardingPriceString(for: .lifetime),
                secondaryPrice: "One-time purchase"
            )
            onboardingTierRow(
                tier: .monthly,
                title: "Monthly",
                primaryPrice: onboardingPriceString(for: .monthly),
                secondaryPrice: nil
            )
        }
    }

    @ViewBuilder
    private func onboardingTierRow(
        tier: Tier,
        title: String,
        primaryPrice: String,
        secondaryPrice: String?
    ) -> some View {
        let isSelected = selectedProductID == tier.productID.rawValue
        Button { selectedProductID = tier.productID.rawValue } label: {
            HStack(alignment: .center) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(title).font(.body.bold())
                    if let secondaryPrice {
                        Text(secondaryPrice).font(.caption).foregroundStyle(.secondary)
                    }
                }
                Spacer()
                Text(primaryPrice).font(.title3.bold())
                if isSelected {
                    Image(systemName: "checkmark.circle.fill").foregroundStyle(.tint)
                } else {
                    Image(systemName: "circle").foregroundStyle(.tertiary)
                }
            }
            .padding()
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier(onboardingTierAccessibilityID(for: tier))
    }

    private func onboardingTierAccessibilityID(for tier: Tier) -> String {
        switch tier {
        case .annual: return "paywall.tier.annual"
        case .monthly: return "paywall.tier.monthly"
        case .lifetime: return "paywall.tier.lifetime"
        }
    }

    private func onboardingProduct(for tier: Tier) -> Product? {
        subscriptions.products.first { $0.id == tier.productID.rawValue }
    }

    private func onboardingPriceString(for tier: Tier) -> String {
        if let displayPrice = onboardingProduct(for: tier)?.displayPrice {
            return displayPrice
        }
        switch tier {
        case .annual: return "$49.99 / yr"
        case .monthly: return "$7.99 / mo"
        case .lifetime: return "$129.99"
        }
    }

    private func onboardingPerMonthEquivalent() -> String? {
        guard let annual = onboardingProduct(for: .annual) else {
            return "≈ $4.17 / mo equivalent"
        }
        let monthly = NSDecimalNumber(decimal: annual.price).doubleValue / 12
        return String(format: "≈ $%.2f / mo equivalent", monthly)
    }
}
