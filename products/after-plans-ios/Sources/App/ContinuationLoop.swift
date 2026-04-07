import Foundation

struct ContinuationLoop {
    let visiblePlans: [AfterPlan]
    let rankedPlans: [AfterPlan]
    let currentContextPlans: [AfterPlan]
    let secondaryPlans: [AfterPlan]
    let livePlans: [AfterPlan]
    let historyPlans: [AfterPlan]
    let recentPartners: [String]
    let focusedPlan: AfterPlan?

    init(
        plans: [AfterPlan],
        selectedContext: ContextOption?,
        blockedUserNames: [String],
        currentUserName: String,
        focusedPlanID: UUID?
    ) {
        visiblePlans = plans.filter { plan in
            !blockedUserNames.contains(plan.hostName) &&
                plan.participants.allSatisfy { !blockedUserNames.contains($0.name) }
        }

        rankedPlans = visiblePlans.sorted { lhs, rhs in
            ContinuationLoop.rankingScore(for: lhs, selectedContext: selectedContext) >
                ContinuationLoop.rankingScore(for: rhs, selectedContext: selectedContext)
        }

        currentContextPlans = rankedPlans.filter { $0.contextTitle == selectedContext?.title }
        secondaryPlans = rankedPlans.filter { $0.contextTitle != selectedContext?.title }
        livePlans = visiblePlans.filter { $0.lifecycle != .closed }
        historyPlans = visiblePlans.filter { $0.lifecycle == .closed }
        focusedPlan = visiblePlans.first(where: { $0.id == focusedPlanID }) ?? currentContextPlans.first

        var partnerNames: [String] = []

        for participant in visiblePlans.flatMap(\.participants) where participant.name != currentUserName {
            if !partnerNames.contains(participant.name) {
                partnerNames.append(participant.name)
            }
        }

        recentPartners = Array(partnerNames.prefix(4))
    }

    func plan(with id: UUID) -> AfterPlan? {
        visiblePlans.first(where: { $0.id == id })
    }

    private static func rankingScore(for plan: AfterPlan, selectedContext: ContextOption?) -> Int {
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
}
