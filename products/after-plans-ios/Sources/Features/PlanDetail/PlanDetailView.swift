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
                        trustVisibility(plan)
                        momentum(plan)
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
                        if plan.canShareInvite {
                            Button {
                                isShowingInvite = true
                            } label: {
                                Image(systemName: "qrcode")
                            }
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
                    LifecycleBadgeView(lifecycle: plan.lifecycle)
                    AppBadge(text: plan.visibility.title)
                }
            }

            LifecycleProgressView(lifecycle: plan.lifecycle)

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

    private func trustVisibility(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Visibility & Safety", subtitle: "This should feel bounded to people from the moment, not like open local discovery.")

            Text(plan.visibilityHeadline)
                .font(.headline)

            Text(plan.visibilityDetail)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            HStack(spacing: Spacing.sm) {
                AppBadge(text: plan.visibility.trustBadge, tone: .appSafe)
                AppBadge(text: plan.visibility.title)
            }

            Text(plan.visibilityFootnote)
                .font(.footnote)
                .foregroundStyle(.secondary)

            Button(plan.safetyEntryTitle) {
                isShowingSafety = true
            }
            .buttonStyle(ActionPillButtonStyle())

            Text(plan.safetyEntryDetail)
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .appSurface()
    }

    private func actions(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Quick actions", subtitle: plan.lifecycleWindowDetail)

            HStack(spacing: Spacing.sm) {
                Button(plan.joinActionTitle) { store.join(plan.id) }
                    .buttonStyle(ActionPillButtonStyle(prominent: true))
                    .disabled(!plan.canJoin)
                Button(plan.interestedActionTitle) { store.expressInterest(in: plan.id) }
                    .buttonStyle(ActionPillButtonStyle())
                    .disabled(!plan.canExpressInterest)
            }

            HStack(spacing: Spacing.sm) {
                Button(plan.suggestPlaceActionTitle) { store.suggestDefaultPlace(for: plan.id) }
                    .buttonStyle(ActionPillButtonStyle())
                    .disabled(!plan.canSuggestPlace)
                Button(plan.shareActionTitle) { isShowingInvite = true }
                    .buttonStyle(ActionPillButtonStyle())
                    .disabled(!plan.canShareInvite)
            }

            Text(plan.shareActionSubtitle)
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .appSurface()
    }

    private func momentum(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Momentum", subtitle: "The detail view should make the plan lifecycle readable at a glance.")

            Text(plan.lifecycleHeadline)
                .font(.headline)

            Text(plan.nextStepGuidance)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Text(plan.lifecycleWindowTitle)
                .font(.footnote.weight(.semibold))
                .foregroundStyle(.secondary)

            HStack(spacing: Spacing.sm) {
                AppBadge(text: plan.mode.title)
                AppBadge(text: plan.visibility.trustBadge, tone: .appSafe)
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

            if plan.lifecycle.allowsConfirmationRoom {
                NavigationLink {
                    ConfirmationRoomView(planID: plan.id)
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(plan.lifecycle.shortActionLabel)
                                .font(.headline)
                            Text(plan.confirmationRoomSubtitle)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Image(systemName: "chevron.right")
                            .foregroundStyle(.secondary)
                    }
                }
            } else {
                VStack(alignment: .leading, spacing: 4) {
                    Text(plan.lifecycle.shortActionLabel)
                        .font(.headline)
                    Text("Closed plans stay readable here, but the confirmation room is no longer actionable.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .appSurface()
    }
}
