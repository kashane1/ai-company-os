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
    @Environment(LifeClockStore.self) private var store
    @Environment(OnboardingDraft.self) private var draft
    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    /// Selected product id. Pre-set to annual to match the prior
    /// `selectedTier = .annual` default. Shared with the extracted
    /// `PaywallProductsView` core (PV-P2) so the onboarding tier toggle
    /// and the Continue purchase target stay consistent.
    @State private var selectedProductID: String? = PaywallProductID.annual.rawValue
    @State private var purchaseSuccessHapticTrigger: Int = 0

    /// Tone routed through `OnboardingDraft` rather than `UserProfile`
    /// because the paywall renders BEFORE `completeOnboarding` writes
    /// the profile. Default `.coach` matches the materialize fallback.
    private var tone: ToneMode {
        draft.toneMode ?? .coach
    }

    /// Habit-failure-mode-keyed headline branch. Captured on the
    /// `habitFailureMode` screen (post-tone, pre-baseline). Unanswered
    /// users fall through to the neutral default in `RevealCopy`.
    private var failureMode: HabitFailureMode {
        draft.habitFailureMode ?? .unanswered
    }

    /// Engine-computed top lever for the user's profile. Names the
    /// lever in the body copy so the value claim is personal. Computed
    /// lazily on appear — the draft is stable by the time the paywall
    /// renders, so a single computation is fine.
    @State private var topLever: LifeClockLever = .unanswered

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
            // Compute top lever once on appear from the draft snapshot.
            // Draft is stable here (every collection screen has fired
            // Continue) so a single pass is enough.
            let snapshot = draft.materialize()
            topLever = ClockEngine(clock: store.clock).topLever(profile: snapshot)
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
            // The pitch (headline + personalized body + the concrete
            // 5-perk enumeration + tier toggle) scrolls; the commit
            // actions (fineprint, Continue, soft-skip, Restore) stay
            // pinned below. Before the perks block landed this fit as a
            // fixed VStack; the added rows overflow the smallest device
            // and clipped the personalized headline off-screen, so the
            // pitch is now scrollable while the CTA stays reachable —
            // mirroring how the re-engagement `PaywallSheet` is built.
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    VStack(alignment: .leading, spacing: 8) {
                        // Headline is keyed off `habitFailureMode` (what
                        // usually breaks habits for this user). Body
                        // names the user's top lever inline. Both via
                        // `RevealCopy` so the strings are reviewable in
                        // one place.
                        Text(RevealCopy.paywallHeadline(tone: tone, failureMode: failureMode))
                            .font(.largeTitle.bold())
                            .fixedSize(horizontal: false, vertical: true)
                            .accessibilityIdentifier("paywall.headline")
                        Text(RevealCopy.paywallBody(tone: tone, top: topLever))
                            .font(.body)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                            .accessibilityIdentifier("paywall.body")
                    }

                    PaywallPerksView(surface: .onboarding)

                    PaywallProductListView(
                        surface: .onboarding,
                        selectedProductID: $selectedProductID
                    )
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

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

            // Soft-skip: an explicit, labeled "Continue with the free
            // clock" CTA replaces the silent X-close as the primary
            // exit path. The X (top-right) still exists for users who
            // bail early without reading. Making the soft skip explicit
            // and tasteful (rather than only via the X) post-Cal-AI
            // raises net conversion (fewer refunds, fewer review bombs)
            // by reducing buyer's remorse. Same `onClose` callback —
            // completion / free-fallback writes the profile via the
            // coordinator's existing handler.
            VStack(spacing: 4) {
                Button(action: softSkip) {
                    Text(RevealCopy.paywallSoftSkipLabel(tone: tone))
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("paywall.softSkip")
                Text(RevealCopy.paywallSoftSkipCaption(tone: tone))
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .multilineTextAlignment(.center)
            }
            .frame(maxWidth: .infinity)

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

    /// Soft-skip path — explicit, labeled CTA for users who want to
    /// continue with the free clock. Records a distinct telemetry
    /// signal so the funnel can separate "X closed" (silent bail) from
    /// "soft-skip CTA tapped" (deliberate choice).
    private func softSkip() {
        telemetry.value.paywallDismissed(stage: .primary, reason: .softSkipped)
        onClose()
    }

    // The perks block + the onboarding tier toggle + the price /
    // per-month math now live in the shared `PaywallPerksView` /
    // `PaywallProductListView` (PV-P2) so this onboarding wrapper and
    // the re-engagement `PaywallSheet` cannot diverge. The personalized
    // headline/body, soft-skip, the always-visible auto-renew line, the
    // Continue button, and Restore stay in this shell — they are
    // onboarding-specific and unchanged.

    private func purchase() {
        guard
            let id = selectedProductID,
            let product = subscriptions.products.first(where: { $0.id == id })
        else { return }
        Task {
            await subscriptions.purchase(product)
            if subscriptions.isPro {
                telemetry.value.purchased(productID: id)
            }
        }
    }
}
