import SwiftUI

/// Single-field reflection editor presented from the Today screen's
/// Reflection card. Modeled after `OverrideSheet` (NavigationStack +
/// VStack + Cancel/Save toolbar + medium detent + drag indicator), not
/// `QuickLogSheet` (which is a multi-section Form).
///
/// Save defends against double-tap by disabling the Save button after
/// the first tap (`isSaving` flag). Underneath, the store's
/// `saveReflection(...)` is `@MainActor`-isolated and fetch-then-mutate
/// upserts on the local-day key.
struct ReflectionSheet: View {
    @Environment(LifeClockStore.self) private var store
    @State private var response: String = ""
    @State private var isSaving: Bool = false
    let prompt: String
    let onDismiss: () -> Void

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
                Spacer(minLength: 0)
            }
            .padding(DesignTokens.Spacing.lg)
            .navigationTitle("Reflection")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { onDismiss() }
                        .accessibilityIdentifier("reflection.cancel")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        guard !isSaving else { return }
                        isSaving = true
                        store.saveReflection(prompt: prompt, response: response)
                        onDismiss()
                    }
                    .disabled(isSaving || response.trimmingCharacters(in: .whitespaces).isEmpty)
                    .accessibilityIdentifier("reflection.save")
                }
            }
            .presentationDetents([.medium])
            .presentationDragIndicator(.visible)
            .onAppear {
                if let saved = store.todayReflection {
                    response = saved.response
                }
            }
        }
        .accessibilityIdentifier("reflection.screen")
    }
}
