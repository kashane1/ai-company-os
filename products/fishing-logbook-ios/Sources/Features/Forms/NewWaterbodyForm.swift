import SwiftData
import SwiftUI

struct NewWaterbodyForm: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @State private var name = ""
    @State private var type: WaterbodyType = .lake

    var onSaved: ((Waterbody) -> Void)?

    var body: some View {
        NavigationStack {
            Form {
                Section("Waterbody") {
                    TextField("Name", text: $name)
                    Picker("Type", selection: $type) {
                        ForEach(WaterbodyType.allCases) { value in
                            Text(value.label).tag(value)
                        }
                    }
                    Text("Private by default.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("New Water")
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
                    .disabled(name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
    }

    private func save() {
        let waterbody = Waterbody(name: name.trimmingCharacters(in: .whitespacesAndNewlines), type: type)
        modelContext.insert(waterbody)
        try? modelContext.save()
        onSaved?(waterbody)
        dismiss()
    }
}
