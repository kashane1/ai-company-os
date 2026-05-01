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

            ClockHandView(signedMinutes: signedMinutes, duration: animationDuration)

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

            Spacer()

            Button(action: onDismiss) {
                Text(toneMode.wrapUpDismissCTA)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, DesignTokens.Spacing.xs)
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.bottom, DesignTokens.Spacing.lg)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
        .interactiveDismissDisabled(false)
    }

    private var deltaColor: Color {
        if signedMinutes > 0 { return DesignTokens.Palette.positive }
        if signedMinutes < 0 { return DesignTokens.Palette.negative }
        return .secondary
    }
}
