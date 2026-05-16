import SwiftUI

/// Top-anchored, auto-dismissing presentation of a `SupportMoment`.
///
/// Replaces the inline `SupportMomentCard` slot that previously sat
/// between the projected-healthspan card and the drivers card on Today.
/// Behavior matches an iOS toast: slides down from beneath the nav bar,
/// auto-dismisses after 3.5s, and is manually dismissable via the close
/// button. A new moment arriving while one is on screen cancels the
/// prior timer and restarts it (driven by `.task(id: moment)`), so
/// rapid quest taps replace rather than queue.
struct SupportMomentToast: View {
    let moment: SupportMoment
    let dismissAction: () -> Void

    /// 3.5s read-time. Long enough for the longer
    /// "Today's signals moved your Life Clock by X" copy without
    /// lingering on a snappy ack like "Action removed."
    private static let visibleDuration: Duration = .milliseconds(3500)

    var body: some View {
        HStack(alignment: .top, spacing: DesignTokens.Spacing.sm) {
            Image(systemName: moment.tone == .celebration ? "sparkles" : "heart.text.square")
                .foregroundStyle(
                    moment.tone == .celebration
                        ? DesignTokens.Palette.positive
                        : Color.accentColor
                )
                .imageScale(.medium)
                .padding(.top, 1)
            VStack(alignment: .leading, spacing: 2) {
                Text(moment.title)
                    .font(.subheadline.weight(.semibold))
                Text(moment.detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
            Button {
                dismissAction()
            } label: {
                Image(systemName: "xmark")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.secondary)
                    .padding(6)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Dismiss")
            .accessibilityIdentifier("supportMoment.dismiss")
        }
        .padding(.horizontal, DesignTokens.Spacing.md)
        .padding(.vertical, DesignTokens.Spacing.sm)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(.regularMaterial)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .strokeBorder(Color.primary.opacity(0.06), lineWidth: 0.5)
        )
        .cardLighting()
        .padding(.horizontal, DesignTokens.Spacing.md)
        .padding(.top, DesignTokens.Spacing.xs)
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("today.supportMoment")
        .task(id: moment) {
            try? await Task.sleep(for: Self.visibleDuration)
            guard !Task.isCancelled else { return }
            dismissAction()
        }
    }
}
