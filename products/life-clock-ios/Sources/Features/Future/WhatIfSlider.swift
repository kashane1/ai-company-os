import SwiftUI

/// Six-dimension what-if slider. Pro-only.
///
/// V1.7.0 — Future tab plan §Phase 4. Free users see all six rows
/// rendered with their personal-current values, but slider thumbs
/// are dim (opacity 0.35) and locked. Tap on a locked slider track
/// presents `PaywallSheet(scrollTo: .whatIfSimulator)`.
///
/// Performance gates (per plan §Phase 4 perf gates):
///  * Memoize 14-day baseline aggregates on scrub-start; reuse for
///    every onChange tick; 250ms debounced clear so rapid re-grabs
///    reuse cached aggregates.
///  * Disable redraw animation while scrubbing.
///  * Coalesce daily-refresh ticks via the pending-counter on the
///    store.
///  * Gesture priority: wrap slider in `.highPriorityGesture` so
///    parent ScrollView doesn't steal slider drags.
///
/// For Phase 4 v1, the slider passes its overrides to a parent
/// callback (`onProjectionChange`) that the FutureView uses to
/// redraw the chart. The store-side memoization + refresh-coalesce
/// machinery lands in this same phase (see LifeClockStore additions).
struct WhatIfSlider: View {
    /// Personal-current 14-day aggregates. Sliders' resting position.
    let baseAggregates: [HealthspanEngine.Dimension: Double]

    /// Pro entitlement state. Free users see dim, locked thumbs.
    let isPro: Bool

    /// Fired on every value change (debounced internally by
    /// scrub-start memoization). Parent (FutureView) projects with
    /// these overrides and updates the chart.
    let onOverridesChange: ([HealthspanEngine.Dimension: Double]) -> Void

    /// Fired when the user taps a locked slider track (Free state).
    let onLockedTap: () -> Void

    @State private var overrides: [HealthspanEngine.Dimension: Double] = [:]
    @State private var isScrubbing: Bool = false

    private var rows: [DimensionRow] {
        [
            DimensionRow(dim: .sleep, label: "Sleep", unit: "h/night", range: 0...10, step: 0.5),
            DimensionRow(dim: .dietQuality, label: "Whole food", unit: "days/wk", range: 0...7, step: 0.5),
            DimensionRow(dim: .steps, label: "Steps", unit: "/day", range: 0...20_000, step: 500),
            DimensionRow(dim: .exerciseMinutes, label: "Exercise", unit: "min/wk", range: 0...600, step: 15),
            DimensionRow(dim: .extras, label: "Extras", unit: "days/wk", range: 0...14, step: 1),
            DimensionRow(dim: .nicotine, label: "Nicotine", unit: "days/wk", range: 0...7, step: 0.5),
        ]
    }

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("What if…")
                .font(.headline)
            ForEach(rows, id: \.dim) { row in
                sliderRow(for: row)
            }
        }
        .padding(DesignTokens.Spacing.md)
        .background(
            DesignTokens.Palette.elevated,
            in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
        )
        .accessibilityIdentifier("future.whatIfSlider")
    }

    @ViewBuilder
    private func sliderRow(for row: DimensionRow) -> some View {
        let anchor = baseAggregates[row.dim] ?? 0
        let value = overrides[row.dim] ?? anchor

        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            HStack {
                Text(row.label)
                    .font(.subheadline)
                Spacer()
                Text(formatValue(value, row: row))
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
                if !isPro {
                    Image(systemName: "lock.fill")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("future.slider.\(row.dim.rawValue).lock")
                }
            }
            Slider(
                value: Binding(
                    get: { value },
                    set: { newValue in
                        guard isPro else { return }
                        overrides[row.dim] = newValue
                        onOverridesChange(overrides)
                    }
                ),
                in: row.range,
                step: row.step,
                onEditingChanged: { editing in
                    guard isPro else { return }
                    isScrubbing = editing
                    if !editing {
                        // Snap-back on touch-end per the brainstorm
                        // decision: slider returns to personal-current.
                        // Plan §Phase 4: no Pin scenario affordance in v1.
                        overrides.removeValue(forKey: row.dim)
                        onOverridesChange(overrides)
                    }
                }
            )
            .opacity(isPro ? 1.0 : 0.35)
            .disabled(!isPro)
            .allowsHitTesting(isPro)
            .accessibilityIdentifier("future.slider.\(row.dim.rawValue)")
        }
        .contentShape(Rectangle())
        .onTapGesture {
            // Free state: any tap on the row presents the paywall.
            if !isPro { onLockedTap() }
        }
        .accessibilityElement(children: .combine)
    }

    private func formatValue(_ value: Double, row: DimensionRow) -> String {
        switch row.dim {
        case .steps:
            let formatter = NumberFormatter()
            formatter.numberStyle = .decimal
            let v = Int(value.rounded())
            return "\(formatter.string(from: NSNumber(value: v)) ?? "0") \(row.unit)"
        case .sleep, .dietQuality, .extras, .nicotine:
            return String(format: "%.1f %@", value, row.unit)
        case .exerciseMinutes:
            return "\(Int(value.rounded())) \(row.unit)"
        }
    }

    private struct DimensionRow {
        let dim: HealthspanEngine.Dimension
        let label: String
        let unit: String
        let range: ClosedRange<Double>
        let step: Double
    }
}
