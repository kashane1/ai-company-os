import SwiftUI

struct ContextSelectionView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        List {
            Section {
                Text("Anchor the feed to what just ended so the app feels bounded and trust-aware from the start.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Section("Suggested right now") {
                ForEach(store.availableContexts) { context in
                    Button {
                        store.selectContext(context)
                        dismiss()
                    } label: {
                        VStack(alignment: .leading, spacing: Spacing.xs) {
                            Text(context.title)
                                .foregroundStyle(.primary)
                            Text("\(context.venueName) · \(context.endedAtLabel)")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            Text(context.trustNote)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }

            Section("Later, not now") {
                Label("Manual context entry", systemImage: "square.and.pencil")
                Label("Context inference from location", systemImage: "location")
                Label("Imported invite or QR context", systemImage: "qrcode")
            }
            .foregroundStyle(.secondary)
        }
        .navigationTitle("Current Context")
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Close") { dismiss() }
            }
        }
    }
}
