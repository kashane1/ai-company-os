import SwiftUI

/// The new onboarding mascot — the iOS app icon clock with two states
/// (positive when the running estimate is at or above baseline, negative
/// when below). Crossfades between the two as the user's reactive estimate
/// moves during the questionnaire phase.
///
/// **Reduce Motion:** when `accessibilityReduceMotion` is on, the
/// crossfade snaps instead of animating (default SwiftUI behavior with
/// `withAnimation` not used).
///
/// **Asset slots:** `ClockMascotPositive` and `ClockMascotNegative` in
/// `Assets.xcassets`. Until the founder ships final art, these fall
/// back to SF Symbol placeholders so the views render in Previews and
/// on-device.
struct ClockMascotView: View {
    let estimate: LifeClockEstimate?
    let baseline: LifeClockEstimate?

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private enum Polarity {
        case positive, negative, neutral
    }

    private var polarity: Polarity {
        guard let e = estimate?.projectedAgeYears,
              let b = baseline?.projectedAgeYears else { return .neutral }
        let delta = e - b
        if delta > 0.25 { return .positive }
        if delta < -0.25 { return .negative }
        return .neutral
    }

    var body: some View {
        ZStack {
            mascotImage(named: "ClockMascotPositive", fallback: "clock.badge.checkmark")
                .opacity(polarity == .negative ? 0 : 1)
            mascotImage(named: "ClockMascotNegative", fallback: "clock.badge.exclamationmark")
                .opacity(polarity == .negative ? 1 : 0)
        }
        .animation(reduceMotion ? nil : .easeInOut(duration: 0.4), value: polarity)
        .accessibilityElement()
        .accessibilityLabel(accessibilityLabel)
    }

    @ViewBuilder
    private func mascotImage(named: String, fallback systemName: String) -> some View {
        if UIImage(named: named) != nil {
            Image(named)
                .resizable()
                .scaledToFit()
        } else {
            Image(systemName: systemName)
                .resizable()
                .scaledToFit()
                .foregroundStyle(systemName.contains("exclamation") ? .red : .accentColor)
        }
    }

    private var accessibilityLabel: String {
        switch polarity {
        case .positive: return "Life clock indicator — your habits are pulling the clock forward."
        case .negative: return "Life clock indicator — your habits are pulling the clock back."
        case .neutral: return "Life clock indicator."
        }
    }
}

#if DEBUG
#Preview("Positive") {
    let baseline = LifeClockEstimate(date: Date())
    baseline.projectedAgeYears = 80
    let estimate = LifeClockEstimate(date: Date())
    estimate.projectedAgeYears = 84
    return ClockMascotView(estimate: estimate, baseline: baseline)
        .frame(width: 200, height: 200)
}

#Preview("Negative") {
    let baseline = LifeClockEstimate(date: Date())
    baseline.projectedAgeYears = 80
    let estimate = LifeClockEstimate(date: Date())
    estimate.projectedAgeYears = 76
    return ClockMascotView(estimate: estimate, baseline: baseline)
        .frame(width: 200, height: 200)
}

#Preview("Neutral") {
    ClockMascotView(estimate: nil, baseline: nil)
        .frame(width: 200, height: 200)
}
#endif
