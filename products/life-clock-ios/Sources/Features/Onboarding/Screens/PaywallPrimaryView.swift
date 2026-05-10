import SwiftUI
import StoreKit

/// Single-tier end-of-onboarding paywall — Phase 6 of the rebuild plan.
/// Replaces the originally-planned two-stage paywall + "I'd rather pay
/// full price" dismissal pattern (dropped after Cal AI's April 2026
/// App Store removal documented that as a rejection vector — see
/// Enhancement Summary §1 in the plan).
///
/// **App Store-safe shape:**
/// - Annual / monthly toggle with EQUAL-prominence pricing for the
///   total amount the user will be billed (not just per-week breakdown
///   — Apple 3.1.2(c)).
/// - Auto-renewal terms always visible (not gated behind a toggle).
/// - Introductory offer auto-applied for new subscribers via App Store
///   Connect intro pricing (no JWS signing infrastructure required).
/// - No strikethrough pricing (deceptive without a real prior price).
/// - No "limited time" / countdown timer language.
///
/// **TODO Phase 6 follow-up:** wire `PaywallProductsView` shared core
/// extraction so the existing `PaywallSheet` (re-engagement from Profile
/// + History) and this onboarding wrapper share product list + restore
/// + fineprint code paths.
struct PaywallPrimaryView: View {
    let onClose: () -> Void

    @Environment(SubscriptionStore.self) private var subscriptions
    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @State private var selectedTier: Tier = .annual
    @State private var purchaseSuccessHapticTrigger: Int = 0

    enum Tier {
        case annual, monthly, lifetime
        var productID: PaywallProductID {
            switch self {
            case .annual: return .annual
            case .monthly: return .monthly
            case .lifetime: return .lifetime
            }
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Spacer()
                Button(action: onClose) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
                .accessibilityIdentifier("paywall.close")
            }
            .padding(.horizontal, 24)
            .padding(.top, 8)
            paywallBody
        }
        // `children: .contain` keeps inner identifiers (`paywall.close`,
        // `paywall.purchase`, `paywall.restore`, the per-tier ids)
        // visible to XCUITest queries. Without it, SwiftUI flattens
        // this VStack into a single accessibility element and the
        // outer screen id shadows every child — so polish recon's
        // existence wait on `onboarding.paywallPrimary` and any
        // per-button query both come up empty. OnboardingScaffold
        // applies the same modifier for the same reason.
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("onboarding.paywallPrimary")
        .onAppear {
            telemetry.value.paywallShown(stage: .primary)
            Task { await subscriptions.loadProducts() }
        }
        .onChange(of: subscriptions.isPro) { _, isPro in
            if isPro {
                purchaseSuccessHapticTrigger &+= 1
                telemetry.value.paywallDismissed(stage: .primary, reason: .purchasedSuccessfully)
                onClose()
            }
        }
        .sensoryFeedback(LifeClockHaptics.purchaseSuccess, trigger: purchaseSuccessHapticTrigger)
    }

    private var paywallBody: some View {
        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Earn time, every day.")
                    .font(.largeTitle.bold())
                Text("Pro keeps your full history, weekly drivers, and every wrap-up.")
                    .font(.body)
                    .foregroundStyle(.secondary)
            }

            tierToggle()

            Spacer()

            // Auto-renewal terms ALWAYS visible per Apple 3.1.2(c).
            // Lifetime is a non-consumable; the line covers both shapes.
            Text("Subscriptions renew automatically until cancelled in Settings. Lifetime is a one-time purchase.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity)

            Button(action: purchase) {
                Text("Continue")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.accentColor)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .accessibilityIdentifier("paywall.purchase")

            // Centered + .callout to match the soft-skip secondary slot
            // the scaffold uses on every other terminal-tier onboarding
            // screen (e.g. healthKitAuth's "Not now"). Earlier styling
            // (.caption + leading alignment) drifted away from that
            // muscle-memory pattern.
            Button("Restore") {
                Task { await subscriptions.refreshEntitlements() }
            }
            .buttonStyle(.plain)
            .font(.callout)
            .foregroundStyle(.secondary)
            .frame(maxWidth: .infinity)
            .accessibilityIdentifier("paywall.restore")
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 24)
    }

    @ViewBuilder
    private func tierToggle() -> some View {
        VStack(spacing: 8) {
            tierRow(
                tier: .annual,
                title: "Yearly",
                primaryPrice: priceString(for: .annual),
                secondaryPrice: perMonthEquivalent()
            )
            tierRow(
                tier: .lifetime,
                title: "Lifetime",
                primaryPrice: priceString(for: .lifetime),
                secondaryPrice: "One-time purchase"
            )
            tierRow(
                tier: .monthly,
                title: "Monthly",
                primaryPrice: priceString(for: .monthly),
                secondaryPrice: nil
            )
        }
    }

    @ViewBuilder
    private func tierRow(
        tier: Tier,
        title: String,
        primaryPrice: String,
        secondaryPrice: String?
    ) -> some View {
        Button { selectedTier = tier } label: {
            HStack(alignment: .center) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(title).font(.body.bold())
                    if let secondaryPrice {
                        Text(secondaryPrice).font(.caption).foregroundStyle(.secondary)
                    }
                }
                Spacer()
                Text(primaryPrice).font(.title3.bold())
                if selectedTier == tier {
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
        .accessibilityIdentifier(paywallTierAccessibilityID(for: tier))
    }

    private func paywallTierAccessibilityID(for tier: Tier) -> String {
        switch tier {
        case .annual: return "paywall.tier.annual"
        case .monthly: return "paywall.tier.monthly"
        case .lifetime: return "paywall.tier.lifetime"
        }
    }

    private func product(for tier: Tier) -> Product? {
        subscriptions.products.first { $0.id == tier.productID.rawValue }
    }

    private func priceString(for tier: Tier) -> String {
        if let displayPrice = product(for: tier)?.displayPrice {
            return displayPrice
        }
        switch tier {
        case .annual: return "$49.99 / yr"
        case .monthly: return "$7.99 / mo"
        case .lifetime: return "$129.99"
        }
    }

    private func perMonthEquivalent() -> String? {
        guard let annual = product(for: .annual) else {
            return "≈ $4.17 / mo equivalent"
        }
        let monthly = NSDecimalNumber(decimal: annual.price).doubleValue / 12
        return String(format: "≈ $%.2f / mo equivalent", monthly)
    }

    private func purchase() {
        guard let product = product(for: selectedTier) else { return }
        Task {
            await subscriptions.purchase(product)
            if subscriptions.isPro {
                telemetry.value.purchased(productID: selectedTier.productID.rawValue)
            }
        }
    }
}
