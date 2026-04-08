import SwiftUI

struct ContextSelectionView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        List {
            Section {
                Text("Pick what just ended to anchor your feed to the right moment and the right people.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Section("Suggested right now") {
                ForEach(store.availableContexts) { context in
                    Button {
                        store.selectContext(context)
                        dismiss()
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: Spacing.xs) {
                                Text(context.title)
                                    .font(.headline)
                                    .foregroundStyle(.primary)
                                Text("\(context.venueName) · \(context.endedAtLabel)")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                                Text(context.trustNote)
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            if store.selectedContext?.id == context.id {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(Color.appAccent)
                            } else {
                                Image(systemName: "chevron.right")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.tertiary)
                            }
                        }
                        .padding(.vertical, 2)
                    }
                }

                if store.availableContexts.isEmpty {
                    Label("No recent contexts found.", systemImage: "clock")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("Current Context")
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Close") { dismiss() }
            }
        }
    }
}
