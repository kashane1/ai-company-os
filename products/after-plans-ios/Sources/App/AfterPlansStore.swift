import Foundation
import SwiftUI

@MainActor
final class AfterPlansStore: ObservableObject {
    @Published var hasCompletedOnboarding: Bool
    @Published var selectedTab: AppTab
    @Published var currentUser: UserProfile
    @Published var availableContexts: [ContextOption]
    @Published var selectedContext: ContextOption?
    @Published private(set) var plans: [AfterPlan]
    @Published private(set) var blockedUserNames: [String]
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
        plans: [AfterPlan],
        blockedUserNames: [String] = [],
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
        self.plans = plans
        self.blockedUserNames = blockedUserNames
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
        visiblePlans.sorted { lhs, rhs in
            rankingScore(for: lhs) > rankingScore(for: rhs)
        }
    }

    var livePlans: [AfterPlan] {
        visiblePlans.filter { $0.lifecycle != .closed }
    }

    var historyPlans: [AfterPlan] {
        visiblePlans.filter { $0.lifecycle == .closed }
    }

    var recentPartners: [String] {
        var names: [String] = []

        for participant in visiblePlans.flatMap(\.participants) where participant.name != currentUser.firstName {
            if !names.contains(participant.name) {
                names.append(participant.name)
            }
        }

        return Array(names.prefix(4))
    }

    var moderationNote: String {
        "Reports route to a founder-reviewed moderation queue in this shell. Backend moderation tooling is intentionally deferred."
    }

    func finishOnboarding() {
        hasCompletedOnboarding = true
        if selectedContext == nil {
            selectedContext = availableContexts.first
        }
        analyticsService.record(event: "signup_completed")
    }

    func selectContext(_ context: ContextOption) {
        selectedContext = context
        analyticsService.record(event: "context_selected")
    }

    func plan(with id: UUID) -> AfterPlan? {
        visiblePlans.first(where: { $0.id == id })
    }

    func invitePreview(for plan: AfterPlan) -> InvitePreview {
        inviteService.preview(for: plan)
    }

    func join(_ planID: UUID) {
        mutatePlan(id: planID) { [participationService, currentUser] plan in
            participationService.apply(.join, to: plan, currentUser: currentUser)
        }
        analyticsService.record(event: "join_tapped")
    }

    func expressInterest(in planID: UUID) {
        mutatePlan(id: planID) { [participationService, currentUser] plan in
            participationService.apply(.interested, to: plan, currentUser: currentUser)
        }
        analyticsService.record(event: "interested_tapped")
    }

    func suggestDefaultPlace(for planID: UUID) {
        guard let plan = plans.first(where: { $0.id == planID }) else { return }
        let defaults = ["Tea House", "Corner Slice", "Mercado", "Rooftop Coffee"]
        let suggestion = defaults[plan.placeSuggestions.count % defaults.count]

        mutatePlan(id: planID) { [participationService, currentUser] current in
            participationService.apply(.suggestPlace(suggestion), to: current, currentUser: currentUser)
        }
        analyticsService.record(event: "suggest_place_tapped")
    }

    func confirm(_ planID: UUID) {
        mutatePlan(id: planID) { [participationService, currentUser] plan in
            participationService.apply(.confirm, to: plan, currentUser: currentUser)
        }
        analyticsService.record(event: "plan_confirmed")
    }

    @discardableResult
    func createPlan(from draft: CreatePlanDraft) -> Bool {
        guard draft.validationMessage(hasContext: selectedContext != nil) == nil, let selectedContext else {
            return false
        }

        let plan = composerService.createPlan(from: draft, in: selectedContext, host: currentUser)
        plans.insert(plan, at: 0)
        selectedTab = .home
        analyticsService.record(event: "plan_created")
        return true
    }

    func reportPlan(_ plan: AfterPlan) {
        reportLog.append("Reported plan: \(plan.title)")
        analyticsService.record(event: "report_submitted")
    }

    func reportUser(named name: String) {
        reportLog.append("Reported user: \(name)")
        analyticsService.record(event: "report_submitted")
    }

    func blockUser(named name: String) {
        guard !blockedUserNames.contains(name) else { return }
        blockedUserNames.append(name)
        analyticsService.record(event: "block_user")
    }

    private var visiblePlans: [AfterPlan] {
        plans.filter { plan in
            !blockedUserNames.contains(plan.hostName) &&
                plan.participants.allSatisfy { !blockedUserNames.contains($0.name) }
        }
    }

    private func rankingScore(for plan: AfterPlan) -> Int {
        var score = 0

        if plan.contextTitle == selectedContext?.title {
            score += 100
        }

        switch plan.lifecycle {
        case .forming:
            score += 30
        case .confirmed:
            score += 25
        case .open:
            score += 20
        case .active:
            score += 15
        case .closed:
            score += 0
        }

        switch plan.visibility {
        case .sameContextOnly:
            score += 12
        case .knownPeople:
            score += 9
        case .inviteOnly:
            score += 6
        case .friendsOfParticipants:
            score += 2
        }

        return score + plan.joinedCount + plan.interestedCount
    }

    private func mutatePlan(id: UUID, transform: (AfterPlan) -> AfterPlan) {
        guard let index = plans.firstIndex(where: { $0.id == id }) else { return }
        plans[index] = transform(plans[index])
    }
}
