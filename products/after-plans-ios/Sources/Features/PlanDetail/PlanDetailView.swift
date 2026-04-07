import SwiftUI

struct PlanDetailView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @State private var isShowingInvite = false
    @State private var isShowingSafety = false

    let planID: UUID

    var body: some View {
        Group {
            if let plan = store.plan(with: planID) {
                ScrollView {
                    VStack(alignment: .leading, spacing: Spacing.xl) {
                        header(plan)
                        actions(plan)
                        people(plan)
                        suggestions(plan)
                        confirmation(plan)
                    }
                    .padding(Spacing.lg)
                }
                .navigationTitle("Plan Detail")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItemGroup(placement: .topBarTrailing) {
                        Button {
                            isShowingInvite = true
                        } label: {
                            Image(systemName: "qrcode")
                        }

                        Button {
                            isShowingSafety = true
                        } label: {
                            Image(systemName: "shield")
                        }
                    }
                }
                .sheet(isPresented: $isShowingInvite) {
                    NavigationStack {
                        InviteShareView(planID: plan.id)
                    }
                }
                .sheet(isPresented: $isShowingSafety) {
                    NavigationStack {
                        SafetyCenterView(focusedPlanID: plan.id)
                    }
                }
            } else {
                ContentUnavailableView("Plan unavailable", systemImage: "eye.slash", description: Text("This plan is hidden because it was blocked or no longer exists in the shell state."))
            }
        }
    }

    private func header(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    Text(plan.title)
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                    Text(plan.summary)
                        .font(.body)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: Spacing.xs) {
                    AppBadge(text: plan.lifecycle.title, tone: .appMomentum)
                    AppBadge(text: plan.visibility.title)
                }
            }

            Text(plan.trustBlurb)
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.secondary)

            HStack(spacing: Spacing.md) {
                InfoRow(icon: "sparkles.rectangle.stack", text: plan.contextTitle)
                InfoRow(icon: "clock", text: plan.timeLabel)
            }

            HStack(spacing: Spacing.md) {
                InfoRow(icon: "mappin.and.ellipse", text: plan.venueLabel)
                InfoRow(icon: "person.3", text: plan.momentumLine)
            }

            Text(plan.participationLabel)
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .appSurface(prominent: true)
    }

    private func actions(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Quick actions", subtitle: "Soft signals stay visible before anything turns into chat.")

            HStack(spacing: Spacing.sm) {
                Button("Join") { store.join(plan.id) }
                    .buttonStyle(ActionPillButtonStyle(prominent: true))
                Button("Interested") { store.expressInterest(in: plan.id) }
                    .buttonStyle(ActionPillButtonStyle())
            }

            HStack(spacing: Spacing.sm) {
                Button("Suggest place") { store.suggestDefaultPlace(for: plan.id) }
                    .buttonStyle(ActionPillButtonStyle())
                Button("Share") { isShowingInvite = true }
                    .buttonStyle(ActionPillButtonStyle())
            }
        }
        .appSurface()
    }

    private func people(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Who is in", subtitle: "Identity-light, but not anonymous.")

            ForEach(plan.participants) { participant in
                HStack {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(participant.name)
                            .font(.headline)
                        Text(participant.descriptor)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    if participant.isOrganizer {
                        AppBadge(text: "Host", tone: .appSafe)
                    } else if participant.isKnown {
                        AppBadge(text: "Known")
                    }
                }
                .padding(.vertical, 4)
            }
        }
        .appSurface()
    }

    private func suggestions(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Place suggestions", subtitle: "Enough structure to converge without building chat.")

            if plan.placeSuggestions.isEmpty {
                Text("No suggestions yet. The shell keeps this lightweight and bounded.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(plan.placeSuggestions, id: \.self) { suggestion in
                    HStack {
                        Text(suggestion)
                        Spacer()
                        Image(systemName: "arrow.up.right.circle")
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .appSurface()
    }

    private func confirmation(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Confirmation room", subtitle: "The app should help the group converge before any last-mile handoff.")

            NavigationLink {
                ConfirmationRoomView(planID: plan.id)
            } label: {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(plan.lifecycle.shortActionLabel)
                            .font(.headline)
                        Text(plan.lifecycle.summary)
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
}
