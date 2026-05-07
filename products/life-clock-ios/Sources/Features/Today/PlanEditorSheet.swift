import SwiftUI

/// Pro-only editor for today's plan. Shows the three categories
/// (Movement, Sleep & Recovery, Nutrition & Habit) with up to three
/// quest variants each. The user picks one per category; their picks
/// last until tomorrow, then defaults reset (one-shot per the v1
/// product decision). "Reset to defaults" clears all picks at once.
///
/// Free users never see this sheet — `TodayView` shows the paywall
/// instead when they tap the plan.
///
/// **Draft semantics.** Row taps mutate a sheet-local `draftPicks`
/// dictionary. The store is touched in exactly two places:
///   - **Done** (`planEditor.done`) → loop the draft and call
///     `store.selectPlanQuest` for every entry that differs from the
///     baseline (the store's overrides at sheet appear), plus
///     `store.clearTodayPlanOverrides()` if the user cleared via Reset
///     while inside the sheet.
///   - **Reset** (`planEditor.reset`) → blanks `draftPicks` only; the
///     store stays untouched until Done.
///
/// **Cancel.** Cancel + swipe-down dismissal both leave the store
/// unchanged — `draftPicks` is discarded, and the underlying Today
/// plan card reflects whatever the user had before they opened the
/// sheet. This matches the behavior an operator asked for in
/// `polish-2026-05-06-plan-editor-pro-and-free-walk.md` Ask 1 (a).
struct PlanEditorSheet: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    /// Per-category slug picks the user has touched in this sheet.
    /// `nil` value means "the user explicitly reset this category"; an
    /// absent key means "untouched, use baseline".
    @State private var draftPicks: [String: String?] = [:]

    /// Snapshot of the store's overrides at the moment the sheet
    /// appeared. Used as the baseline for Done's diff and to suppress
    /// no-op writes.
    @State private var baselinePicks: [String: String] = [:]

    /// Set when the user tapped Reset inside the sheet. Done will then
    /// call `clearTodayPlanOverrides` instead of (or before) per-category
    /// writes. Discarded on Cancel along with the rest of the draft.
    @State private var draftCleared: Bool = false

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
                        // Stay inside the sheet — only blank the draft.
                        // The store is still showing the prior plan on
                        // the underlying Today card; Done will commit
                        // the clear, Cancel will throw it away.
                        draftPicks = [:]
                        draftCleared = true
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
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        // Discard draft. The store is already untouched
                        // — nothing else to roll back.
                        dismiss()
                    }
                    .accessibilityIdentifier("planEditor.cancel")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        commitDraft()
                        dismiss()
                    }
                    .accessibilityIdentifier("planEditor.done")
                }
            }
            .accessibilityIdentifier("planEditor.screen")
            .onAppear {
                baselinePicks = store.todayPlanOverrides.picks
                draftPicks = [:]
                draftCleared = false
            }
            .interactiveDismissDisabled(false)
        }
    }

    /// Effective per-category selection given baseline + draft.
    /// Returns nil if the user reset that category in this sheet OR
    /// if the user reset the whole sheet via the destructive button.
    private func selectedSlug(for category: QuestEngine.Category) -> String? {
        if draftCleared {
            // After a sheet-level reset, individual category picks the
            // user makes afterward override the cleared baseline.
            if let drafted = draftPicks[category.rawValue], let slug = drafted {
                return slug
            }
            return nil
        }
        if let drafted = draftPicks[category.rawValue] {
            return drafted // may be nil if the user explicitly cleared the row
        }
        return baselinePicks[category.rawValue]
    }

    /// Diff the draft against the baseline and write through. Called
    /// only on Done.
    private func commitDraft() {
        if draftCleared {
            store.clearTodayPlanOverrides()
            // After the clear, replay any drafted picks. (Edge case:
            // user hit Reset, then picked a new variant before Done.)
            for category in QuestEngine.Category.allCases {
                if let drafted = draftPicks[category.rawValue], let slug = drafted {
                    try? store.selectPlanQuest(slug: slug, in: category)
                }
            }
            return
        }

        for category in QuestEngine.Category.allCases {
            guard let drafted = draftPicks[category.rawValue] else { continue }
            let baseline = baselinePicks[category.rawValue]
            guard drafted != baseline else { continue }
            if let slug = drafted {
                try? store.selectPlanQuest(slug: slug, in: category)
            }
            // `nil`-drafted (the user explicitly cleared one row) is
            // not currently expressible from the UI — the row tap just
            // selects, never deselects. If we add a per-category clear
            // later, route it through the store's per-category clear.
        }
    }

    @ViewBuilder
    private func categorySection(_ category: QuestEngine.Category) -> some View {
        let variants = store.planVariants(for: category)
        let selected = selectedSlug(for: category)
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
                    questRow(quest, isSelected: selected == quest.slug, category: category)
                }
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Palette.elevated, in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        // `.contain` keeps child ids (planEditor.categoryTitle.<raw>,
        // planEditor.empty.<raw>, planEditor.option.<slug>) reachable
        // instead of letting this container's id swallow them. Same
        // shape as `today.plan` in TodayView.
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("planEditor.category.\(category.rawValue)")
    }

    private func questRow(_ quest: Quest, isSelected: Bool, category: QuestEngine.Category) -> some View {
        Button {
            // Mutate the draft only; store is untouched until Done.
            draftPicks[category.rawValue] = quest.slug
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
