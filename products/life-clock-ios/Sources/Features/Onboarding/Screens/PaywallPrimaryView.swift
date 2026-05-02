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

    enum Tier {
        case annual, monthly
        var productID: PaywallProductID {
            switch self {
            case .annual: return .annual
            case .monthly: return .monthly
            }
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack {
                Spacer()
                Button(action: onClose) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
                .accessibilityIdentifier("paywall.close")
            }
            VStack(alignment: .leading, spacing: 8) {
                Text("Lock in your clock.")
                    .font(.largeTitle.bold())
                Text("Unlock full history, weekly drivers, and every wrap-up.")
                    .font(.body)
                    .foregroundStyle(.secondary)
            }

            tierToggle()

            Spacer()

            // Auto-renewal terms ALWAYS visible per Apple 3.1.2(c).
            Text("Subscription renews automatically. Cancel anytime in Settings.")
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

            Button("Restore") {
                Task { await subscriptions.refreshEntitlements() }
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .padding(24)
        .accessibilityIdentifier("onboarding.paywallPrimary")
        .onAppear {
            telemetry.value.paywallShown(stage: .primary)
            Task { await subscriptions.loadProducts() }
        }
        .onChange(of: subscriptions.isPro) { _, isPro in
            if isPro {
                telemetry.value.paywallDismissed(stage: .primary, reason: .purchasedSuccessfully)
                onClose()
            }
        }
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
        .accessibilityIdentifier("paywall.tier.\(tier == .annual ? "annual" : "monthly")")
    }

    private func product(for tier: Tier) -> Product? {
        subscriptions.products.first { $0.id == tier.productID.rawValue }
    }

    private func priceString(for tier: Tier) -> String {
        product(for: tier)?.displayPrice ??
            (tier == .annual ? "$59.99 / yr" : "$5.99 / mo")
    }

    private func perMonthEquivalent() -> String? {
        guard let annual = product(for: .annual) else {
            return "≈ $5.00 / mo equivalent"
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
