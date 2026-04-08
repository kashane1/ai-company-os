import SwiftUI

struct ConfirmationRoomView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @State private var isShowingSafety = false
    let planID: UUID

    var body: some View {
        Group {
            if let plan = store.plan(with: planID) {
                ScrollView {
                    VStack(alignment: .leading, spacing: Spacing.xl) {
                        VStack(alignment: .leading, spacing: Spacing.md) {
                            LifecycleBadgeView(lifecycle: plan.lifecycle)
                            LifecycleProgressView(lifecycle: plan.lifecycle)
                            Text("Confirmation room")
                                .font(.system(size: 28, weight: .bold, design: .rounded))
                            Text(plan.confirmationRoomSubtitle)
                                .foregroundStyle(.secondary)
                        }
                        .appSurface(prominent: true)

                        VStack(alignment: .leading, spacing: Spacing.md) {
                            SectionHeader(title: "Locked details", subtitle: "Enough structure to move from soft interest to a real next plan.")
                            Text(plan.title)
                                .font(.headline)
                            InfoRow(icon: "mappin.and.ellipse", text: plan.venueLabel)
                            InfoRow(icon: "clock", text: plan.timeLabel)
                            InfoRow(icon: "person.3", text: "\(plan.joinedCount) joined · \(plan.interestedCount) interested")
                        }
                        .appSurface()

                        VStack(alignment: .leading, spacing: Spacing.md) {
                            SectionHeader(title: plan.lifecycleWindowTitle, subtitle: "Confirmation should feel like convergence, not like opening a chat thread.")
                            Text(plan.lifecycleHeadline)
                                .font(.headline)
                            Text(plan.nextStepGuidance)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            Text(plan.lifecycleWindowDetail)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                            Text(plan.participationLabel)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                        .appSurface()

                        VStack(alignment: .leading, spacing: Spacing.md) {
                            SectionHeader(title: "Visibility & Safety", subtitle: "Bounded visibility should stay legible even as the plan gets more real.")
                            Text(plan.visibilityHeadline)
                                .font(.headline)
                            Text(plan.visibilityDetail)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            Text(plan.visibilityFootnote)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                            Button(plan.safetyEntryTitle) {
                                isShowingSafety = true
                            }
                            .buttonStyle(ActionPillButtonStyle())
                        }
                        .appSurface()

                        VStack(alignment: .leading, spacing: Spacing.md) {
                            SectionHeader(title: "What happens next", subtitle: "Later slices can add handoff, arrival, and richer coordination.")
                            Text(sequenceLineOne(for: plan))
                            Text(sequenceLineTwo(for: plan))
                            Text(sequenceLineThree(for: plan))
                        }
                        .appSurface()

                        if plan.canShareInvite {
                            VStack(alignment: .leading, spacing: Spacing.md) {
                                SectionHeader(title: "Invite the right people", subtitle: "Sharing here should help the current plan form or fill in, not turn into broad outreach.")
                                Text(plan.shareActionSubtitle)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)

                                NavigationLink {
                                    InviteShareView(planID: plan.id)
                                } label: {
                                    HStack {
                                        VStack(alignment: .leading, spacing: 4) {
                                            Text(plan.shareActionTitle)
                                                .font(.headline)
                                            Text(plan.shareAudienceHeadline)
                                                .font(.subheadline)
                                                .foregroundStyle(.secondary)
                                        }
                                        Spacer()
                                        Image(systemName: "chevron.right")
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                            .appSurface()
                        }

                        Button(plan.confirmationActionTitle) {
                            store.runConfirmationAction(for: plan.id)
                        }
                        .buttonStyle(ActionPillButtonStyle(prominent: true))
                        .disabled(!plan.canTakeConfirmationAction)
                    }
                    .padding(Spacing.lg)
                }
                .navigationTitle("Confirmation")
                .sheet(isPresented: $isShowingSafety) {
                    NavigationStack {
                        SafetyCenterView(focusedPlanID: plan.id)
                    }
                }
            } else {
                ContentUnavailableView("Plan unavailable", systemImage: "exclamationmark.triangle")
            }
        }
    }

    private func sequenceLineOne(for plan: AfterPlan) -> String {
        switch plan.lifecycle {
        case .open:
            "1. People react while the plan is still lightweight."
        case .forming:
            "1. The group narrows toward one place and timing."
        case .confirmed:
            "1. The details are already locked for the group."
        case .active:
            "1. The plan is already underway."
        case .closed:
            "1. The plan already happened."
        }
    }

    private func sequenceLineTwo(for plan: AfterPlan) -> String {
        switch plan.lifecycle {
        case .open, .forming:
            "2. Enough joins and one clear option push it into a confirmed plan."
        case .confirmed:
            "2. People now shift from confirmed to actually heading there."
        case .active:
            "2. The room now just reflects the agreed details."
        case .closed:
            "2. The room is now history, not coordination."
        }
    }

    private func sequenceLineThree(for plan: AfterPlan) -> String {
        switch plan.lifecycle {
        case .open, .forming, .confirmed:
            "3. Last-mile chatter can hand off to text later."
        case .active:
            "3. No new setup should compete with the fact that it is already real."
        case .closed:
            "3. Any follow-up belongs to recap, not this room."
        }
    }
}
