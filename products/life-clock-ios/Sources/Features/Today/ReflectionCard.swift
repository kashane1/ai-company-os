import SwiftUI

/// Today's reflection surface. Renders the day's deterministic prompt
/// from `ReflectionPrompts` when no reflection has been saved yet, or
/// the saved response in a "Saved." state when one exists. Tapping the
/// card opens `ReflectionSheet` via the `onTap` closure provided by
/// `TodayView` (sheet ownership lives at the parent, matching the
/// `quickLogPresented` pattern in the same view).
struct ReflectionCard: View {
    @Environment(LifeClockStore.self) private var store
    let onTap: () -> Void

    var body: some View {
        let prompt = ReflectionPrompts.prompt(
            for: store.clock.now(),
            tone: store.toneMode,
            calendar: store.clock.calendar
        )

        Button(action: onTap) {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                Text(store.toneMode.reflectionHeading)
                    .font(.headline)
                if let saved = store.todayReflection {
                    Text(saved.prompt)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                    Text(saved.response)
                        .font(.callout)
                        .lineLimit(3)
                        .accessibilityIdentifier("today.reflection.savedResponse")
                    Text("Saved. Tap to edit.")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                } else {
                    Text(prompt)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("today.reflection.prompt")
                    HStack {
                        Spacer()
                        Text("Reflect")
                            .font(.callout.bold())
                            .accessibilityIdentifier("today.reflection.openSheet")
                    }
                }
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityHint(Text(store.todayReflection == nil ? "Double tap to write a reflection" : "Double tap to edit your reflection"))
        .accessibilityIdentifier("today.reflection")
    }
}
