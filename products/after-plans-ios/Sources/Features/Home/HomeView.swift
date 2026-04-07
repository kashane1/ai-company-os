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

            Text("Shared context comes first. The shell keeps the app low-pressure, visible, and bounded instead of feeling like an open public feed.")
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
        }
        .appSurface(prominent: true)
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
                    Text(store.selectedContext?.trustNote ?? "Choose a context before you publish or join.")
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
            SectionHeader(
                title: "What is next",
                subtitle: "A believable shell for ranked continuation cards. Server ranking and social memory come later."
            )

            ForEach(store.feedPlans) { plan in
                DiscoveryCardView(
                    plan: plan,
                    onJoin: { store.join(plan.id) },
                    onInterested: { store.expressInterest(in: plan.id) },
                    onSuggestPlace: { store.suggestDefaultPlace(for: plan.id) }
                )
            }
        }
    }
}

private struct DiscoveryCardView: View {
    let plan: AfterPlan
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

            HStack(spacing: Spacing.sm) {
                InfoRow(icon: "person.2", text: plan.momentumLine)
                InfoRow(icon: "shield", text: plan.visibility.title)
            }

            Text(plan.trustBlurb)
                .font(.footnote)
                .foregroundStyle(.secondary)

            HStack(spacing: Spacing.sm) {
                Button("Join", action: onJoin)
                    .buttonStyle(ActionPillButtonStyle(prominent: true))
                Button("Interested", action: onInterested)
                    .buttonStyle(ActionPillButtonStyle())
            }

            HStack(spacing: Spacing.sm) {
                Button("Suggest place", action: onSuggestPlace)
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
