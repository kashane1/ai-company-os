import SwiftUI

struct ConfidenceBadge: View {
    let confidence: Confidence

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.xs) {
            Circle()
                .fill(color)
                .frame(width: 8, height: 8)
            Text("Confidence: \(confidence.label)")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, DesignTokens.Spacing.xs)
        .padding(.horizontal, DesignTokens.Spacing.sm)
        .background(DesignTokens.Palette.elevated, in: Capsule())
    }

    private var color: Color {
        switch confidence {
        case .high: return DesignTokens.Palette.positive
        case .medium: return .yellow
        case .low: return DesignTokens.Palette.muted
        }
    }
}
