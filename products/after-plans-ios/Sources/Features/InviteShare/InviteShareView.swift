import SwiftUI

struct InviteShareView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @Environment(\.dismiss) private var dismiss
    @State private var isShowingSafety = false

    let planID: UUID

    var body: some View {
        Group {
            if let plan = store.plan(with: planID) {
                if plan.canShareInvite {
                    let preview = store.invitePreview(for: plan)
                    let channels = store.inviteChannels(for: plan)
                    let state = store.inviteShareState(for: plan.id)

                    List {
                        Section {
                            Text(plan.shareActionSubtitle)
                                .foregroundStyle(.secondary)
                            Text("This shell keeps sharing bounded to context, known people, and in-person handoff. It does not open a chat thread or generic outreach flow.")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }

                        Section("Invite preview") {
                            VStack(alignment: .leading, spacing: Spacing.sm) {
                                Text(preview.title)
                                    .font(.headline)
                                Text(preview.subtitle)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                                Text(preview.joinFraming)
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        Section("Who this is for") {
                            VStack(alignment: .leading, spacing: Spacing.sm) {
                                Text(preview.audienceHeadline)
                                    .font(.headline)
                                Text(preview.audienceDetail)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                                Text(plan.visibilityDetail)
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        Section("Share options") {
                            ForEach(channels) { channel in
                                Button {
                                    store.prepareInviteShare(for: plan.id, channel: channel)
                                } label: {
                                    HStack(alignment: .top, spacing: Spacing.md) {
                                        Image(systemName: channel.systemImage)
                                            .foregroundStyle(.appSafe)
                                        VStack(alignment: .leading, spacing: 4) {
                                            Text(channel.title)
                                                .font(.headline)
                                                .foregroundStyle(.primary)
                                            Text(channel.subtitle)
                                                .font(.subheadline)
                                                .foregroundStyle(.secondary)
                                            Text(channel.actionTitle)
                                                .font(.footnote.weight(.semibold))
                                                .foregroundStyle(.appMomentum)
                                        }
                                        Spacer()
                                    }
                                }
                                .buttonStyle(.plain)
                            }

                            Label(preview.linkLabel, systemImage: "link")
                                .foregroundStyle(.secondary)
                            Label(preview.qrLabel, systemImage: "qrcode")
                                .foregroundStyle(.secondary)
                        }

                        Section(state == nil ? preview.nextStepTitle : "Ready after sharing") {
                            if let state {
                                VStack(alignment: .leading, spacing: Spacing.sm) {
                                    Text(state.statusTitle)
                                        .font(.headline)
                                    Text(state.statusDetail)
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                }
                            } else {
                                Text(preview.nextStepDetail)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        Section("Trust note") {
                            VStack(alignment: .leading, spacing: Spacing.sm) {
                                Text(plan.trustBlurb)
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
                                Text(plan.visibilityFootnote)
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
                                Button(plan.safetyEntryTitle) {
                                    isShowingSafety = true
                                }
                            }
                        }
                    }
                    .navigationTitle("Invite & Share")
                    .toolbar {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button("Done") { dismiss() }
                        }
                    }
                    .sheet(isPresented: $isShowingSafety) {
                        NavigationStack {
                            SafetyCenterView(focusedPlanID: plan.id)
                        }
                    }
                } else {
                    ContentUnavailableView(
                        "Invite unavailable",
                        systemImage: "link.badge.plus",
                        description: Text(plan.shareActionSubtitle)
                    )
                }
            } else {
                ContentUnavailableView("Invite unavailable", systemImage: "link.badge.plus")
            }
        }
    }
}
