import SwiftUI

/// Shared driver-slider row used by `ReactiveSliderView` (the lead-in
/// demo) and the new reveal screens (`HealthspanRevealView`,
/// `RecoveryPreviewView`). One label, one slider, leading/trailing
/// extreme labels, optional caption.
///
/// **Why pinned mode lives here instead of a separate read-only view:**
/// the reveal screens want exactly the same visual shape as the demo —
/// the user reads it as "the slider I just played with, but now it shows
/// MY position." Disabling the slider via the `.pinned` mode keeps the
/// thumb, the rail, and the label structure identical; only the
/// interaction is removed.
struct LifeClockSliderRow: View {
    let label: String
    let leadingExtremeLabel: String
    let trailingExtremeLabel: String
    @Binding var value: Double
    let mode: Mode
    let identifierSuffix: String
    /// Optional caption shown beneath the slider — used by reveal screens
    /// to label *which* of the user's answers drove the pin position.
    let caption: String?

    enum Mode {
        /// Free-form drag. Used by `ReactiveSliderView` and by the
        /// recovery preview's one unlocked lever.
        case interactive
        /// Read-only — value is fixed by the binding, drag is suppressed.
        /// Used by reveal screens that want the visual without the input.
        case pinned
    }

    init(
        label: String,
        leadingExtremeLabel: String,
        trailingExtremeLabel: String,
        value: Binding<Double>,
        mode: Mode = .interactive,
        identifierSuffix: String,
        caption: String? = nil
    ) {
        self.label = label
        self.leadingExtremeLabel = leadingExtremeLabel
        self.trailingExtremeLabel = trailingExtremeLabel
        self._value = value
        self.mode = mode
        self.identifierSuffix = identifierSuffix
        self.caption = caption
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.caption.bold())
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("lifeClockSlider.\(identifierSuffix).label")

            Slider(value: $value, in: 0...1)
                .disabled(mode == .pinned)
                // Pinned sliders fade slightly so the rail reads as
                // "set, not editable" instead of "ready for input".
                .opacity(mode == .pinned ? 0.85 : 1.0)
                .accessibilityIdentifier("lifeClockSlider.\(identifierSuffix)")

            HStack {
                Text(leadingExtremeLabel)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                Spacer()
                Text(trailingExtremeLabel)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }

            if let caption {
                Text(caption)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .padding(.top, 2)
                    .accessibilityIdentifier("lifeClockSlider.\(identifierSuffix).caption")
            }
        }
    }
}

#if DEBUG
#Preview("Interactive") {
    @Previewable @State var value: Double = 0.6
    return LifeClockSliderRow(
        label: "Sleep",
        leadingExtremeLabel: "5 hrs",
        trailingExtremeLabel: "9 hrs",
        value: $value,
        mode: .interactive,
        identifierSuffix: "sleep"
    )
    .padding()
}

#Preview("Pinned w/ caption") {
    @Previewable @State var value: Double = 0.3
    return LifeClockSliderRow(
        label: "Movement",
        leadingExtremeLabel: "Sedentary",
        trailingExtremeLabel: "Active",
        value: $value,
        mode: .pinned,
        identifierSuffix: "movement",
        caption: "You're closer to sedentary today."
    )
    .padding()
}
#endif
