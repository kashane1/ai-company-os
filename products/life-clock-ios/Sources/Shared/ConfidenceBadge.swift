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
                Text("Confidence: \(confidence.label)")
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
        .accessibilityLabel("Confidence: \(confidence.label). Tap for an explanation.")
        .accessibilityIdentifier("confidence.badge")
        // A small detent sheet rather than a true popover: the compact
        // popover adaptation on iPhone caps the popover height regardless
        // of content, which clips the explanation. A fraction detent
        // gives full visibility while still reading as a lightweight
        // pop-up rather than a full modal.
        .sheet(isPresented: $explanationPresented) {
            ConfidenceExplanationCard()
                .presentationDetents([.fraction(0.4)])
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

/// Generic explanation surfaced when the user taps the confidence badge.
/// Intentionally non-personalized — the message covers what drives the
/// score and the levers that raise it, regardless of the current value.
private struct ConfidenceExplanationCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text("Confidence")
                .font(.headline)
                .headingLighting()
            Text("Reflects how complete your Apple Health data was for the day. More signals → higher confidence.")
                .font(.callout)
                .foregroundStyle(.primary)
                .fixedSize(horizontal: false, vertical: true)
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                Text("To raise it")
                    .font(.subheadline.weight(.semibold))
                bullet("Wear your Apple Watch overnight for sleep.")
                bullet("Carry your iPhone so steps register.")
                bullet("Grant every Health permission Life Clock asks for.")
            }
            .padding(.top, DesignTokens.Spacing.xs)
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: 300)
        .accessibilityIdentifier("confidence.explanation")
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
