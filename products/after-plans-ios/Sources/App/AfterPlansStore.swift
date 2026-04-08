import Foundation
import SwiftUI

@MainActor
final class AfterPlansStore: ObservableObject {
    @Published var hasCompletedOnboarding: Bool
    @Published var selectedTab: AppTab
    @Published var currentUser: UserProfile
    @Published var availableContexts: [ContextOption]
    @Published var selectedContext: ContextOption?
    @Published var focusedPlanID: UUID?
    @Published private(set) var lastActionMessage: String?
    @Published private(set) var plans: [AfterPlan]
    @Published private(set) var blockedUserNames: [String]
    @Published private(set) var inviteShareStates: [UUID: InviteShareState]
    @Published private(set) var reportLog: [String]

    let reportReasons: [SafetyReason]

    private let composerService: PlanComposerService
    private let participationService: PlanParticipationService
    private let inviteService: InviteService
    private let analyticsService: AnalyticsService

    init(
        hasCompletedOnboarding: Bool = false,
        selectedTab: AppTab = .home,
        currentUser: UserProfile,
        availableContexts: [ContextOption],
        selectedContext: ContextOption?,
        focusedPlanID: UUID? = nil,
        plans: [AfterPlan],
        blockedUserNames: [String] = [],
        inviteShareStates: [UUID: InviteShareState] = [:],
        reportLog: [String] = [],
        reportReasons: [SafetyReason],
        composerService: PlanComposerService,
        participationService: PlanParticipationService,
        inviteService: InviteService,
        analyticsService: AnalyticsService
    ) {
        self.hasCompletedOnboarding = hasCompletedOnboarding
        self.selectedTab = selectedTab
        self.currentUser = currentUser
        self.availableContexts = availableContexts
        self.selectedContext = selectedContext
        self.focusedPlanID = focusedPlanID
        self.plans = plans
        self.blockedUserNames = blockedUserNames
        self.inviteShareStates = inviteShareStates
        self.reportLog = reportLog
        self.reportReasons = reportReasons
        self.composerService = composerService
        self.participationService = participationService
        self.inviteService = inviteService
        self.analyticsService = analyticsService
    }

    static func bootstrap() -> AfterPlansStore {
        let auth = InMemoryAuthService()
        let contexts = InMemoryContextService().suggestedContexts()
        return AfterPlansStore(
            currentUser: auth.currentUser(),
            availableContexts: contexts,
            selectedContext: contexts.first,
            plans: InMemoryDiscoveryFeedService(contexts: contexts).seededPlans(),
            reportReasons: InMemorySafetyService().reportReasons,
            composerService: InMemoryPlanComposerService(),
            participationService: InMemoryPlanParticipationService(),
            inviteService: InMemoryInviteService(),
            analyticsService: NoopAnalyticsService()
        )
    }

    var feedPlans: [AfterPlan] {
        continuation.rankedPlans
    }

    var currentContextPlans: [AfterPlan] {
        continuation.currentContextPlans
    }

    var secondaryFeedPlans: [AfterPlan] {
        continuation.secondaryPlans
    }

    var focusedPlan: AfterPlan? {
        continuation.focusedPlan
    }

    var livePlans: [AfterPlan] {
        continuation.livePlans
    }

    var historyPlans: [AfterPlan] {
        continuation.historyPlans
    }

    var recentPartners: [String] {
        continuation.recentPartners
    }

    var recapSummary: RecapSummary {
        continuation.recapSummary
    }

    func affinity(for planID: UUID) -> PlanAffinity? {
        continuation.affinity(for: planID)
    }

    var moderationNote: String {
        "Reports route to a founder-reviewed moderation queue in this shell. Backend moderation tooling is intentionally deferred."
    }

    var blockEffectNote: String {
        "Blocked hosts or participants disappear from your visible plan surfaces in this shell."
    }

    func finishOnboarding() {
        hasCompletedOnboarding = true
        if selectedContext == nil {
            selectedContext = availableContexts.first
        }
        focusedPlanID = continuation.currentContextPlans.first?.id
        analyticsService.record(event: "signup_completed")
    }

    func selectContext(_ context: ContextOption) {
        selectedContext = context
        focusedPlanID = continuation.currentContextPlans.first?.id
        lastActionMessage = "Showing what's next after \(context.title)."
        analyticsService.record(event: "context_selected")
    }

    func plan(with id: UUID) -> AfterPlan? {
        continuation.plan(with: id)
    }

    func invitePreview(for plan: AfterPlan) -> InvitePreview {
        inviteService.preview(for: plan)
    }

    func inviteShareState(for planID: UUID) -> InviteShareState? {
        inviteShareStates[planID]
    }

    func inviteChannels(for plan: AfterPlan) -> [InviteShareChannel] {
        plan.inviteChannels
    }

    func join(_ planID: UUID) {
        mutatePlan(id: planID) { [participationService, currentUser] plan in
            participationService.apply(.join, to: plan, currentUser: currentUser)
        }
        focus(on: planID)
        if let plan = plan(with: planID) {
            lastActionMessage = "You're in for \(plan.title)."
        }
        analyticsService.record(event: "join_tapped")
    }

    func expressInterest(in planID: UUID) {
        mutatePlan(id: planID) { [participationService, currentUser] plan in
            participationService.apply(.interested, to: plan, currentUser: currentUser)
        }
        focus(on: planID)
        if let plan = plan(with: planID) {
            lastActionMessage = "Marked interest in \(plan.title)."
        }
        analyticsService.record(event: "interested_tapped")
    }

    func suggestDefaultPlace(for planID: UUID) {
        guard let existingPlan = plans.first(where: { $0.id == planID }) else { return }
        let defaults = ["Tea House", "Corner Slice", "Mercado", "Rooftop Coffee"]
        let suggestion = defaults[existingPlan.placeSuggestions.count % defaults.count]

        mutatePlan(id: planID) { [participationService, currentUser] current in
            participationService.apply(.suggestPlace(suggestion), to: current, currentUser: currentUser)
        }
        focus(on: planID)
        if let plan = plan(with: planID) {
            lastActionMessage = "Suggested \(suggestion) for \(plan.title)."
        }
        analyticsService.record(event: "suggest_place_tapped")
    }

    func confirm(_ planID: UUID) {
        mutatePlan(id: planID) { [participationService, currentUser] plan in
            participationService.apply(.confirm, to: plan, currentUser: currentUser)
        }
        focus(on: planID)
        if let plan = plan(with: planID) {
            lastActionMessage = "\(plan.title) is now locked for \(plan.timeLabel)."
        }
        analyticsService.record(event: "plan_confirmed")
    }

    func markPlanActive(_ planID: UUID) {
        mutatePlan(id: planID) { plan in
            var updated = plan
            updated.lifecycle = .active
            if updated.participationState == .joined {
                updated.participationState = .confirmed
            }
            return updated
        }
        focus(on: planID)
        if let plan = plan(with: planID) {
            lastActionMessage = "\(plan.title) is now in motion."
        }
        analyticsService.record(event: "plan_active")
    }

    func wrapPlan(_ planID: UUID) {
        mutatePlan(id: planID) { plan in
            var updated = plan
            updated.lifecycle = .closed
            return updated
        }
        if let plan = plan(with: planID) {
            lastActionMessage = "\(plan.title) is wrapped. Check your activity for the recap."
        }
        analyticsService.record(event: "plan_closed")
    }

    func prepareInviteShare(for planID: UUID, channel: InviteShareChannel) {
        guard let plan = plan(with: planID), plan.inviteChannels.contains(channel) else { return }

        let state = InviteShareState(
            channel: channel,
            statusTitle: shareStatusTitle(for: plan, channel: channel),
            statusDetail: shareStatusDetail(for: plan, channel: channel)
        )

        inviteShareStates[planID] = state
        focus(on: planID)
        lastActionMessage = state.statusTitle
        analyticsService.record(event: "invite_share_prepared")
    }

    func runConfirmationAction(for planID: UUID) {
        guard let plan = plan(with: planID) else { return }

        switch plan.confirmationAction {
        case .join:
            join(planID)
        case .confirm:
            confirm(planID)
        case .markActive:
            markPlanActive(planID)
        case .wrapPlan:
            wrapPlan(planID)
        case .none:
            break
        }
    }

    @discardableResult
    func createPlan(from draft: CreatePlanDraft) -> Bool {
        guard draft.validationMessage(hasContext: selectedContext != nil) == nil, let selectedContext else {
            return false
        }

        let plan = composerService.createPlan(from: draft, in: selectedContext, host: currentUser)
        plans.insert(plan, at: 0)
        focus(on: plan.id)
        lastActionMessage = "Your plan is live for \(selectedContext.title)."
        selectedTab = .home
        analyticsService.record(event: "plan_created")
        return true
    }

    func reportPlan(_ plan: AfterPlan) {
        reportLog.append("Reported plan: \(plan.title)")
        focus(on: plan.id)
        analyticsService.record(event: "report_submitted")
    }

    func reportUser(named name: String) {
        reportLog.append("Reported user: \(name)")
        analyticsService.record(event: "report_submitted")
    }

    func blockUser(named name: String) {
        guard !blockedUserNames.contains(name) else { return }
        blockedUserNames.append(name)
        if let focusedPlan, focusedPlan.hostName == name || focusedPlan.participants.contains(where: { $0.name == name }) {
            focusedPlanID = continuation.currentContextPlans.first?.id
        }
        analyticsService.record(event: "block_user")
    }

    private var continuation: ContinuationLoop {
        ContinuationLoop(
            plans: plans,
            selectedContext: selectedContext,
            blockedUserNames: blockedUserNames,
            currentUserName: currentUser.firstName,
            focusedPlanID: focusedPlanID
        )
    }

    private func mutatePlan(id: UUID, transform: (AfterPlan) -> AfterPlan) {
        guard let index = plans.firstIndex(where: { $0.id == id }) else { return }
        plans[index] = transform(plans[index])
    }

    private func focus(on planID: UUID) {
        focusedPlanID = planID
    }

    private func shareStatusTitle(for plan: AfterPlan, channel: InviteShareChannel) -> String {
        switch channel {
        case .sameContext:
            "Ready to share \(plan.title) with people from \(plan.contextTitle)."
        case .knownPeople:
            "Ready to send a low-pressure invite for \(plan.title)."
        case .nearbyQR:
            "QR handoff is ready for people already nearby."
        }
    }

    private func shareStatusDetail(for plan: AfterPlan, channel: InviteShareChannel) -> String {
        switch channel {
        case .sameContext:
            return "Use this if the plan still needs a couple quick joins from the same moment."
        case .knownPeople:
            return "Use this for a few familiar people who are likely to say yes without needing extra context."
        case .nearbyQR:
            if plan.lifecycle == .confirmed {
                return "Use this in person for the last right people instead of widening the plan further."
            }

            return "Use this in person so people already around can join without turning this into generic outreach."
        }
    }
}
