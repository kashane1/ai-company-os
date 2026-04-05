import SwiftData
import SwiftUI

struct NewWaterbodyForm: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @State private var name = ""
    @State private var type: WaterbodyType = .lake
    @State private var persistenceErrorMessage: String?

    var onSaved: ((Waterbody) -> Void)?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Name", text: $name)
                        .textInputAutocapitalization(.words)
                        .submitLabel(.done)

                    Picker("Type", selection: $type) {
                        ForEach(WaterbodyType.allCases) { value in
                            Text(value.label).tag(value)
                        }
                    }
                } header: {
                    Text("Waterbody")
                } footer: {
                    Text("Private by default. Only you can see your waters.")
                }
            }
            .navigationTitle("New Water")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        save()
                    }
                    .fontWeight(.semibold)
                    .disabled(!WaterbodyFormLogic.canSave(name: name))
                }
            }
            .interactiveDismissDisabled(!name.isEmpty)
        }
        .presentationDetents([.medium])
        .persistenceFailureAlert(message: $persistenceErrorMessage)
    }

    private func save() {
        let waterbody = Waterbody(name: WaterbodyFormLogic.normalizedName(name), type: type)
        modelContext.insert(waterbody)
        PersistenceWriteCoordinator.perform(
            commit: {
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
                onSaved?(waterbody)
                dismiss()
            },
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
    }
}
