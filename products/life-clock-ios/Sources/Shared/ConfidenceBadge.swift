import SwiftUI

struct ConfidenceBadge: View {
    let confidence: Confidence
    @State private var explanationPresented: Bool = false

    var body: some View {
        Button {
            explanationPresented = true
        } label: {
            HStack(spacing: DesignTokens.Spacing.xs) {
                Circle()
                    .fill(color)
                    .frame(width: 8, height: 8)
                Text("Data quality: \(confidence.label)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Image(systemName: "info.circle")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, DesignTokens.Spacing.xs)
            .padding(.horizontal, DesignTokens.Spacing.sm)
            .background(DesignTokens.Palette.elevated, in: Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Data quality: \(confidence.label). Tap for an explanation.")
        .accessibilityIdentifier("dataQuality.badge")
        // A small detent sheet rather than a true popover: the compact
        // popover adaptation on iPhone caps the popover height regardless
        // of content, which clips the explanation. A fraction detent
        // gives full visibility while still reading as a lightweight
        // pop-up rather than a full modal.
        .sheet(isPresented: $explanationPresented) {
            DataQualityExplanationCard()
                .presentationDetents([.fraction(0.5)])
                .presentationDragIndicator(.visible)
        }
    }

    private var color: Color {
        switch confidence {
        case .high: return DesignTokens.Palette.positive
        case .medium: return .yellow
        case .low: return DesignTokens.Palette.muted
        }
    }
}

/// Generic explanation surfaced when the user taps the data-quality badge.
/// Intentionally non-personalized — the message covers what drives the
/// score and the levers that raise it, regardless of the current value.
private struct DataQualityExplanationCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Data quality")
                .font(.headline)
                .headingLighting()
            Text("How much we have to work with today. Half comes from what you log, half from what your devices measure.")
                .font(.callout)
                .foregroundStyle(.primary)
                .fixedSize(horizontal: false, vertical: true)
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                Text("To raise it")
                    .font(.subheadline.weight(.semibold))
                bullet("Complete the daily check-in.")
                bullet("Wear your Apple Watch overnight for sleep.")
                bullet("Carry your iPhone so steps register.")
                bullet("Grant every Health permission Life Clock asks for.")
            }
            .padding(.top, DesignTokens.Spacing.xs)
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: 320)
        .accessibilityIdentifier("dataQuality.explanation")
    }

    private func bullet(_ text: String) -> some View {
        HStack(alignment: .top, spacing: DesignTokens.Spacing.xs) {
            Text("•").foregroundStyle(.secondary)
            Text(text)
                .font(.callout)
                .foregroundStyle(.primary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}
