import SwiftUI

/// Pro-only editor for today's plan. Shows the three categories
/// (Movement, Sleep & Recovery, Nutrition & Habit) with up to three
/// quest variants each. The user picks one per category; their picks
/// last until tomorrow, then defaults reset (one-shot per the v1
/// product decision). "Reset to defaults" clears all picks at once.
///
/// Free users never see this sheet — `TodayView` shows the paywall
/// instead when they tap the plan.
struct PlanEditorSheet: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    Text(store.toneMode.planEditorSubtitle)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .padding(.bottom, DesignTokens.Spacing.xs)
                        .accessibilityIdentifier("planEditor.subtitle")

                    ForEach(QuestEngine.Category.allCases, id: \.self) { category in
                        categorySection(category)
                    }

                    Button(role: .destructive) {
                        store.clearTodayPlanOverrides()
                    } label: {
                        Label(store.toneMode.planEditorResetCTA, systemImage: "arrow.counterclockwise")
                    }
                    .accessibilityIdentifier("planEditor.reset")
                    .padding(.top, DesignTokens.Spacing.md)
                }
                .padding(DesignTokens.Spacing.lg)
                .readableColumn()
            }
            .navigationTitle(store.toneMode.planEditorTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                        .accessibilityIdentifier("planEditor.done")
                }
            }
            .accessibilityIdentifier("planEditor.screen")
        }
    }

    @ViewBuilder
    private func categorySection(_ category: QuestEngine.Category) -> some View {
        let variants = store.planVariants(for: category)
        let selectedSlug = store.todayPlanOverrides.picks[category.rawValue]
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text(category.displayTitle)
                .font(.headline)
                .accessibilityIdentifier("planEditor.categoryTitle.\(category.rawValue)")
            if variants.isEmpty {
                Text("No options today — already covered.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("planEditor.empty.\(category.rawValue)")
            } else {
                ForEach(variants, id: \.slug) { quest in
                    questRow(quest, isSelected: selectedSlug == quest.slug, category: category)
                }
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        .accessibilityIdentifier("planEditor.category.\(category.rawValue)")
    }

    private func questRow(_ quest: Quest, isSelected: Bool, category: QuestEngine.Category) -> some View {
        Button {
            // Pro-gated at the store layer. If the user somehow reaches
            // this row without Pro the call no-ops via thrown .notEntitled.
            try? store.selectPlanQuest(slug: quest.slug, in: category)
        } label: {
            HStack(alignment: .top, spacing: DesignTokens.Spacing.sm) {
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(isSelected ? DesignTokens.Palette.positive : .secondary)
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    Text(quest.title).font(.callout.bold())
                    Text(quest.detail).font(.caption).foregroundStyle(.secondary)
                }
                Spacer(minLength: 0)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .padding(.vertical, DesignTokens.Spacing.xs)
        .accessibilityIdentifier("planEditor.option.\(quest.slug)")
    }
}
