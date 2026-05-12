import SwiftUI

/// Free narrative line + Pro long-form narrative. Both live in one
/// file per the simplicity-review cut (was originally split across
/// Phase 4 + Phase 5).
///
/// V1.7.0 — Future tab plan §Phase 4 (merged Pro depth phase).

// MARK: - Free narrative line

/// One-line rules-based narrative below the chart. Rendered for all
/// users. Identifies the strongest absolute-delta lever from the
/// 14-day projection and fills a tone-conditional template.
struct FreeNarrativeLine: View {
    let perDimensionDelta: [HealthspanEngine.Dimension: Double]
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
        switch tone {
        case .gentle:
            return isPositive
                ? "\(display) has been carrying you."
                : "\(display) has been a quiet drag."
        case .coach:
            return isPositive
                ? "\(display) is your strongest lever."
                : "\(display) is the drag."
        case .firmDirect:
            return isPositive
                ? "\(display): top lever."
                : "\(display): drag."
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
