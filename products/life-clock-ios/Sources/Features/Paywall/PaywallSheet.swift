import SwiftUI
import StoreKit

/// Three-tier paywall (annual / monthly / lifetime). Annual is pre-selected
/// because RevenueCat 2026 benchmarks show materially better retention on
/// annual plans (see `MONETIZATION.md` § Recommendation, [S2]).
///
/// Always shows price + period, "auto-renews" disclosure, restore, ToS, and
/// privacy links — App Review § 3.1.2 requirements.
struct PaywallSheet: View {
    /// Named scroll-to anchors. V1.7.0 (Future tab plan §Phase 4):
    /// the Future tab's slider locks present `PaywallSheet(scrollTo:
    /// .whatIfSimulator)` so the user lands directly on the
    /// simulator section instead of scrolling past the generic
    /// header. Default nil preserves existing behavior — every other
    /// call site continues to land at the top.
    enum Section: String, Hashable {
        case top
        case whatIfSimulator
        case restore
    }

    let scrollTo: Section?

    @Environment(SubscriptionStore.self) private var subscriptions
    @Environment(\.dismiss) private var dismiss
    @State private var selectedProductID: String?
    @State private var purchaseSuccessHapticTrigger: Int = 0
    @State private var restoring: Bool = false
    @State private var restoreEmptyMessageVisible: Bool = false

    init(scrollTo: Section? = nil) {
        self.scrollTo = scrollTo
    }

    private var termsURL: URL { LifeClockConfiguration.termsOfUseURL }
    private var privacyURL: URL { LifeClockConfiguration.privacyPolicyURL }

    var body: some View {
        NavigationStack {
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                        header
                            .id(Section.top)
                        whatIfSimulatorTeaser
                            .id(Section.whatIfSimulator)
                        productList
                        subscribeButton
                        fineprint
                            .id(Section.restore)
                        DisclaimerBanner()
                    }
                    .padding(DesignTokens.Spacing.lg)
                }
                .onAppear {
                    guard let target = scrollTo, target != .top else { return }
                    // Defer one tick — ScrollViewReader needs the layout
                    // pass before scrollTo lands cleanly.
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) {
                        withAnimation(.smooth(duration: Motion.Duration.instant)) {
                            proxy.scrollTo(target, anchor: .top)
                        }
                    }
                }
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
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("Unlock the full Life Clock")
                .font(.title.bold())
            Text("Pro unlocks the depth Free hints at:")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                proBullet("Full daily history", detail: "every past day, drillable")
                proBullet("Weekly drivers + next-best lever", detail: "the deeper breakdown in History and richer weekly wrap-ups")
                proBullet("Correction power", detail: "override imported Apple Health values you know are wrong")
                proBullet("Custom Today's Plan", detail: "pick the daily-plan actions that fit your life")
                proBullet("Deeper trend breakdown", detail: "the Future-tab What-If Simulator")
            }
            Text("Your free experience keeps working either way.")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("paywall.header")
    }

    /// Pro-feature bullet sourced verbatim from `MONETIZATION.md` § Pro Annual.
    /// Do not edit copy here without updating MONETIZATION.md in lockstep —
    /// the App Review value-claim guard requires marketing copy to match
    /// what the app actually delivers (pro-value-backlog Prompt 2).
    private func proBullet(_ title: String, detail: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: DesignTokens.Spacing.sm) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.tint)
                .font(.footnote)
            (Text(title).fontWeight(.semibold)
                + Text(" — ")
                + Text(detail).foregroundStyle(.secondary))
            .font(.subheadline)
        }
    }

    /// V1.7.0 — the Future tab's slider tap routes here via
    /// `PaywallSheet(scrollTo: .whatIfSimulator)`. Title-case neutral
    /// (no per-tone variants); paywall copy is not tone-conditional in v1.
    private var whatIfSimulatorTeaser: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("The what-if simulator")
                .font(.title2.bold())
            Text("Drag any of six dimensions — sleep, steps, exercise, whole food, extras, nicotine — and watch your trajectory redraw in real time. Pro only.")
                .foregroundStyle(.secondary)
        }
        .padding(DesignTokens.Spacing.md)
        .background(
            DesignTokens.Palette.elevated,
            in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
        )
        .accessibilityIdentifier("paywall.whatIfSimulator")
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
