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
                        planCard(plan)
                        stepsCard(plan)
                        trustLine(plan)

                        if plan.canShareInvite {
                            inviteCard(plan)
                        }

                        if plan.canHandoffToText {
                            handoffCard(plan)
                        }

                        // CTA with extra breathing room
                        VStack(spacing: Spacing.sm) {
                            Button(plan.confirmationActionTitle) {
                                store.runConfirmationAction(for: plan.id)
                            }
                            .buttonStyle(ActionPillButtonStyle(prominent: true))
                            .disabled(!plan.canTakeConfirmationAction)

                            if !plan.canTakeConfirmationAction {
                                Text(plan.confirmationDisabledReason.isEmpty
                                     ? "Waiting for enough people to join before this unlocks."
                                     : plan.confirmationDisabledReason)
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
                                    .multilineTextAlignment(.center)
                                    .frame(maxWidth: .infinity)
                            }
                        }
                        .padding(.top, Spacing.sm)
                    }
                    .padding(Spacing.lg)
                }
                .background(Color.appBackground.ignoresSafeArea())
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

    // MARK: - Plan card (merged header + details)

    private func planCard(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            // Status row
            HStack {
                LifecycleBadgeView(lifecycle: plan.lifecycle)
                Spacer()
                AppBadge(text: plan.visibility.trustBadge, tone: .appSafe)
            }

            // Plan identity
            Text(plan.title)
                .font(.system(size: 24, weight: .bold, design: .rounded))

            Text(plan.confirmationRoomSubtitle)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            LifecycleProgressView(lifecycle: plan.lifecycle)

            // What you need to do — prominent guidance below progress
            Text(plan.nextStepGuidance)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            CardDivider()

            // Key facts
            HStack(spacing: Spacing.lg) {
                InfoRow(icon: "mappin.and.ellipse", text: plan.venueLabel)
                InfoRow(icon: "clock", text: plan.timeLabel)
            }
            InfoRow(icon: "person.3", text: "\(plan.joinedCount) joined · \(plan.interestedCount) interested")

            if !plan.joinConfidenceCue.isEmpty {
                Text(plan.joinConfidenceCue)
                    .font(.footnote.weight(.medium))
                    .foregroundStyle(plan.lifecycle == .confirmed || plan.lifecycle == .active ? Color.appSafe : Color.appMomentum)
            }

            Text(plan.lifecycleWindowDetail)
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
        .appSurface(prominent: true, tint: plan.lifecycle == .confirmed || plan.lifecycle == .active ? .appSafe : nil)
    }

    // MARK: - Steps card (icon-bulleted)

    private func stepsCard(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "What happens next")

            VStack(alignment: .leading, spacing: Spacing.sm) {
                stepRow(sequenceLineOne(for: plan))
                stepRow(sequenceLineTwo(for: plan))
                stepRow(sequenceLineThree(for: plan))
            }
        }
        .appSurface()
    }

    private func stepRow(_ text: String) -> some View {
        HStack(alignment: .top, spacing: Spacing.sm) {
            Circle()
                .fill(Color.appAccent.opacity(0.35))
                .frame(width: 6, height: 6)
                .padding(.top, 7)
            Text(stripped(text))
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }

    /// Strips a leading "N. " step prefix so content can be displayed without the number.
    private func stripped(_ text: String) -> String {
        guard text.count > 3,
              let first = text.first, first.isNumber,
              text.dropFirst().first == "." else {
            return text
        }
        return String(text.dropFirst(3))
    }

    // MARK: - Trust line (single-line, not a full card)

    private func trustLine(_ plan: AfterPlan) -> some View {
        HStack(spacing: Spacing.sm) {
            AppBadge(text: plan.visibility.trustBadge, tone: .appSafe)
            Text(plan.visibilityHeadline)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .lineLimit(1)
            Spacer()
            Button(plan.safetyEntryTitle) {
                isShowingSafety = true
            }
            .buttonStyle(TextLinkButtonStyle())
        }
        .appSurface(tint: .appSafe)
    }

    // MARK: - Invite card

    private func inviteCard(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Invite people", subtitle: "People in your context only.")

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

    // MARK: - Handoff to text

    private func handoffCard(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Coordinate outside the app", subtitle: plan.handoffSubtitle)

            ShareLink(
                item: plan.handoffTextBody,
                subject: Text(plan.title),
                message: Text("Here are the details for \(plan.title)")
            ) {
                HStack {
                    Label(plan.handoffCTATitle, systemImage: "message.fill")
                        .font(.subheadline.weight(.medium))
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundStyle(.secondary)
                        .font(.footnote)
                }
            }

            Text("After Plans owns discovery and formation. Last-mile coordination belongs in your messages.")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .appSurface()
    }

    // MARK: - Step copy

    private func sequenceLineOne(for plan: AfterPlan) -> String {
        switch plan.lifecycle {
        case .open:      "1. People see the plan and decide if they're in."
        case .forming:   "1. The group is converging on a time and place."
        case .confirmed: "1. The details are locked — everyone knows the plan."
        case .active:    "1. The plan is live."
        case .closed:    "1. The plan already happened."
        }
    }

    private func sequenceLineTwo(for plan: AfterPlan) -> String {
        switch plan.lifecycle {
        case .open, .forming: "2. Enough people joining locks the details in."
        case .confirmed:      "2. People mark themselves as heading out."
        case .active:         "2. The room reflects the agreed details."
        case .closed:         "2. This room is part of the record now."
        }
    }

    private func sequenceLineThree(for plan: AfterPlan) -> String {
        switch plan.lifecycle {
        case .open, .forming, .confirmed: "3. Final coordination moves to your messages app."
        case .active:  "3. You're set — just show up."
        case .closed:  "3. Any follow-up lives in the activity recap, not here."
        }
    }
}
