import SwiftUI

struct InviteShareView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @Environment(\.dismiss) private var dismiss

    let planID: UUID

    var body: some View {
        Group {
            if let plan = store.plan(with: planID) {
                let preview = store.invitePreview(for: plan)

                List {
                    Section {
                        Text("Share stays bounded to context and invite paths in this shell. Deep-link plumbing and QR generation come in a later slice.")
                            .foregroundStyle(.secondary)
                    }

                    Section("Invite preview") {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            Text(preview.title)
                                .font(.headline)
                            Text(preview.subtitle)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }

                    Section("Share options") {
                        Label(preview.linkLabel, systemImage: "link")
                        Label(preview.qrLabel, systemImage: "qrcode")
                        Label("Use the standard share sheet later", systemImage: "square.and.arrow.up")
                    }

                    Section("Trust note") {
                        Text(plan.trustBlurb)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
                .navigationTitle("Invite & Share")
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Done") { dismiss() }
                    }
                }
            } else {
                ContentUnavailableView("Invite unavailable", systemImage: "link.badge.plus")
            }
        }
    }
}
