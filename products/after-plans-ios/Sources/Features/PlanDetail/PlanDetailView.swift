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
                        actions(plan)         // near top — user came here to act
                        people(plan)          // social proof second
                        suggestions(plan)
                        trustLine(plan)       // compressed single-line trust row
                        confirmation(plan)
                    }
                    .padding(Spacing.lg)
                }
                .background(Color.appBackground.ignoresSafeArea())
                .navigationTitle(plan.title)
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItemGroup(placement: .topBarTrailing) {
                        if plan.canShareInvite {
                            Button {
                                isShowingInvite = true
                            } label: {
                                Image(systemName: "square.and.arrow.up")
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
                    NavigationStack { InviteShareView(planID: plan.id) }
                }
                .sheet(isPresented: $isShowingSafety) {
                    NavigationStack { SafetyCenterView(focusedPlanID: plan.id) }
                }
            } else {
                ContentUnavailableView(
                    "Plan unavailable",
                    systemImage: "eye.slash",
                    description: Text("This plan is no longer visible to you.")
                )
            }
        }
    }

    // MARK: - Header (hero card)
    // Integrates: identity, lifecycle, trust blurb, key facts, next-step guidance.
    // The separate momentum card from earlier passes is absorbed here.

    private func header(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            // Identity + lifecycle state
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    Text(plan.title)
                        .font(.system(size: 26, weight: .bold, design: .rounded))
                    Text(plan.summary)
                        .font(.body)
                        .foregroundStyle(.secondary)
                }
                Spacer(minLength: Spacing.sm)
                VStack(alignment: .trailing, spacing: Spacing.xs) {
                    LifecycleBadgeView(lifecycle: plan.lifecycle)
                    AppBadge(text: plan.visibility.title)
                }
            }

            LifecycleProgressView(lifecycle: plan.lifecycle)

            // What to do next — prominent guidance
            Text(plan.nextStepGuidance)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            CardDivider()

            // Key facts
            HStack(spacing: Spacing.md) {
                InfoRow(icon: "sparkles.rectangle.stack", text: plan.contextTitle)
                InfoRow(icon: "clock", text: plan.timeLabel)
            }
            HStack(spacing: Spacing.md) {
                InfoRow(icon: "mappin.and.ellipse", text: plan.venueLabel)
                InfoRow(icon: "person.3", text: plan.momentumLine)
            }

            // Trust context
            Text(plan.trustBlurb)
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .appSurface(prominent: true, tint: headerTint(plan))
    }

    private func headerTint(_ plan: AfterPlan) -> Color? {
        switch plan.lifecycle {
        case .forming:   return .appMomentum
        case .confirmed: return .appSafe
        case .active:    return .appSafe
        default:         return nil
        }
    }

    // MARK: - Actions (shown only when something is actionable)

    @ViewBuilder
    private func actions(_ plan: AfterPlan) -> some View {
        if plan.canJoin || plan.canExpressInterest || plan.canSuggestPlace || plan.canShareInvite {
            VStack(alignment: .leading, spacing: Spacing.md) {
                SectionHeader(title: "Actions", subtitle: plan.lifecycleWindowDetail)

                if plan.canJoin || plan.canExpressInterest {
                    HStack(spacing: Spacing.sm) {
                        if plan.canJoin {
                            Button(plan.joinActionTitle) { store.join(plan.id) }
                                .buttonStyle(ActionPillButtonStyle(prominent: true))
                        }
                        if plan.canExpressInterest {
                            Button(plan.interestedActionTitle) { store.expressInterest(in: plan.id) }
                                .buttonStyle(ActionPillButtonStyle())
                        }
                    }
                }

                if plan.canSuggestPlace || plan.canShareInvite {
                    HStack(spacing: Spacing.sm) {
                        if plan.canSuggestPlace {
                            Button(plan.suggestPlaceActionTitle) { store.suggestDefaultPlace(for: plan.id) }
                                .buttonStyle(ActionPillButtonStyle())
                        }
                        if plan.canShareInvite {
                            Button(plan.shareActionTitle) { isShowingInvite = true }
                                .buttonStyle(ActionPillButtonStyle())
                        }
                    }
                }

                if plan.canShareInvite {
                    Text(plan.shareActionSubtitle)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .appSurface()
        }
    }

    // MARK: - People (with participant avatar circles)

    private func people(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            let count = plan.participants.count
            SectionHeader(
                title: "Who's in",
                subtitle: count == 0 ? "No one yet." : "\(count) \(count == 1 ? "person" : "people")"
            )

            if plan.participants.isEmpty {
                HStack(spacing: Spacing.sm) {
                    Image(systemName: "person.crop.circle.badge.plus")
                        .foregroundStyle(Color.appAccent.opacity(0.4))
                    Text("Invite the first person to join.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            } else {
                ForEach(Array(plan.participants.enumerated()), id: \.element.id) { index, participant in
                    if index > 0 {
                        CardDivider()
                    }
                    HStack(spacing: Spacing.md) {
                        ParticipantAvatar(
                            name: participant.name,
                            color: participant.isOrganizer ? .appSafe : .appAccent
                        )
                        VStack(alignment: .leading, spacing: 2) {
                            Text(participant.name)
                                .font(.subheadline.weight(.semibold))
                            Text(participant.descriptor)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        if participant.isOrganizer {
                            AppBadge(text: "Host", tone: .appSafe)
                        } else if participant.isKnown {
                            AppBadge(text: "Known")
                        }
                    }
                    .padding(.vertical, 3)
                }
            }
        }
        .appSurface()
    }

    // MARK: - Suggestions

    private func suggestions(_ plan: AfterPlan) -> some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Place suggestions", subtitle: "Suggest a spot for the group.")

            if plan.placeSuggestions.isEmpty {
                HStack(spacing: Spacing.sm) {
                    Image(systemName: "mappin.circle")
                        .foregroundStyle(Color.appAccent.opacity(0.4))
                    Text("No suggestions yet. Be the first.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            } else {
                ForEach(plan.placeSuggestions, id: \.self) { suggestion in
                    HStack {
                        Image(systemName: "mappin.and.ellipse")
                            .font(.footnote)
                            .foregroundStyle(Color.appAccent.opacity(0.5))
                        Text(suggestion)
                            .font(.subheadline)
                        Spacer()
                    }
                    .padding(.vertical, 2)
                }
            }
        }
        .appSurface()
    }

    // MARK: - Trust line (compressed, single row)

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

    // MARK: - Confirmation room entry

    @ViewBuilder
    private func confirmation(_ plan: AfterPlan) -> some View {
        if plan.lifecycle.allowsConfirmationRoom {
            VStack(alignment: .leading, spacing: Spacing.md) {
                SectionHeader(title: "Confirmation room", subtitle: "Final coordination before you head out.")

                CardDivider()

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
            }
            .appSurface(tint: headerTint(plan))
        }
    }
}
