import SwiftUI

struct InviteShareView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @Environment(\.dismiss) private var dismiss
    @State private var isShowingSafety = false
    @State private var isShowingQR = false

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
                            Text("Sharing is limited to people already in your context — not open outreach.")
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
                                if channel == .nearbyQR {
                                    Button {
                                        Task { await store.prepareInviteShare(for: plan.id, channel: channel) }
                                        isShowingQR = true
                                    } label: {
                                        channelRowLabel(channel)
                                    }
                                    .buttonStyle(.plain)
                                } else {
                                    ShareLink(
                                        item: plan.shareable.url,
                                        subject: Text(plan.title),
                                        message: Text(plan.shareable.text)
                                    ) {
                                        channelRowLabel(channel)
                                    }
                                    .buttonStyle(.plain)
                                    .simultaneousGesture(
                                        TapGesture().onEnded {
                                            Task { await store.prepareInviteShare(for: plan.id, channel: channel) }
                                        }
                                    )
                                }
                            }
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
                    .sheet(isPresented: $isShowingQR) {
                        qrSheet(for: plan)
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

    @ViewBuilder
    private func channelRowLabel(_ channel: InviteShareChannel) -> some View {
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

    @ViewBuilder
    private func qrSheet(for plan: AfterPlan) -> some View {
        NavigationStack {
            VStack(spacing: Spacing.lg) {
                Text("Show this to people already around you.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)

                QRCodeView(payload: plan.shareable.qrString)
                    .padding(.vertical, Spacing.sm)

                Text("Scan to join \"\(plan.title)\"")
                    .font(.headline)
                    .multilineTextAlignment(.center)

                Text("Only for people already here — not for wide sharing.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)

                ShareLink(
                    item: plan.shareable.url,
                    subject: Text(plan.title),
                    message: Text(plan.shareable.text)
                ) {
                    Label("Copy or share link", systemImage: "link")
                }
                .buttonStyle(.bordered)
            }
            .padding()
            .navigationTitle("Nearby QR")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { isShowingQR = false }
                }
            }
        }
    }
}
