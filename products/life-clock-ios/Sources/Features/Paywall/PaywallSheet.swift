import SwiftUI
import StoreKit

/// Three-tier paywall (annual / monthly / lifetime). Annual is pre-selected
/// because RevenueCat 2026 benchmarks show materially better retention on
/// annual plans (see `MONETIZATION.md` § Recommendation, [S2]).
///
/// Always shows price + period, "auto-renews" disclosure, restore, ToS, and
/// privacy links — App Review § 3.1.2 requirements.
struct PaywallSheet: View {
    @Environment(SubscriptionStore.self) private var subscriptions
    @Environment(\.dismiss) private var dismiss
    @State private var selectedProductID: String?
    @State private var purchaseSuccessHapticTrigger: Int = 0
    @State private var restoring: Bool = false
    @State private var restoreEmptyMessageVisible: Bool = false

    private var termsURL: URL { LifeClockConfiguration.termsOfUseURL }
    private var privacyURL: URL { LifeClockConfiguration.privacyPolicyURL }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    header
                    productList
                    subscribeButton
                    fineprint
                    DisclaimerBanner()
                }
                .padding(DesignTokens.Spacing.lg)
            }
            .navigationTitle(LifeClockConfiguration.proName)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                        .accessibilityIdentifier("paywall.close")
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await runRestore() }
                    } label: {
                        if restoring {
                            ProgressView()
                        } else {
                            Text("Restore")
                        }
                    }
                    .disabled(restoring)
                    .accessibilityIdentifier("paywall.restore")
                }
            }
            .accessibilityIdentifier("paywall.screen")
        }
        // ScrollView eats drag-to-dismiss from inside content, so without
        // a visible drag indicator the only dismissal affordance is the
        // Close button. App Store reviewers expect system swipe-down to
        // work — caught 2026-05-10 gestural final-check.
        .presentationDragIndicator(.visible)
        .task {
            await subscriptions.loadProducts()
            // Pre-select annual when available.
            if selectedProductID == nil {
                selectedProductID = subscriptions.products
                    .first(where: { $0.id == PaywallProductID.annual.rawValue })?.id
                    ?? subscriptions.products.first?.id
            }
        }
        .onChange(of: subscriptions.isPro) { _, newValue in
            if newValue {
                purchaseSuccessHapticTrigger &+= 1
                dismiss()
            }
        }
        .sensoryFeedback(LifeClockHaptics.purchaseSuccess, trigger: purchaseSuccessHapticTrigger)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Unlock the full Life Clock")
                .font(.title.bold())
            Text("Full weekly reports, tailored action plans, and deeper trend breakdowns. Your free experience keeps working either way.")
                .foregroundStyle(.secondary)
        }
    }

    private var productList: some View {
        VStack(spacing: DesignTokens.Spacing.sm) {
            ForEach(subscriptions.products, id: \.id) { product in
                productRow(product)
            }
            if subscriptions.products.isEmpty {
                Text("Loading subscription options…")
                    .foregroundStyle(.secondary)
                    .padding()
            }
        }
    }

    private func productRow(_ product: Product) -> some View {
        let isSelected = product.id == selectedProductID
        return Button {
            selectedProductID = product.id
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    Text(product.displayName).font(.headline)
                    Text(periodLabel(product))
                        .font(.caption)
                        .foregroundStyle(.secondary)
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
        }
        .buttonStyle(.plain)
    }

    private func periodLabel(_ product: Product) -> String {
        switch product.id {
        case PaywallProductID.annual.rawValue: return "Auto-renews yearly"
        case PaywallProductID.monthly.rawValue: return "Auto-renews monthly"
        case PaywallProductID.lifetime.rawValue: return "One-time purchase"
        default: return ""
        }
    }

    private var subscribeButton: some View {
        Button {
            guard
                let id = selectedProductID,
                let product = subscriptions.products.first(where: { $0.id == id })
            else { return }
            Task { await subscriptions.purchase(product) }
        } label: {
            HStack {
                if subscriptions.purchaseInFlight {
                    ProgressView()
                } else {
                    Text("Continue")
                        .font(.headline)
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, DesignTokens.Spacing.sm)
        }
        .buttonStyle(.borderedProminent)
        .disabled(selectedProductID == nil || subscriptions.purchaseInFlight)
    }

    private var fineprint: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text("Subscriptions auto-renew until cancelled in iOS Settings → [your name] → Subscriptions. Cancel any time.")
                .font(.caption2)
                .foregroundStyle(.secondary)
            HStack(spacing: DesignTokens.Spacing.md) {
                Link("Terms of Use", destination: termsURL)
                Link("Privacy Policy", destination: privacyURL)
            }
            .font(.caption2)

            if let error = subscriptions.lastError {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
            } else if restoreEmptyMessageVisible {
                Text("No prior purchases were found on this Apple ID.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("paywall.restoreEmpty")
            }
        }
    }

    /// Restore + a small UX layer: spinner, disabled-while-running, and a
    /// "nothing to restore" hint when the call succeeds without granting
    /// entitlements. The sheet auto-dismisses on isPro flip via the
    /// existing onChange, so a successful restore needs no extra path.
    private func runRestore() async {
        restoring = true
        restoreEmptyMessageVisible = false
        await subscriptions.clearLastError()
        await subscriptions.restore()
        restoring = false
        if subscriptions.lastError == nil && !subscriptions.isPro {
            restoreEmptyMessageVisible = true
        }
    }
}
