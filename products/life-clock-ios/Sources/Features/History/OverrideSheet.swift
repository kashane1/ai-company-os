import SwiftUI

/// Single-field bottom sheet for entering a Pro override value.
/// Validation is delegated to `OverrideService.applyOverride` which
/// returns `.invalidValue` for out-of-bounds inputs; the sheet surfaces
/// that as inline tone-aware copy.
struct OverrideSheet: View {
    let field: SnapshotOverrideMap.Field
    let dayStart: Date
    let currentValue: Double?
    let onDismiss: () -> Void

    @Environment(LifeClockStore.self) private var store
    @State private var inputText: String = ""
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                Text(field.displayName)
                    .font(.headline)

                TextField("Value", text: $inputText)
                    .keyboardType(field.keyboardType)
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 32, weight: .semibold, design: .rounded))

                Text(field.bounds)
                    .font(.caption)
                    .foregroundStyle(.secondary)

                if let errorMessage {
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundStyle(DesignTokens.Palette.negative)
                }

                Spacer()
            }
            .padding(DesignTokens.Spacing.lg)
            .navigationTitle("Adjust value")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel", action: onDismiss)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save", action: save)
                        .disabled(inputText.isEmpty)
                }
            }
            .presentationDetents([.medium])
            .presentationDragIndicator(.visible)
        }
        .onAppear { prefill() }
    }

    private func prefill() {
        guard let currentValue else { return }
        inputText = field.spec.editorFormat(currentValue)
    }

    private func save() {
        guard let value = Double(inputText.replacingOccurrences(of: ",", with: ".")) else {
            errorMessage = "Enter a number."
            return
        }
        do {
            try store.applyOverride(field: field, value: value, on: dayStart)
            onDismiss()
        } catch OverrideService.OverrideError.notEntitled {
            errorMessage = store.toneMode.overrideNotEntitledMessage
        } catch OverrideService.OverrideError.invalidValue {
            errorMessage = "Out of range. \(field.bounds)."
        } catch OverrideService.OverrideError.snapshotMissing {
            errorMessage = "No data for this day yet."
        } catch {
            errorMessage = "Couldn't save. Try again."
        }
    }
}

private extension SnapshotOverrideMap.Field {
    // Thin convenience aliases to the field's `Spec` so view code reads
    // naturally. Spec is the single source of truth — see
    // `SnapshotOverrideMap.Field.spec` in `SnapshotOverrideMap.swift`.
    var keyboardType: UIKeyboardType { spec.keyboard }
    var bounds: String { spec.boundsCopy }
}
