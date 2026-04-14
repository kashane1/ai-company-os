import SwiftData
import SwiftUI

struct SavedLuresView: View {
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \SavedLure.name) private var lures: [SavedLure]

    @State private var showingAddForm = false
    @State private var editingLure: SavedLure?

    var body: some View {
        List {
            if lures.isEmpty {
                ContentUnavailableView {
                    Label("No Saved Lures", systemImage: "lasso.and.sparkles")
                } description: {
                    Text("Add your favorite lures and baits. They'll appear as suggestions when you log catches.")
                } actions: {
                    Button {
                        showingAddForm = true
                    } label: {
                        Label("Add Lure", systemImage: "plus")
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.appAccent)
                }
            } else {
                ForEach(lures, id: \.id) { lure in
                    Button {
                        editingLure = lure
                    } label: {
                        VStack(alignment: .leading, spacing: Spacing.xs) {
                            Text(lure.name)
                                .font(.subheadline.weight(.semibold))
                            if !lure.color.isEmpty {
                                Text(lure.color)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            if !lure.notes.isEmpty {
                                Text(lure.notes)
                                    .font(.caption)
                                    .foregroundStyle(.tertiary)
                                    .lineLimit(1)
                            }
                        }
                        .padding(.vertical, Spacing.xxs)
                    }
                    .buttonStyle(.plain)
                }
                .onDelete(perform: deleteLures)
            }
        }
        .navigationTitle("Saved Lures & Baits")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showingAddForm = true
                } label: {
                    Label("Add", systemImage: "plus")
                }
            }
        }
        .sheet(isPresented: $showingAddForm) {
            LureFormSheet()
        }
        .sheet(item: $editingLure) { lure in
            LureFormSheet(lure: lure)
        }
    }

    private func deleteLures(at offsets: IndexSet) {
        for index in offsets {
            modelContext.delete(lures[index])
        }
        try? modelContext.save()
    }
}

// MARK: - Lure Form Sheet

private struct LureFormSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext

    @State private var name: String
    @State private var color: String
    @State private var notes: String
    @State private var persistenceErrorMessage: String?

    let lure: SavedLure?

    init(lure: SavedLure? = nil) {
        self.lure = lure
        _name = State(initialValue: lure?.name ?? "")
        _color = State(initialValue: lure?.color ?? "")
        _notes = State(initialValue: lure?.notes ?? "")
    }

    private var canSave: Bool {
        SavedLuresLogic.canSave(name: name)
    }

    private var isEditing: Bool {
        lure != nil
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Lure or bait name", text: $name)
                        .textInputAutocapitalization(.words)
                        .characterLimit(CharacterLimits.lureName, text: $name)
                    TextField("Color / variant", text: $color)
                        .textInputAutocapitalization(.words)
                        .characterLimit(CharacterLimits.lureColor, text: $color)
                    TextField("Notes", text: $notes, axis: .vertical)
                        .lineLimit(2...4)
                        .characterLimit(CharacterLimits.lureNotes, text: $notes)
                } footer: {
                    Text("Saved lures will appear as suggestions when you log catches.")
                }
            }
            .navigationTitle(isEditing ? "Edit Lure" : "Add Lure")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { save() }
                        .fontWeight(.semibold)
                        .disabled(!canSave)
                }
            }
            .interactiveDismissDisabled(!name.isEmpty)
        }
        .presentationDetents([.medium])
        .persistenceFailureAlert(message: $persistenceErrorMessage)
    }

    private func save() {
        let draft = SavedLuresLogic.draft(name: name, color: color, notes: notes)

        if let lure {
            lure.name = draft.name
            lure.color = draft.color
            lure.notes = draft.notes
        } else {
            let newLure = SavedLure(name: draft.name, color: draft.color, notes: draft.notes)
            modelContext.insert(newLure)
        }

        PersistenceWriteCoordinator.perform(
            commit: {
                try modelContext.save()
            },
            rollback: {
                modelContext.rollback()
            },
            onSuccess: {
                dismiss()
            },
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
    }
}
