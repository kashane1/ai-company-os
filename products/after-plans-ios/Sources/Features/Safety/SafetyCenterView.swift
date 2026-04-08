import SwiftUI

struct SafetyCenterView: View {
    @EnvironmentObject private var store: AfterPlansStore
    let focusedPlanID: UUID?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Spacing.xl) {
                introCard

                if let focusedPlanID, let plan = store.plan(with: focusedPlanID) {
                    planActionsCard(plan)
                }

                reportReasonsCard
                moderationCard

                if !store.reportLog.isEmpty {
                    actionsLogCard
                }
            }
            .padding(Spacing.lg)
        }
        .background(Color.appBackground.ignoresSafeArea())
        .navigationTitle("Safety")
    }

    // MARK: - Intro

    private var introCard: some View {
        HStack(spacing: Spacing.lg) {
            Image(systemName: "shield.lefthalf.filled")
                .font(.system(size: 28, weight: .semibold))
                .foregroundStyle(Color.appSafe)

            VStack(alignment: .leading, spacing: 4) {
                Text("Your safety tools")
                    .font(.headline)
                Text("Report or block anyone, anytime. Your actions are private.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Spacer()
        }
        .appSurface(prominent: true, tint: .appSafe)
    }

    // MARK: - Plan-specific actions

    private func planActionsCard(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: plan.title, subtitle: plan.visibilityHeadline)

            Text(store.blockEffectNote)
                .font(.footnote)
                .foregroundStyle(.secondary)

            CardDivider()

            // Non-destructive report actions
            actionRow(
                label: "Report this plan",
                icon: "flag",
                action: { store.reportPlan(plan) }
            )

            CardDivider()

            actionRow(
                label: "Report \(plan.hostName)",
                icon: "person.crop.circle.badge.exclamationmark",
                action: { store.reportUser(named: plan.hostName) }
            )

            CardDivider()

            // Destructive block — extra breathing room + distinct weight from report actions
            Button {
                store.blockUser(named: plan.hostName)
            } label: {
                Label("Block \(plan.hostName)", systemImage: "hand.raised")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(Color.red.opacity(0.8))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, Spacing.sm)
                    .padding(.top, Spacing.xs)
            }
            .buttonStyle(PlainPressButtonStyle())
        }
        .appSurface()
    }

    private func actionRow(label: String, icon: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Label(label, systemImage: icon)
                .font(.subheadline)
                .foregroundStyle(Color.primary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.vertical, Spacing.sm)
        }
        .buttonStyle(PlainPressButtonStyle())
    }

    // MARK: - Report reasons

    private var reportReasonsCard: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "What to report")

            ForEach(Array(store.reportReasons.enumerated()), id: \.element.id) { index, reason in
                if index > 0 {
                    CardDivider()
                }
                HStack(alignment: .top, spacing: Spacing.md) {
                    Image(systemName: "exclamationmark.circle")
                        .font(.footnote)
                        .foregroundStyle(Color.appAccent.opacity(0.6))
                        .frame(width: 16)
                        .padding(.top, 2)

                    VStack(alignment: .leading, spacing: 2) {
                        Text(reason.title)
                            .font(.subheadline.weight(.medium))
                        Text(reason.explanation)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.vertical, 2)
            }
        }
        .appSurface()
    }

    // MARK: - Moderation note

    private var moderationCard: some View {
        Text(store.moderationNote)
            .font(.footnote)
            .foregroundStyle(.secondary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .appSurface()
    }

    // MARK: - Recent safety actions

    private var actionsLogCard: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Recent safety actions")

            ForEach(store.reportLog.reversed(), id: \.self) { item in
                HStack(spacing: Spacing.sm) {
                    Circle()
                        .fill(Color.appSafe.opacity(0.4))
                        .frame(width: 6, height: 6)
                    Text(item)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .appSurface()
    }
}
