import SwiftUI

struct ActivityView: View {
    @EnvironmentObject private var store: AfterPlansStore

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Spacing.xl) {
                recapHeader
                recentPartnersSection
                liveSection
                historySection
            }
            .padding(Spacing.lg)
        }
        .background(Color.appBackground.ignoresSafeArea())
        .navigationTitle("Activity")
    }

    // MARK: - Recap header

    private var recapHeader: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            Label("Your continuation history", systemImage: "arrow.trianglehead.2.counterclockwise.rotate.90")
                .font(.caption.weight(.semibold))
                .foregroundStyle(Color.appSafe)

            Text(store.recapSummary.headline)
                .font(.system(size: 22, weight: .bold, design: .rounded))
                .fixedSize(horizontal: false, vertical: true)

            Text(store.recapSummary.detail)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            if !store.recapSummary.distinctContextsFollowedThrough.isEmpty {
                HStack(spacing: Spacing.xs) {
                    ForEach(store.recapSummary.distinctContextsFollowedThrough, id: \.self) { context in
                        AppBadge(text: context, tone: .appSafe)
                    }
                }
            }
        }
        .appSurface(prominent: true, tint: .appSafe)
    }

    // MARK: - Recent partners

    @ViewBuilder
    private var recentPartnersSection: some View {
        if !store.recentPartners.isEmpty {
            VStack(alignment: .leading, spacing: Spacing.md) {
                SectionHeader(
                    title: "People you've planned with",
                    subtitle: "Familiar faces from recent continuations."
                )
                HStack(spacing: Spacing.sm) {
                    ForEach(store.recentPartners, id: \.self) { name in
                        HStack(spacing: Spacing.xs) {
                            ParticipantAvatar(name: name, size: 28, color: .appAccent)
                            Text(name)
                                .font(.footnote.weight(.medium))
                        }
                    }
                }
            }
            .appSurface()
        }
    }

    // MARK: - Live section

    private var liveSection: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(
                title: "Live now",
                subtitle: store.livePlans.isEmpty
                    ? "Nothing live right now."
                    : "\(store.livePlans.count) \(store.livePlans.count == 1 ? "plan" : "plans") in progress."
            )

            if store.livePlans.isEmpty {
                HStack(spacing: Spacing.sm) {
                    Image(systemName: "moon")
                        .foregroundStyle(Color.appAccent.opacity(0.38))
                    Text("Plans you join or create will appear here while they're active.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            } else {
                ForEach(store.livePlans) { plan in
                    livePlanRow(plan)
                }
            }
        }
        .appSurface()
    }

    private func livePlanRow(_ plan: AfterPlan) -> some View {
        NavigationLink {
            PlanDetailView(planID: plan.id)
        } label: {
            HStack(spacing: Spacing.sm) {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    Text(plan.title)
                        .font(.headline)
                    Text(plan.contextTitle)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text(plan.joinConfidenceCue)
                        .font(.footnote.weight(.medium))
                        .foregroundStyle(plan.lifecycle == .confirmed || plan.lifecycle == .active ? Color.appSafe : Color.appMomentum)
                }
                Spacer()
                LifecycleBadgeView(lifecycle: plan.lifecycle)
            }
            .padding(.vertical, 3)
        }
        .buttonStyle(.plain)
    }

    // MARK: - History section

    private var historySection: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(
                title: "Recent follow-throughs",
                subtitle: store.historyPlans.isEmpty
                    ? "Closed plans will appear here."
                    : "Continuations that happened."
            )

            if store.historyPlans.isEmpty {
                HStack(spacing: Spacing.sm) {
                    Image(systemName: "clock.arrow.circlepath")
                        .foregroundStyle(Color.appAccent.opacity(0.38))
                    Text("When a plan wraps, it becomes part of your continuation history.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            } else {
                ForEach(store.historyPlans) { plan in
                    historyPlanRow(plan)
                }
            }
        }
        .appSurface()
    }

    private func historyPlanRow(_ plan: AfterPlan) -> some View {
        NavigationLink {
            PlanDetailView(planID: plan.id)
        } label: {
            VStack(alignment: .leading, spacing: Spacing.xs) {
                HStack {
                    Text(plan.title)
                        .font(.headline)
                    Spacer()
                    LifecycleBadgeView(lifecycle: plan.lifecycle)
                }
                Text("\(plan.contextTitle) · \(plan.venueLabel)")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                if !plan.recapLine.isEmpty {
                    Text(plan.recapLine)
                        .font(.footnote.weight(.medium))
                        .foregroundStyle(Color.appSafe)
                }
                if let affinity = store.affinity(for: plan.id), !affinity.badges.isEmpty {
                    HStack(spacing: Spacing.xs) {
                        ForEach(affinity.badges.prefix(3), id: \.self) { badge in
                            AppBadge(text: badge, tone: .appSafe)
                        }
                    }
                }
            }
            .padding(.vertical, 3)
        }
        .buttonStyle(.plain)
    }
}
