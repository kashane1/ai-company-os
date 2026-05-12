import SwiftUI

/// Free narrative line + Pro long-form narrative. Both live in one
/// file per the simplicity-review cut (was originally split across
/// Phase 4 + Phase 5).
///
/// V1.7.0 — Future tab plan §Phase 4 (merged Pro depth phase).

// MARK: - Free narrative line

/// One-line rules-based narrative below the chart. Rendered for all
/// users. Identifies the strongest absolute-delta lever from the
/// 14-day projection and fills a tone-conditional template, slotting
/// in a delta magnitude ("+1.4y") and threshold descriptor ("7.5h/night")
/// drawn from the resolved aggregates so the line stays accurate
/// during an active slider scrub.
struct FreeNarrativeLine: View {
    let perDimensionDelta: [HealthspanEngine.Dimension: Double]
    /// Resolved per-dim aggregates (overrides applied). Use
    /// `HealthspanEngine.resolvedAggregates(...)` at the call site so
    /// the threshold descriptor matches the dominant-lever delta.
    let aggregates: [HealthspanEngine.Dimension: Double]
    let tone: ToneMode

    var body: some View {
        if let line = composed {
            Text(line)
                .font(.body)
                .foregroundStyle(.primary)
                .accessibilityIdentifier("future.freeNarrative")
        }
    }

    private var composed: String? {
        guard let (dim, delta) = perDimensionDelta
            .filter({ $0.value != 0 })
            .max(by: { abs($0.value) < abs($1.value) }) else { return nil }
        let isPositive = delta >= 0
        let display = displayName(dim)
        let magnitude = formatYearsInline(abs(delta))
        let detail = thresholdDescriptor(dim, value: aggregates[dim] ?? 0)
        switch tone {
        case .gentle:
            if isPositive {
                return "\(display) has been carrying you — \(magnitude) from \(detail)."
            }
            return "\(display) has been a quiet drag — \(magnitude) at \(detail)."
        case .coach:
            if isPositive {
                return "\(display) is your strongest lever (\(magnitude), \(detail))."
            }
            return "\(display) is the drag (\(magnitude) at \(detail))."
        case .firmDirect:
            if isPositive {
                return "\(display): top lever. \(magnitude), \(detail)."
            }
            return "\(display): drag. \(magnitude) at \(detail)."
        }
    }

    private func displayName(_ dim: HealthspanEngine.Dimension) -> String {
        switch dim {
        case .sleep: return "Sleep"
        case .dietQuality: return "Whole food"
        case .steps: return "Steps"
        case .exerciseMinutes: return "Exercise"
        case .extras: return "Extras"
        case .nicotine: return "Nicotine"
        }
    }

    /// Inline years format ("1.4y" / "8m"). Separate from the headline's
    /// "X years, Y months" because this lives mid-sentence — tighter
    /// magnitudes read better.
    private func formatYearsInline(_ years: Double) -> String {
        let totalMonths = Int((years * 12).rounded())
        if totalMonths >= 12 {
            let y = Double(totalMonths) / 12.0
            return String(format: "%.1fy", y)
        }
        return "\(totalMonths)m"
    }

    /// Concrete per-dim threshold descriptor for the narrative slot
    /// ("7.5h/night", "11k/day"). Reads the resolved aggregate value
    /// so it tracks the slider during scrub.
    private func thresholdDescriptor(
        _ dim: HealthspanEngine.Dimension,
        value: Double
    ) -> String {
        switch dim {
        case .sleep:
            return String(format: "%.1fh/night", value)
        case .steps:
            if value >= 1_000 {
                return String(format: "%.0fk/day", value / 1_000)
            }
            return String(format: "%.0f/day", value)
        case .exerciseMinutes:
            return "\(Int(value.rounded())) min/wk"
        case .dietQuality:
            return "\(Int(value.rounded())) days/wk"
        case .extras:
            return "\(Int(value.rounded())) days/wk"
        case .nicotine:
            return "\(Int(value.rounded())) days/wk"
        }
    }
}

// MARK: - Pro long-form narrative

/// 3–4 paragraph Pro long-form. Recomputed every tab open (in-memory
/// only — no `WeeklyNarrativeSnapshot` persistence per the plan
/// simplification). Subhead derived from `clock.now().snappedToLastSunday`.
struct LongFormNarrative: View {
    let narrative: NarrativeEngine.Narrative

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text(narrative.subhead)
                .font(.caption)
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("future.longForm.subhead")
            ForEach(Array(narrative.ordered.enumerated()), id: \.offset) { _, para in
                Text(para)
                    .font(.body)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding(DesignTokens.Spacing.md)
        .background(
            DesignTokens.Palette.elevated,
            in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
        )
        .accessibilityIdentifier("future.longForm")
    }
}
