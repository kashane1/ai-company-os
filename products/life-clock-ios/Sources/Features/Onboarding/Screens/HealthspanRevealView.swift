import SwiftUI

/// Replaces the former `lifeGridRemaining` + `bigNumberPenalty` dot-grid
/// pair (deprecated 2026-05-14). One slider-based reveal screen:
///
/// 1. The user's projected healthspan (big number)
/// 2. Five pinned sliders showing where their answers placed them on
///    each lever (Sleep, Movement, Food, Drinking, Stress recovery)
///
/// The sliders are read-only here — they animate in one-by-one on appear
/// so the user reads the picture being drawn. The interactive dial on
/// the next screen (`engineRevealAndDial`) lets them fine-tune the
/// final number.
///
/// **Why sliders instead of dot grids:** the lead-in `ReactiveSliderView`
/// established the mental model ("drag → number moves"). Closing the
/// loop with the same visual — but now pinned to the user's actual
/// answers — creates structural symmetry: the lead-in slider is the
/// generic mockup, this slider is *theirs*. The dot-grid screens
/// asserted loss; the slider screen *shows* causation.
struct HealthspanRevealView: View {
    let onContinue: () -> Void

    @Environment(LifeClockStore.self) private var store
    @Environment(OnboardingDraft.self) private var draft
    @Environment(OnboardingTelemetryHolder.self) private var telemetry
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// Per-row reveal stage. We render every row in the final layout
    /// from the first frame (no layout shifts) but animate opacity +
    /// scale in sequence so the user reads the picture being drawn.
    /// `visibleRows == leverOrder.count` ⇒ all revealed.
    @State private var visibleRows: Int = 0

    /// Live driver positions, materialized once on appear. Reading
    /// `draft` every body invocation would recompute the engine pass
    /// per layout pass during animation; cache once.
    @State private var positions: [LifeClockLever: Double] = [:]

    /// Projected healthspan in years, computed on appear from the same
    /// engine pass that drives the dial screen.
    @State private var projectedYears: Double = 0

    /// Stable display order for the lever rows. Sleep first because it's
    /// the most-discussed lever in everyday language; movement next
    /// because Apple Health surfaces it; stress recovery last because
    /// it's the most internal/sensitive.
    private static let leverOrder: [LifeClockLever] = [
        .sleep, .movement, .food, .drinking, .stressRecovery,
    ]

    private var tone: ToneMode {
        draft.toneMode ?? .coach
    }

    private var softened: Bool {
        revealUsesSofterRegister(draft: draft)
    }

    var body: some View {
        OnboardingScaffold(
            screenID: "healthspanReveal",
            title: RevealCopy.healthspanRevealTitle(tone: tone, softened: softened),
            bodyText: RevealCopy.healthspanRevealCaption(tone: tone),
            onContinue: onContinue
        ) {
            // Content is dense — the big number + 5 sliders + captions
            // stack taller than the scaffold's available space on smaller
            // devices, clipping the Continue button. Wrap the inner stack
            // in a ScrollView so the user can reach Continue while still
            // seeing the lead-in number anchor.
            ScrollView(showsIndicators: false) {
                VStack(spacing: 14) {
                    Text(String(format: "%.0f years", projectedYears))
                        .font(.system(size: 48, weight: .semibold, design: .rounded))
                        .contentTransition(.numericText(value: projectedYears))
                        .frame(maxWidth: .infinity)
                        .accessibilityIdentifier("onboarding.healthspanReveal.years")

                    VStack(spacing: 12) {
                        ForEach(Array(Self.leverOrder.enumerated()), id: \.element) { idx, lever in
                            leverRow(lever: lever, position: positions[lever] ?? 0.5)
                                .opacity(idx < visibleRows ? 1 : 0)
                                .scaleEffect(idx < visibleRows ? 1 : 0.92, anchor: .leading)
                                .animation(
                                    reduceMotion ? nil : .easeOut(duration: Motion.Duration.beat),
                                    value: visibleRows
                                )
                        }
                    }
                }
            }
        }
        .onAppear {
            let snapshot = draft.materialize()
            let engine = ClockEngine(clock: store.clock)
            projectedYears = engine.calculateBaseline(profile: snapshot).projectedAgeYears
            positions = engine.normalizedDriverPositions(profile: snapshot)
            telemetry.value.screenAppeared("healthspanReveal")
            revealRowsInSequence()
        }
    }

    /// Stagger the row reveals so the user reads the picture being
    /// drawn. Total animation ≤ 1.2s, well inside the perceived "instant"
    /// budget for a Continue-gated screen. Reduce Motion ⇒ all rows
    /// visible immediately.
    private func revealRowsInSequence() {
        if reduceMotion {
            visibleRows = Self.leverOrder.count
            return
        }
        for idx in 0..<Self.leverOrder.count {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.18 * Double(idx + 1)) {
                visibleRows = idx + 1
            }
        }
    }

    @ViewBuilder
    private func leverRow(lever: LifeClockLever, position: Double) -> some View {
        let binding = Binding<Double>(
            get: { position },
            set: { _ in /* pinned — drag is disabled, setter is a no-op */ }
        )
        LifeClockSliderRow(
            label: lever.displayName,
            leadingExtremeLabel: leadingExtremeLabel(for: lever),
            trailingExtremeLabel: trailingExtremeLabel(for: lever),
            value: binding,
            mode: .pinned,
            identifierSuffix: "healthspanReveal.\(lever.rawValue)",
            caption: caption(for: lever, position: position)
        )
    }

    /// Sub-line under each pinned slider — names what specifically the
    /// user told us. Tone-aware where it matters. Empty when the user
    /// skipped (position = 0.5) so the row doesn't fabricate insight.
    private func caption(for lever: LifeClockLever, position: Double) -> String? {
        if !hasSignal(for: lever) {
            return tone == .firmDirect
                ? "Not answered."
                : "You didn't answer this one."
        }
        let band: String
        switch position {
        case ..<0.34: band = "lower"
        case 0.34..<0.67: band = "middle"
        default: band = "upper"
        }
        switch tone {
        case .gentle:     return "Your answers put you in the \(band) band."
        case .coach:      return "You're in the \(band) band."
        case .firmDirect: return "\(band.capitalized) band."
        }
    }

    /// Whether the user actually answered the inputs that feed this
    /// lever. Drives whether we render a "you didn't answer" caption
    /// instead of pretending to interpret the neutral 0.5 midpoint.
    private func hasSignal(for lever: LifeClockLever) -> Bool {
        switch lever {
        case .sleep:
            return draft.sleepGoalHours != nil
        case .movement:
            return draft.cardioMinsPerWeek != nil
                || draft.strengthFrequencyPerWeek != nil
        case .food:
            return draft.dietQualityBaseline != nil
        case .drinking:
            return draft.alcoholFrequency != nil
        case .stressRecovery:
            return draft.perceivedStressScore != nil
                || draft.lonelinessScore != nil
        case .unanswered:
            return false
        }
    }

    private func leadingExtremeLabel(for lever: LifeClockLever) -> String {
        switch lever {
        case .sleep: return "Short"
        case .movement: return "Sedentary"
        case .food: return "Rough"
        case .drinking: return "Heavy"
        case .stressRecovery: return "Stretched"
        case .unanswered: return ""
        }
    }

    private func trailingExtremeLabel(for lever: LifeClockLever) -> String {
        switch lever {
        case .sleep: return "Rested"
        case .movement: return "Active"
        case .food: return "Whole foods"
        case .drinking: return "Rare"
        case .stressRecovery: return "Steady"
        case .unanswered: return ""
        }
    }
}
