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
///     current store overrides, plus `store.clearTodayPlanOverrides()`
///     if the user cleared via Reset while inside the sheet.
///   - **Reset** (`planEditor.reset`) → blanks `draftPicks` only; the
///     store stays untouched until Done.
///
/// **Pre-selection.** On appear the sheet pre-selects the slug that's
/// currently effective for each category — an existing override if
/// present, otherwise the engine-generated quest currently shown in
/// today's plan, otherwise the top-ranked variant for that category.
/// This ensures the user always sees exactly three items selected
/// (matching the "today's plan is an atomic 3-tuple, swap in/out
/// but never dissect" product invariant) and so picking a different
/// row REPLACES the current pick rather than adding to it.
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
    /// An absent key means "untouched, use `initialPicks`".
    @State private var draftPicks: [String: String] = [:]

    /// Slug pre-selected for each category when the sheet appeared.
    /// Mirrors the today's plan card: existing override > engine pick >
    /// top variant. Re-read after `Reset` so the sheet still shows a
    /// full 3-tuple to pick from.
    @State private var initialPicks: [String: String] = [:]

    /// Set when the user tapped Reset inside the sheet. Done will then
    /// call `clearTodayPlanOverrides` first, before any per-category
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
                        // Stay inside the sheet — clear the draft and
                        // recompute the pre-selection so the sheet
                        // still shows a complete 3-tuple from engine
                        // defaults. The store is still showing the
                        // prior plan on the underlying Today card;
                        // Done will commit the clear, Cancel will
                        // throw it away.
                        draftPicks = [:]
                        draftCleared = true
                        initialPicks = computeInitialPicks(ignoringOverrides: true)
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
                initialPicks = computeInitialPicks(ignoringOverrides: false)
                draftPicks = [:]
                draftCleared = false
            }
            .interactiveDismissDisabled(false)
        }
    }

    /// Effective per-category selection given pre-selection + draft.
    /// Falls back to `initialPicks` when the user hasn't touched a row,
    /// so the sheet always shows the current today's-plan item highlighted
    /// (or, if nothing was current, the top variant) per the 3-tuple
    /// invariant.
    private func selectedSlug(for category: QuestEngine.Category) -> String? {
        if let drafted = draftPicks[category.rawValue] {
            return drafted
        }
        return initialPicks[category.rawValue]
    }

    /// Compute the slug to pre-select per category. Preference order:
    ///   1. Existing override (unless `ignoringOverrides`, used after Reset).
    ///   2. The slug currently shown in today's plan for this category.
    ///   3. The top-ranked variant in the editor list — fallback for
    ///      categories the engine left empty today (e.g. Movement when
    ///      the step goal is already met). Ensures the editor always
    ///      presents 3 selected items, satisfying "always 3 saved".
    private func computeInitialPicks(ignoringOverrides: Bool) -> [String: String] {
        var picks: [String: String] = [:]
        let overrides = ignoringOverrides ? [:] : store.todayPlanOverrides.picks
        for category in QuestEngine.Category.allCases {
            if let slug = overrides[category.rawValue] {
                picks[category.rawValue] = slug
                continue
            }
            if let quest = store.todayQuests.first(where: { LifeClockStore.engineCategory(of: $0) == category }) {
                picks[category.rawValue] = quest.slug
                continue
            }
            if let first = store.planVariants(for: category).first {
                picks[category.rawValue] = first.slug
            }
        }
        return picks
    }

    /// Commit the final selection per category. Always writes the picks
    /// that DIFFER from the store's current overrides; engine-derived
    /// pre-selections that the user didn't touch are skipped unless the
    /// engine produced no quest for that category — in which case we
    /// write the fallback as an override so today's plan still shows
    /// three items.
    private func commitDraft() {
        if draftCleared {
            store.clearTodayPlanOverrides()
        }
        let overridesBefore = draftCleared ? [:] : store.todayPlanOverrides.picks
        for category in QuestEngine.Category.allCases {
            guard let slug = selectedSlug(for: category) else { continue }
            if overridesBefore[category.rawValue] == slug { continue }
            // If there's no existing override AND the engine is already
            // showing this slug for this category, skip — writing would
            // just lock in what's already happening.
            let engineCurrent = store.todayQuests
                .first(where: { LifeClockStore.engineCategory(of: $0) == category })?.slug
            if overridesBefore[category.rawValue] == nil && engineCurrent == slug {
                continue
            }
            try? store.selectPlanQuest(slug: slug, in: category)
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
