import SwiftUI

/// Single-field reflection editor presented from the Today screen's
/// Reflection card. Modeled after `OverrideSheet` (NavigationStack +
/// VStack + Cancel/Save toolbar + drag indicator), not `QuickLogSheet`
/// (which is a multi-section Form).
///
/// Save defends against double-tap by disabling the Save button after
/// the first tap (`isSaving` flag). Underneath, the store's
/// `saveReflection(...)` is `@MainActor`-isolated and fetch-then-mutate
/// upserts on the local-day key.
///
/// Drafts persist across backgrounding via `@SceneStorage` keyed by
/// today's `dayKey` so a stale yesterday-draft never leaks into a new
/// day. Cancel discards the draft; Save and Delete clear it.
struct ReflectionSheet: View {
    @Environment(LifeClockStore.self) private var store
    @SceneStorage("reflection.draft") private var draft: String = ""
    @SceneStorage("reflection.draftDayKey") private var draftDayKey: Int = 0
    @State private var response: String = ""
    @State private var isSaving: Bool = false
    @State private var showDeleteConfirm: Bool = false
    let prompt: String
    let onDismiss: () -> Void

    private var todayKey: Int {
        DayKey.from(date: store.clock.now(), calendar: store.clock.calendar)
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                Text(prompt)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                TextEditor(text: $response)
                    .frame(minHeight: 120)
                    .padding(DesignTokens.Spacing.xs)
                    .background(
                        DesignTokens.Palette.elevated,
                        in: RoundedRectangle(cornerRadius: DesignTokens.Radius.sm)
                    )
                    .accessibilityIdentifier("reflection.editor")
                if store.todayReflection != nil {
                    Button(role: .destructive) {
                        showDeleteConfirm = true
                    } label: {
                        Label("Delete reflection", systemImage: "trash")
                            .font(.callout)
                    }
                    .accessibilityIdentifier("reflection.delete")
                }
                Spacer(minLength: 0)
            }
            .padding(DesignTokens.Spacing.lg)
            .navigationTitle("Reflection")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        clearDraft()
                        onDismiss()
                    }
                    .accessibilityIdentifier("reflection.cancel")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        guard !isSaving else { return }
                        isSaving = true
                        store.saveReflection(prompt: prompt, response: response)
                        clearDraft()
                        onDismiss()
                    }
                    .disabled(isSaving || response.trimmingCharacters(in: .whitespaces).isEmpty)
                    .accessibilityIdentifier("reflection.save")
                }
            }
            .presentationDetents([.medium, .large])
            .presentationDragIndicator(.visible)
            .onAppear {
                // Three-way priority on initial population:
                //   1. A persisted reflection for today (the user is editing).
                //   2. A draft saved earlier today during a backgrounded
                //      session (recovery path).
                //   3. Empty (first edit of the day).
                if let saved = store.todayReflection {
                    response = saved.response
                } else if draftDayKey == todayKey, !draft.isEmpty {
                    response = draft
                }
            }
            .onChange(of: response) { _, newValue in
                // Persist every keystroke so the draft survives if the
                // OS tears the sheet down while backgrounded.
                draft = newValue
                draftDayKey = todayKey
            }
            .confirmationDialog(
                "Delete this reflection?",
                isPresented: $showDeleteConfirm,
                titleVisibility: .visible
            ) {
                Button("Delete", role: .destructive) {
                    store.deleteTodayReflection()
                    response = ""
                    clearDraft()
                    onDismiss()
                }
                .accessibilityIdentifier("reflection.deleteConfirm")
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This will remove today's reflection. You can write a new one later.")
            }
        }
        .accessibilityIdentifier("reflection.screen")
    }

    private func clearDraft() {
        draft = ""
        draftDayKey = 0
    }
}
