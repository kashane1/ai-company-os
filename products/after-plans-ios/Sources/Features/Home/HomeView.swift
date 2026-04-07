import SwiftUI

struct HomeView: View {
    @EnvironmentObject private var store: AfterPlansStore
    @State private var isShowingContextSelector = false
    @State private var isShowingCreatePlan = false
    @State private var invitePlan: AfterPlan?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Spacing.xl) {
                hero
                currentMoveSection
                contextSection
                discoverySection
            }
            .padding(Spacing.lg)
        }
        .navigationTitle("After Plans")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    isShowingCreatePlan = true
                } label: {
                    Image(systemName: "plus.circle.fill")
                }
            }
        }
        .sheet(isPresented: $isShowingContextSelector) {
            NavigationStack {
                ContextSelectionView()
            }
        }
        .sheet(isPresented: $isShowingCreatePlan) {
            NavigationStack {
                CreatePlanView()
            }
        }
        .sheet(item: $invitePlan) { plan in
            NavigationStack {
                InviteShareView(planID: plan.id)
            }
        }
    }

    private var hero: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            AppBadge(text: "Join-first continuation", tone: .appMomentum)

            Text("When the current thing ends, see or start what is next.")
                .font(.system(size: 28, weight: .bold, design: .rounded))
                .fixedSize(horizontal: false, vertical: true)

            Text(heroSubtitle)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            HStack(spacing: Spacing.sm) {
                Button("Start what's next") {
                    isShowingCreatePlan = true
                }
                .buttonStyle(ActionPillButtonStyle(prominent: true))

                Button("Share a plan") {
                    invitePlan = store.feedPlans.first
                }
                .buttonStyle(ActionPillButtonStyle())
            }

            if let message = store.lastActionMessage {
                Text(message)
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.appSafe)
            }
        }
        .appSurface(prominent: true)
    }

    private var currentMoveSection: some View {
        Group {
            if let plan = store.focusedPlan {
                VStack(alignment: .leading, spacing: Spacing.md) {
                    SectionHeader(
                        title: "Your current move",
                        subtitle: "The app should carry your latest join, create, or confirmation forward instead of dropping you into disconnected screens."
                    )

                    VStack(alignment: .leading, spacing: Spacing.md) {
                        HStack {
                            VStack(alignment: .leading, spacing: Spacing.xs) {
                                Text(plan.title)
                                    .font(.headline)
                                Text(plan.lifecycleHeadline)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }

                            Spacer()

                            AppBadge(text: plan.lifecycle.title, tone: .appMomentum)
                        }

                        Text(plan.nextStepGuidance)
                            .font(.footnote)
                            .foregroundStyle(.secondary)

                        HStack(spacing: Spacing.sm) {
                            NavigationLink("Open details") {
                                PlanDetailView(planID: plan.id)
                            }
                            .buttonStyle(ActionPillButtonStyle(prominent: true))

                            if plan.lifecycle.allowsConfirmationRoom {
                                NavigationLink("Confirmation room") {
                                    ConfirmationRoomView(planID: plan.id)
                                }
                                .buttonStyle(ActionPillButtonStyle())
                            }
                        }
                    }
                    .appSurface()
                }
            }
        }
    }

    private var contextSection: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(
                title: "Current context",
                subtitle: "The feed should feel anchored to what just happened, not to the entire city."
            )

            Button {
                isShowingContextSelector = true
            } label: {
                VStack(alignment: .leading, spacing: Spacing.sm) {
                    Text(store.selectedContext?.title ?? "Pick what just ended")
                        .font(.headline)
                        .foregroundStyle(.primary)
                    Text(contextSubtitle)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    HStack(spacing: Spacing.sm) {
                        AppBadge(text: store.selectedContext?.proximityLabel ?? "Context first")
                        AppBadge(text: store.selectedContext?.endedAtLabel ?? "Recent", tone: .appMomentum)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .appSurface()
            }
            .buttonStyle(.plain)
        }
    }

    private var discoverySection: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            if !store.currentContextPlans.isEmpty {
                SectionHeader(
                    title: "Happening after \(store.selectedContext?.title ?? "this")",
                    subtitle: "Current-context plans should win first so Home answers the question, “what is happening after this?”"
                )

                ForEach(store.currentContextPlans) { plan in
                    discoveryCard(for: plan, showContext: false)
                }
            } else {
                SectionHeader(
                    title: "Nothing started here yet",
                    subtitle: "If this context is quiet, starting a lightweight plan should still feel easier than spinning up an event."
                )

                Button("Start the first next plan") {
                    isShowingCreatePlan = true
                }
                .buttonStyle(ActionPillButtonStyle(prominent: true))
            }

            if !store.secondaryFeedPlans.isEmpty {
                SectionHeader(
                    title: "Also nearby from other recent contexts",
                    subtitle: "Secondary plans stay visible, but only after the current context is clear."
                )

                ForEach(store.secondaryFeedPlans) { plan in
                    discoveryCard(for: plan, showContext: true)
                }
            }
        }
    }

    private var heroSubtitle: String {
        if let context = store.selectedContext {
            return "Right now you're anchored to \(context.title). Shared context comes first so the app stays low-pressure, visible, and bounded."
        }

        return "Shared context comes first. The shell keeps the app low-pressure, visible, and bounded instead of feeling like an open public feed."
    }

    private var contextSubtitle: String {
        if let context = store.selectedContext {
            let count = store.currentContextPlans.count
            let noun = count == 1 ? "plan" : "plans"
            return "\(context.trustNote) \(count) \(noun) currently match this moment."
        }

        return "Choose a context before you publish or join."
    }

    @ViewBuilder
    private func discoveryCard(for plan: AfterPlan, showContext: Bool) -> some View {
        DiscoveryCardView(
            plan: plan,
            showContext: showContext,
            onJoin: { store.join(plan.id) },
            onInterested: { store.expressInterest(in: plan.id) },
            onSuggestPlace: { store.suggestDefaultPlace(for: plan.id) }
        )
    }
}

private struct DiscoveryCardView: View {
    let plan: AfterPlan
    let showContext: Bool
    let onJoin: () -> Void
    let onInterested: () -> Void
    let onSuggestPlace: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    Text(plan.title)
                        .font(.headline)
                    Text(plan.summary)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: Spacing.xs) {
                    AppBadge(text: plan.lifecycle.title, tone: .appMomentum)
                    AppBadge(text: plan.visibility.trustBadge)
                }
            }

            HStack(spacing: Spacing.sm) {
                InfoRow(icon: "mappin.and.ellipse", text: plan.venueLabel)
                InfoRow(icon: "clock", text: plan.timeLabel)
            }

            if showContext {
                InfoRow(icon: "sparkles.rectangle.stack", text: plan.contextTitle)
            }

            HStack(spacing: Spacing.sm) {
                InfoRow(icon: "person.2", text: plan.momentumLine)
                InfoRow(icon: "shield", text: plan.visibility.title)
            }

            Text(plan.trustBlurb)
                .font(.footnote)
                .foregroundStyle(.secondary)

            HStack(spacing: Spacing.sm) {
                Button(plan.joinActionTitle, action: onJoin)
                    .buttonStyle(ActionPillButtonStyle(prominent: true))
                    .disabled(!plan.canJoin)
                Button(plan.interestedActionTitle, action: onInterested)
                    .buttonStyle(ActionPillButtonStyle())
                    .disabled(!plan.canExpressInterest)
            }

            HStack(spacing: Spacing.sm) {
                Button(plan.suggestPlaceActionTitle, action: onSuggestPlace)
                    .buttonStyle(ActionPillButtonStyle())

                NavigationLink("Details") {
                    PlanDetailView(planID: plan.id)
                }
                .buttonStyle(ActionPillButtonStyle())
            }
        }
        .appSurface()
    }
}
