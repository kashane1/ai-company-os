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
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
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
                        PaywallProductListView(
                            surface: .reengagement,
                            selectedProductID: $selectedProductID
                        )
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
                        if reduceMotion {
                            proxy.scrollTo(target, anchor: .top)
                        } else {
                            withAnimation(.smooth(duration: Motion.Duration.instant)) {
                                proxy.scrollTo(target, anchor: .top)
                            }
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
                            LifeClockSpinner()
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
            Text("Pro adds depth:")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            // Perks block now sourced from the shared `PaywallPerksView`
            // (PV-P2) so the re-engagement sheet and the
            // onboarding-terminal paywall cannot diverge. The
            // `.reengagement` surface renders byte-identically to the
            // previous hand-rolled `proBullet` loop (same
            // `ProPerks.perks` source, same layout, no nested
            // `paywall.perks` element).
            PaywallPerksView(surface: .reengagement)
            Text("Your free experience keeps working either way.")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("paywall.header")
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
        .cardLighting()
        .accessibilityIdentifier("paywall.whatIfSimulator")
    }

    // The product list, savings badges, per-month-equivalent, period
    // labels, and product slugs now live in the shared
    // `PaywallProductsView` core (PV-P2) and are composed via
    // `core.productList`. They were byte-for-byte moved — same selection
    // semantics (`selectedProductID` binding), same strings, same
    // `paywall.product.<slug>.savings` identifiers — so the
    // re-engagement sheet renders identically to before.

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
                    LifeClockSpinner()
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
        // Restore semantics (clear-error → restore → empty-detection)
        // are owned by the shared `PaywallProductsView` core (PV-P2) so
        // they cannot diverge between surfaces. The sheet keeps its own
        // spinner / disabled / empty-hint chrome, unchanged.
        let nothingRestored = await PaywallProductsView.runReengagementRestore(subscriptions)
        restoring = false
        restoreEmptyMessageVisible = nothingRestored
    }
}
