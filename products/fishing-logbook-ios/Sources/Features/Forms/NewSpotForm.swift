import SwiftData
import SwiftUI

struct NewSpotForm: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @Query(sort: \Waterbody.createdAt) private var waterbodies: [Waterbody]

    @State private var title = ""
    @State private var notes = ""
    @State private var selectedWaterbodyID: UUID?

    var preselectedWaterbodyID: UUID?
    var onSaved: ((Spot) -> Void)?

    init(preselectedWaterbodyID: UUID? = nil, onSaved: ((Spot) -> Void)? = nil) {
        self.preselectedWaterbodyID = preselectedWaterbodyID
        self.onSaved = onSaved
        _selectedWaterbodyID = State(initialValue: preselectedWaterbodyID)
    }

    var body: some View {
        NavigationStack {
            Form {
                if waterbodies.isEmpty {
                    Section {
                        Text("Create a waterbody first so this spot has a private home.")
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Section("Spot") {
                        TextField("Spot name", text: $title)
                        Picker("Waterbody", selection: $selectedWaterbodyID) {
                            ForEach(waterbodies, id: \.id) { waterbody in
                                Text(waterbody.name).tag(Optional(waterbody.id))
                            }
                        }
                        TextField("Notes", text: $notes, axis: .vertical)
                    }
                }
            }
            .navigationTitle("New Spot")
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
                    .disabled(!canSave)
                }
            }
        }
    }

    private var canSave: Bool {
        !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && selectedWaterbody != nil
    }

    private var selectedWaterbody: Waterbody? {
        waterbodies.first(where: { $0.id == selectedWaterbodyID })
    }

    private func save() {
        let spot = Spot(
            title: title.trimmingCharacters(in: .whitespacesAndNewlines),
            waterbody: selectedWaterbody,
            notes: notes.trimmingCharacters(in: .whitespacesAndNewlines)
        )
        modelContext.insert(spot)
        try? modelContext.save()
        onSaved?(spot)
        dismiss()
    }
}
