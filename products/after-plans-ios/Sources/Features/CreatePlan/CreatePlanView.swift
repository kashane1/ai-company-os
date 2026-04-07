import SwiftUI

struct CreatePlanView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @Environment(\.dismiss) private var dismiss
    @State private var draft = CreatePlanDraft()

    var body: some View {
        Form {
            Section {
                Text("Creation should feel lighter than spinning up a full event. Pick one mode and give people enough context to join.")
                    .foregroundStyle(.secondary)
            }

            Section("Plan mode") {
                ForEach(PlanMode.allCases) { mode in
                    Button {
                        draft.mode = mode
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(mode.title)
                                    .foregroundStyle(.primary)
                                Text(mode.subtitle)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            if draft.mode == mode {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(.appAccent)
                            }
                        }
                    }
                }
            }

            Section("Core details") {
                TextField("Plan headline", text: $draft.title)
                TextField("What should people know?", text: $draft.summary, axis: .vertical)
                    .lineLimit(3, reservesSpace: true)
                TextField("Place", text: $draft.venueHint)
                TextField("Timing", text: $draft.timeHint)
            }

            Section("Visibility") {
                ForEach(PlanVisibility.launchModes) { visibility in
                    Button {
                        draft.visibility = visibility
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(visibility.title)
                                    .foregroundStyle(.primary)
                                Text(visibility.subtitle)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            if draft.visibility == visibility {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(.appAccent)
                            }
                        }
                    }
                }
            }

            Section("Context") {
                Label(store.selectedContext?.title ?? "No context selected", systemImage: "sparkles.rectangle.stack")
                Text(store.selectedContext?.trustNote ?? "Pick a context first to keep the plan bounded.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let message = draft.validationMessage(hasContext: store.selectedContext != nil) {
                Section {
                    Text(message)
                        .font(.footnote)
                        .foregroundStyle(.orange)
                }
            }
        }
        .navigationTitle("Start What's Next")
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Close") { dismiss() }
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button("Publish") {
                    if store.createPlan(from: draft) {
                        dismiss()
                    }
                }
            }
        }
    }
}
