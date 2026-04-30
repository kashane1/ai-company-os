import SwiftUI

struct QuestsView: View {
    @Environment(LifeClockStore.self) private var store

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                    Text(store.toneMode.questsPreamble)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    ForEach(Array(store.todayQuests.enumerated()), id: \.element.id) { index, quest in
                        questCard(quest, index: index)
                    }
                }
                .padding(DesignTokens.Spacing.lg)
                .readableColumn()
            }
            .navigationTitle(store.toneMode.questsTitle)
            .accessibilityIdentifier("plan.screen")
        }
    }

    private func questCard(_ quest: Quest, index: Int) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack {
                Text(quest.title).font(.headline)
                Spacer()
                Text("Potential \(TimeDeltaFormatter.format(minutes: quest.rewardEstimateMinutes))")
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(DesignTokens.Palette.positive)
            }
            Text(quest.detail)
                .font(.callout)
                .foregroundStyle(.secondary)
            HStack {
                Text(quest.category.capitalized)
                    .font(.caption2)
                    .padding(.horizontal, DesignTokens.Spacing.sm)
                    .padding(.vertical, DesignTokens.Spacing.xs)
                    .background(DesignTokens.Palette.surface, in: Capsule())
                Spacer()
                Button(quest.completedAt == nil ? "Mark complete" : "Undo") {
                    store.toggleQuestCompletion(quest)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
                .accessibilityIdentifier("plan.complete.\(index)")
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        .accessibilityIdentifier("plan.card.\(index)")
    }
}
