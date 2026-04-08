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
        .background(Color.appBackground.ignoresSafeArea())
        .navigationTitle("After Plans")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    isShowingCreatePlan = true
                } label: {
                    Image(systemName: "plus.circle.fill")
                        .imageScale(.large)
                }
            }
        }
        .sheet(isPresented: $isShowingContextSelector) {
            NavigationStack { ContextSelectionView() }
        }
        .sheet(isPresented: $isShowingCreatePlan) {
            NavigationStack { CreatePlanView() }
        }
        .sheet(item: $invitePlan) { plan in
            NavigationStack { InviteShareView(planID: plan.id) }
        }
    }

    // MARK: - Hero

    private var hero: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            if let context = store.selectedContext {
                AppBadge(text: context.title, tone: .appMomentum)
            }

            Text(store.selectedContext != nil
                 ? "Keep the moment going."
                 : "Catch what happens after.")
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

                if !store.feedPlans.isEmpty {
                    Button {
                        invitePlan = store.feedPlans.first
                    } label: {
                        Image(systemName: "square.and.arrow.up")
                            .font(.system(size: 16, weight: .semibold))
                            .frame(width: 44, height: 44)
                            .background(Color.black.opacity(0.055), in: Circle())
                            .foregroundStyle(Color.primary)
                    }
                }
            }

            if let message = store.lastActionMessage {
                Text(message)
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.appSafe)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .animation(.easeInOut(duration: 0.3), value: store.lastActionMessage != nil)
        .appSurface(prominent: true)
    }

    // MARK: - Current move

    private var currentMoveSection: some View {
        Group {
            if let plan = store.focusedPlan {
                VStack(alignment: .leading, spacing: Spacing.md) {
                    Label("Your current move", systemImage: "arrow.right.circle.fill")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(Color.appMomentum)

                    HStack {
                        VStack(alignment: .leading, spacing: Spacing.xs) {
                            Text(plan.title)
                                .font(.headline)
                            Text(plan.lifecycleHeadline)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        LifecycleBadgeView(lifecycle: plan.lifecycle)
                    }

                    LifecycleProgressView(lifecycle: plan.lifecycle)

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
                .appSurface(tint: plan.lifecycle == .forming ? .appMomentum : (plan.lifecycle == .confirmed ? .appSafe : nil))
            }
        }
    }

    // MARK: - Context chip

    private var contextSection: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(
                title: "Current context",
                subtitle: store.selectedContext == nil ? "Choose what just ended to unlock the feed." : ""
            )

            Button {
                isShowingContextSelector = true
            } label: {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: Spacing.sm) {
                        Text(store.selectedContext?.title ?? "What just ended?")
                            .font(.headline)
                            .foregroundStyle(.primary)
                        Text(contextSubtitle)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        HStack(spacing: Spacing.sm) {
                            AppBadge(
                                text: store.selectedContext?.proximityLabel ?? "Choose context",
                                tone: store.selectedContext == nil ? .appAccent : .appMomentum
                            )
                            if let context = store.selectedContext {
                                AppBadge(text: context.endedAtLabel, tone: .appMomentum)
                            }
                        }
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(.tertiary)
                        .padding(.top, 3)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .appSurface()
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Discovery

    private var discoverySection: some View {
        VStack(alignment: .leading, spacing: Spacing.xl) {
            primaryDiscovery
            if !store.secondaryFeedPlans.isEmpty {
                secondaryDiscovery
            }
        }
    }

    @ViewBuilder
    private var primaryDiscovery: some View {
        if !store.currentContextPlans.isEmpty {
            VStack(alignment: .leading, spacing: Spacing.md) {
                SectionHeader(
                    title: "Happening after \(store.selectedContext?.title ?? "this")",
                    subtitle: "Plans from people in the same moment."
                )
                VStack(spacing: Spacing.lg) {
                    ForEach(store.currentContextPlans) { plan in
                        discoveryCard(for: plan, showContext: false)
                    }
                }
            }
        } else if store.selectedContext != nil {
            emptyFeedCard(
                icon: "plus.circle.dashed",
                title: "Nothing started here yet",
                body: "Be the first to start a plan after \(store.selectedContext!.title).",
                ctaLabel: "Start what's next",
                ctaAction: { isShowingCreatePlan = true }
            )
        } else {
            emptyFeedCard(
                icon: "sparkles.rectangle.stack",
                title: "Set your context first",
                body: "Choose what just ended to see plans from people you were around.",
                ctaLabel: "Choose context",
                ctaAction: { isShowingContextSelector = true }
            )
        }
    }

    @ViewBuilder
    private var secondaryDiscovery: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(
                title: "Also nearby",
                subtitle: "Plans from other recent contexts."
            )
            VStack(spacing: Spacing.lg) {
                ForEach(store.secondaryFeedPlans) { plan in
                    discoveryCard(for: plan, showContext: true)
                }
            }
        }
    }

    // MARK: - Empty feed card

    private func emptyFeedCard(
        icon: String,
        title: String,
        body: String,
        ctaLabel: String,
        ctaAction: @escaping () -> Void
    ) -> some View {
        VStack(alignment: .center, spacing: Spacing.md) {
            Image(systemName: icon)
                .font(.system(size: 34, weight: .light))
                .foregroundStyle(Color.appAccent.opacity(0.38))
                .padding(.bottom, Spacing.xs)

            VStack(alignment: .center, spacing: Spacing.xs) {
                Text(title)
                    .font(.headline)
                Text(body)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }

            Button(ctaLabel, action: ctaAction)
                .buttonStyle(ActionPillButtonStyle(prominent: true))
        }
        .frame(maxWidth: .infinity)
        .appSurface()
    }

    // MARK: - Helpers

    private var heroSubtitle: String {
        if let context = store.selectedContext {
            return "See who's planning their next move after \(context.title)."
        }
        return "Set a context to see plans from people you were just around."
    }

    private var contextSubtitle: String {
        if let context = store.selectedContext {
            let count = store.currentContextPlans.count
            let noun = count == 1 ? "plan" : "plans"
            return "\(context.trustNote) \(count) \(noun) right now."
        }
        return "Tap to choose what just ended."
    }

    @ViewBuilder
    private func discoveryCard(for plan: AfterPlan, showContext: Bool) -> some View {
        DiscoveryCardView(
            plan: plan,
            affinity: store.affinity(for: plan.id),
            showContext: showContext,
            onJoin: { store.join(plan.id) },
            onInterested: { store.expressInterest(in: plan.id) },
            onSuggestPlace: { store.suggestDefaultPlace(for: plan.id) }
        )
    }
}

// MARK: - Discovery card

private struct DiscoveryCardView: View {
    let plan: AfterPlan
    let affinity: PlanAffinity?
    let showContext: Bool
    let onJoin: () -> Void
    let onInterested: () -> Void
    let onSuggestPlace: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {

            // 1. Identity — title + lifecycle badge only (clean header)
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    Text(plan.title)
                        .font(.headline)
                    Text(plan.summary)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
                Spacer(minLength: Spacing.sm)
                LifecycleBadgeView(lifecycle: plan.lifecycle)
            }

            // 2. Compact meta — one line, no icon overflow risk
            Text(planMetaLine)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .lineLimit(2)

            // 2b. Join-confidence cue — lightweight readiness signal
            if !plan.joinConfidenceCue.isEmpty {
                Text(plan.joinConfidenceCue)
                    .font(.footnote.weight(.medium))
                    .foregroundStyle(confidenceCueColor)
            }

            if showContext {
                InfoRow(icon: "sparkles.rectangle.stack", text: plan.contextTitle)
            }

            // 3. Trust signal — callout if strong affinity, quiet blurb if not
            trustSignalView

            // 4. Actions first — join before context/lifecycle (low-pressure)
            if plan.canJoin || plan.canExpressInterest {
                HStack(spacing: Spacing.sm) {
                    if plan.canJoin {
                        Button(plan.joinActionTitle, action: onJoin)
                            .buttonStyle(ActionPillButtonStyle(prominent: true))
                    }
                    if plan.canExpressInterest {
                        Button(plan.interestedActionTitle, action: onInterested)
                            .buttonStyle(ActionPillButtonStyle())
                    }
                }
            }

            // 5. Momentum context
            LifecycleProgressView(lifecycle: plan.lifecycle, compact: true)

            // 6. Footer
            CardDivider()

            HStack {
                if plan.canSuggestPlace {
                    Button(plan.suggestPlaceActionTitle, action: onSuggestPlace)
                        .buttonStyle(ActionPillButtonStyle())
                }
                Spacer()
                NavigationLink {
                    PlanDetailView(planID: plan.id)
                } label: {
                    HStack(spacing: 4) {
                        Text("View details")
                        Image(systemName: "chevron.right")
                            .font(.caption.weight(.bold))
                    }
                    .font(.subheadline.weight(.medium))
                }
                .buttonStyle(TextLinkButtonStyle())
            }
        }
        .appSurface(tint: hasTrustSignal ? .appSafe : nil)
    }

    // MARK: - Helpers

    private var hasTrustSignal: Bool {
        guard let affinity else { return false }
        return !affinity.badges.isEmpty
    }

    private var confidenceCueColor: Color {
        switch plan.lifecycle {
        case .confirmed, .active: return .appSafe
        case .forming:            return .appMomentum
        default:                  return .secondary
        }
    }

    private var planMetaLine: String {
        [plan.venueLabel, plan.timeLabel, plan.momentumLine]
            .filter { !$0.isEmpty }
            .joined(separator: " · ")
    }

    @ViewBuilder
    private var trustSignalView: some View {
        if let affinity, !affinity.badges.isEmpty {
            // Strong affinity — highlighted callout
            HStack(spacing: Spacing.xs) {
                Image(systemName: "person.2.fill")
                    .font(.caption.weight(.semibold))
                Text(affinity.detailLine.isEmpty
                     ? affinity.badges.prefix(3).joined(separator: " · ")
                     : affinity.detailLine)
                    .font(.footnote.weight(.semibold))
            }
            .foregroundStyle(Color.appSafe)
            .padding(.horizontal, Spacing.sm)
            .padding(.vertical, 7)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                Color.appSafe.opacity(0.08),
                in: RoundedRectangle(cornerRadius: 10, style: .continuous)
            )
        } else {
            // No affinity — quiet blurb with consistent icon presence
            HStack(spacing: Spacing.xs) {
                Image(systemName: "person.2")
                    .font(.caption)
                Text(plan.trustBlurb)
                    .font(.footnote)
            }
            .foregroundStyle(.secondary)
        }
    }
}
