import SwiftData
import SwiftUI

struct NewSpotForm: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @Query(sort: \Waterbody.createdAt) private var waterbodies: [Waterbody]

    @State private var title = ""
    @State private var notes = ""
    @State private var selectedWaterbodyID: UUID?
    @State private var showingWaterbodyForm = false

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
                        SectionEmptyState(
                            icon: "water.waves",
                            title: "No waterbodies yet",
                            subtitle: "Add a waterbody first, then save this spot."
                        )

                        Button {
                            showingWaterbodyForm = true
                        } label: {
                            Label("Add Waterbody", systemImage: "plus.circle.fill")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(.appAccent)
                    }
                } else {
                    Section {
                        TextField("Spot name", text: $title)
                            .textInputAutocapitalization(.words)
                            .submitLabel(.next)

                        Picker("Waterbody", selection: $selectedWaterbodyID) {
                            Text("Select water").tag(Optional<UUID>.none)
                            ForEach(waterbodies, id: \.id) { waterbody in
                                Text(waterbody.name).tag(Optional(waterbody.id))
                            }
                        }

                        Button {
                            showingWaterbodyForm = true
                        } label: {
                            Label("Add Waterbody", systemImage: "plus")
                                .font(.footnote)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)

                        TextField("Notes", text: $notes, axis: .vertical)
                            .lineLimit(2...4)
                    } header: {
                        Text("Spot")
                    } footer: {
                        Text("Private by default. Your spot stays on this device.")
                    }
                }
            }
            .navigationTitle("New Spot")
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
                    .disabled(!canSave)
                }
            }
            .interactiveDismissDisabled(!title.isEmpty)
        }
        .presentationDetents([.medium])
        .sheet(isPresented: $showingWaterbodyForm) {
            NewWaterbodyForm { waterbody in
                selectedWaterbodyID = waterbody.id
            }
        }
    }

    private var canSave: Bool {
        SpotFormLogic.canSave(title: title, selectedWaterbodyID: selectedWaterbodyID)
    }

    private var selectedWaterbody: Waterbody? {
        waterbodies.first(where: { $0.id == selectedWaterbodyID })
    }

    private func save() {
        let draft = SpotFormLogic.draft(title: title, notes: notes)
        let spot = Spot(
            title: draft.title,
            waterbody: selectedWaterbody,
            notes: draft.notes
        )
        modelContext.insert(spot)
        try? modelContext.save()
        onSaved?(spot)
        dismiss()
    }
}
