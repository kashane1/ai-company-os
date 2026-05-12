import SwiftUI

/// Six-dimension what-if slider. Pro-only.
///
/// V1.7.0 — Future tab plan §Phase 4. Free users see all six rows
/// rendered with their personal-current values, but slider thumbs
/// are dim (opacity 0.35) and locked. Tap on a locked slider track
/// presents `PaywallSheet(scrollTo: .whatIfSimulator)`.
///
/// Performance gates (per plan §Phase 4 — all wired through
/// `LifeClockStore`'s scrub state machine):
///  * `beginScrub()` memoizes 14-day baseline aggregates on
///    scrub-start; reused for every onChange tick.
///  * `endScrub()` debounce-clears the cache 250ms after touch-end
///    so rapid re-grabs reuse it.
///  * `pendingRefreshCount` coalesces HK refresh ticks during a
///    scrub; flush is exactly-one on touch-end.
///  * Slider opacity 0.35 + `.disabled(true)` for Free; tap on the
///    row routes to `onLockedTap`.
///  * `highPriorityGesture` on the active slider keeps parent
///    ScrollView from stealing drags.
///
/// View binds to `store.sliderOverrides` via @Observable — no
/// view-local `@State` for the overrides themselves.
struct WhatIfSlider: View {
    /// Personal-current 14-day aggregates. Sliders' resting position.
    let baseAggregates: [HealthspanEngine.Dimension: Double]

    /// Pro entitlement state. Free users see dim, locked thumbs.
    let isPro: Bool

    /// Store reference — slider writes overrides + scrub state here
    /// so cached aggregates + animation gating + refresh coalesce
    /// live in one place (per plan §Phase 4 architecture-strategist
    /// finding: orchestration must not leak into Views).
    let store: LifeClockStore

    /// Fired when the user taps a locked slider track (Free state).
    let onLockedTap: () -> Void

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
        let value = store.sliderOverrides[row.dim] ?? anchor

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
                        store.setSliderOverride(row.dim, value: newValue)
                        TelemetryRecorder.shared.emit(.futureSliderScrubbed(dimension: row.dim))
                    }
                ),
                in: row.range,
                step: row.step,
                onEditingChanged: { editing in
                    guard isPro else { return }
                    if editing {
                        // Captures aggregates once per active scrub;
                        // multi-touch supported via the counter.
                        store.beginScrub()
                    } else {
                        // Snap-back per brainstorm decision. clear
                        // BEFORE endScrub so chart shows snap-back
                        // animation; endScrub then flushes pending
                        // refresh + debounce-clears aggregates.
                        store.clearSliderOverrides()
                        store.endScrub()
                    }
                }
            )
            .opacity(isPro ? 1.0 : 0.35)
            .disabled(!isPro)
            .allowsHitTesting(isPro)
            // Parent ScrollView doesn't steal drags from the active
            // slider thumb. No-op in the Free state (slider already
            // disabled).
            .highPriorityGesture(
                isPro ? DragGesture(minimumDistance: 0) : nil,
                including: .gesture
            )
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
