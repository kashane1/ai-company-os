import SwiftUI

struct CreatePlanView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @Environment(\.dismiss) private var dismiss
    @State private var draft = CreatePlanDraft()
    @State private var isPublishing = false

    var body: some View {
        let validationMessage = draft.validationMessage(hasContext: store.selectedContext != nil)

        Form {
            Section {
                Text("Pick a mode and give people enough to decide if they want to join.")
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

            Section("Core details") {
                TextField("Plan headline", text: $draft.title)
                TextField("What should people know?", text: $draft.summary, axis: .vertical)
                    .lineLimit(3, reservesSpace: true)
                if draft.visibility != .publicMatch {
                    // Public-match plans bind Place inside their own
                    // anchor section below — keep one editable Place
                    // field per form to avoid duplicate-binding bugs.
                    TextField("Place", text: $draft.venueHint)
                }
                TextField("Timing", text: $draft.timeHint)
            }

            // Visibility-conditional anchor section. Phase 5 contract:
            // - .sameContextOnly → context selector (legacy behavior).
            // - .publicMatch     → activity + venue (no context needed).
            // - .inviteOnly      → neither (sender controls reach).
            switch draft.visibility {
            case .sameContextOnly:
                Section("Context") {
                    Label(store.selectedContext?.title ?? "No context selected", systemImage: "sparkles.rectangle.stack")
                    Text(store.selectedContext?.trustNote ?? "Pick a context first to keep the plan bounded.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            case .publicMatch:
                Section("Activity") {
                    Picker("Activity", selection: $draft.activityID) {
                        Text("Pick one").tag(UUID?.none)
                        ForEach(ActivityTaxonomy.children) { activity in
                            Text(activity.title).tag(UUID?.some(activity.id))
                        }
                    }
                    Text("People who declared this activity in their profile will see your plan.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                Section("Place") {
                    TextField("Place", text: $draft.venueHint)
                    Text("A typed place becomes a freeform venue. We'll line it up with a real one when someone confirms the location.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            case .inviteOnly, .friendsOfParticipants, .knownPeople:
                EmptyView()
            }

            Section("What people will see") {
                Text(previewTitle)
                    .font(.headline)
                Text(previewSummary)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text("Once published, this plan appears on Home as your current move.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let message = validationMessage {
                Section {
                    Text(message)
                        .font(.footnote)
                        .foregroundStyle(.orange)
                }
            }
        }
        .animation(.default, value: draft.visibility)
        .tint(.appAccent)
        .navigationTitle("Plan What's Next")
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Close") { dismiss() }
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button("Publish") {
                    guard !isPublishing else { return }
                    isPublishing = true
                    Task {
                        defer { isPublishing = false }
                        if await store.createPlan(from: draft) {
                            dismiss()
                        }
                    }
                }
                .disabled(validationMessage != nil || isPublishing)
            }
        }
    }

    private var previewTitle: String {
        if !draft.trimmedTitle.isEmpty {
            return draft.trimmedTitle
        }

        if let context = store.selectedContext {
            return "\(draft.mode.defaultTitlePrefix) \(context.title)"
        }

        return "Pick a context to preview the plan"
    }

    private var previewSummary: String {
        let contextTitle = store.selectedContext?.title ?? "Current context"
        return "\(contextTitle) · \(draft.visibility.title) · \(draft.timeHint)"
    }
}
