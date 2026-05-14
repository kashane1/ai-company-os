import SwiftUI

/// First-open ceremonial moment hosting the clock-hand animation, the signed
/// minute readout, and a tone-aware body line. Presented by `LifeClockApp` as
/// a `.sheet` with medium/large detents.
///
/// On dismiss, the parent calls `LifeClockStore.markWrapUpShown(_:)` which
/// advances `lastShownYesterdayWrapUpDay` / `lastShownWeeklyWrapUpWeek` and
/// clears `pendingWrapUp` so the sheet does not re-present the same day.
struct WrapUpSheet: View {
    let wrapUp: WrapUpCoordinator.PendingWrapUp
    let signedMinutes: Int
    let toneMode: ToneMode
    let onDismiss: () -> Void

    @Environment(SubscriptionStore.self) private var subscriptions
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var paywallPresented: Bool = false
    @State private var proSignalRevealed: Bool = false

    /// Free + weekly-variant gate per `wrap-up-spec.md` § "Pro signal".
    /// Yesterday wrap-ups never show the signal; Pro users never see it.
    private var showsProSignal: Bool {
        guard case .weekly = wrapUp else { return false }
        return !subscriptions.isPro
    }

    private var heading: String {
        switch wrapUp {
        case .yesterday: return toneMode.yesterdayWrapUpHeading
        case .weekly: return toneMode.weeklyWrapUpHeading
        }
    }

    private var body_: String {
        if signedMinutes > 0 {
            return toneMode.wrapUpPositiveBody(minutes: signedMinutes)
        } else if signedMinutes < 0 {
            return toneMode.wrapUpNegativeBody(minutes: signedMinutes)
        } else {
            return toneMode.wrapUpZeroBody
        }
    }

    private var animationDuration: Double {
        switch wrapUp {
        case .yesterday: return 1.4
        case .weekly: return 2.2
        }
    }

    var body: some View {
        VStack(spacing: DesignTokens.Spacing.lg) {
            Text(heading)
                .font(.title3)
                .foregroundStyle(.secondary)
                .padding(.top, DesignTokens.Spacing.lg)
                .accessibilityIdentifier("wrapup.heading")

            ClockHandView(
                signedMinutes: signedMinutes,
                duration: animationDuration,
                haptic: LifeClockHaptics.wrapUp(signedMinutes: signedMinutes)
            )

            Text(TimeDeltaFormatter.format(minutes: signedMinutes))
                .font(.system(size: 44, weight: .semibold, design: .rounded))
                .foregroundStyle(deltaColor)
                .accessibilityHidden(true)  // Already announced by ClockHandView

            Text(body_)
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .readableColumn()
                .padding(.horizontal, DesignTokens.Spacing.lg)

            if showsProSignal && proSignalRevealed {
                proSignalRow
                    .transition(.opacity.combined(with: .move(edge: .bottom)))
                    .padding(.horizontal, DesignTokens.Spacing.lg)
            }

            Spacer()

            Button(action: onDismiss) {
                Text(toneMode.wrapUpDismissCTA)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, DesignTokens.Spacing.xs)
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.bottom, DesignTokens.Spacing.lg)
            .accessibilityIdentifier("wrapup.dismissCTA")
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        // `.contain` keeps child identifiers (heading, dismissCTA) addressable
        // while still exposing the kind identifier on the container element.
        // Without this, the kind id propagates down and overwrites
        // wrapup.dismissCTA on the inner Button.
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier(wrapUpKindIdentifier)
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
        .interactiveDismissDisabled(false)
        .task {
            // Reveal the Pro signal AFTER the ceremony animation lands.
            // The ceremony itself has primacy — see wrap-up-spec.md § "Pro
            // signal (Free-side)". Yesterday is 1.4s, weekly is 2.2s; we
            // add a 0.4s settle on top before the signal fades in.
            guard showsProSignal else { return }
            try? await Task.sleep(nanoseconds: UInt64((animationDuration + 0.4) * 1_000_000_000))
            // Reduce Motion short-circuits to an instant reveal — the
            // signal still appears (no functional regression) but
            // without the fade-in.
            if reduceMotion {
                proSignalRevealed = true
            } else {
                withAnimation(.smooth(duration: Motion.Duration.beat)) {
                    proSignalRevealed = true
                }
            }
        }
        .sheet(isPresented: $paywallPresented) {
            PaywallSheet(scrollTo: .top)
                .environment(subscriptions)
        }
    }

    /// Single-row, non-intrusive Pro signal. Tone-aware copy via
    /// `ToneMode.weeklyWrapUpProSignalTitle / Body`. Tap routes to
    /// `PaywallSheet(scrollTo: .top)`. The row never appears on yesterday
    /// wrap-ups (daily reflection ≠ upsell moment) or for active-Pro
    /// users (would be redundant).
    private var proSignalRow: some View {
        Button {
            paywallPresented = true
        } label: {
            HStack(alignment: .firstTextBaseline, spacing: DesignTokens.Spacing.sm) {
                Image(systemName: "sparkles")
                    .foregroundStyle(.tint)
                    .font(.subheadline)
                VStack(alignment: .leading, spacing: 2) {
                    Text(toneMode.weeklyWrapUpProSignalTitle)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                    Text(toneMode.weeklyWrapUpProSignalBody)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.leading)
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
            .padding(DesignTokens.Spacing.md)
            .background(
                DesignTokens.Palette.elevated,
                in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
            )
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("wrapup.proSignal")
    }

    /// Stable id distinguishing yesterday vs weekly so XCUITest can wait on
    /// the right sheet during sequencing checks.
    private var wrapUpKindIdentifier: String {
        switch wrapUp {
        case .yesterday: return "wrapup.sheet.yesterday"
        case .weekly: return "wrapup.sheet.weekly"
        }
    }

    private var deltaColor: Color {
        if signedMinutes > 0 { return DesignTokens.Palette.positive }
        if signedMinutes < 0 { return DesignTokens.Palette.negative }
        return .secondary
    }
}
