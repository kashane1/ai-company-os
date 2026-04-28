import SwiftUI

struct QuestsView: View {
    @Environment(LifeClockStore.self) private var store

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                    Text("1–3 quests per day. Pick one to do well.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    ForEach(store.todayQuests, id: \.id) { quest in
                        questCard(quest)
                    }

                    DisclaimerBanner()
                }
                .padding(DesignTokens.Spacing.lg)
            }
            .navigationTitle("Quests")
        }
    }

    private func questCard(_ quest: Quest) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack {
                Text(quest.title).font(.headline)
                Spacer()
                Text("+\(quest.rewardEstimateMinutes) min")
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
                Button(quest.completedAt == nil ? "Mark done" : "Undo") {
                    store.toggleQuestCompletion(quest)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }
}
