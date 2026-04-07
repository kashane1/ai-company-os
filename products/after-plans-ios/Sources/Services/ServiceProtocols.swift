import Foundation

protocol AuthService {
    func currentUser() -> UserProfile
}

protocol ContextService {
    func suggestedContexts() -> [ContextOption]
}

protocol DiscoveryFeedService {
    func seededPlans() -> [AfterPlan]
}

protocol PlanComposerService {
    func createPlan(from draft: CreatePlanDraft, in context: ContextOption, host: UserProfile) -> AfterPlan
}

enum PlanAction: Equatable {
    case join
    case interested
    case suggestPlace(String)
    case confirm
}

protocol PlanParticipationService {
    func apply(_ action: PlanAction, to plan: AfterPlan, currentUser: UserProfile) -> AfterPlan
}

protocol InviteService {
    func preview(for plan: AfterPlan) -> InvitePreview
}

protocol SafetyService {
    var reportReasons: [SafetyReason] { get }
}

protocol AnalyticsService {
    func record(event: String)
}
