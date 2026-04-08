import Foundation

struct PlanAffinity: Equatable {
    let isInSelectedContext: Bool
    let knownPeopleCount: Int
    let hasPriorContextHistory: Bool
    let hostMemory: String?

    var badges: [String] {
        var badges: [String] = []

        if isInSelectedContext {
            badges.append("Same moment")
        }

        if knownPeopleCount > 0 {
            let noun = knownPeopleCount == 1 ? "known face" : "known faces"
            badges.append("\(knownPeopleCount) \(noun)")
        }

        if hasPriorContextHistory {
            badges.append("Repeat context")
        }

        return badges
    }

    var detailLine: String {
        if let hostMemory {
            return hostMemory
        }

        if knownPeopleCount > 0 {
            let verb = knownPeopleCount == 1 ? "is" : "are"
            return "\(knownPeopleCount) known people \(verb) already in this plan."
        }

        if hasPriorContextHistory {
            return "This context already produced a recent continuation, which makes the next move feel safer."
        }

        if isInSelectedContext {
            return "Shared context keeps this visible to the people who just left the same moment."
        }

        return "This stays lower in the stack because it comes from a nearby context instead of the current one."
    }
}

struct ContinuationLoop {
    let visiblePlans: [AfterPlan]
    let rankedPlans: [AfterPlan]
    let currentContextPlans: [AfterPlan]
    let secondaryPlans: [AfterPlan]
    let livePlans: [AfterPlan]
    let historyPlans: [AfterPlan]
    let recentPartners: [String]
    let focusedPlan: AfterPlan?
    private let affinityByPlanID: [UUID: PlanAffinity]

    init(
        plans: [AfterPlan],
        selectedContext: ContextOption?,
        blockedUserNames: [String],
        currentUserName: String,
        focusedPlanID: UUID?
    ) {
        let visiblePlans = plans.filter { plan in
            !blockedUserNames.contains(plan.hostName) &&
                plan.participants.allSatisfy { !blockedUserNames.contains($0.name) }
        }

        let affinityByPlanID = Dictionary(uniqueKeysWithValues: visiblePlans.map { plan in
            (
                plan.id,
                PlanAffinity(
                    isInSelectedContext: plan.contextTitle == selectedContext?.title,
                    knownPeopleCount: plan.participants.filter(\.isKnown).count,
                    hasPriorContextHistory: visiblePlans.contains { candidate in
                        candidate.id != plan.id &&
                            candidate.contextTitle == plan.contextTitle &&
                            candidate.lifecycle == .closed
                    },
                    hostMemory: plan.meaningfulHostMemory
                )
            )
        })

        let rankedPlans = visiblePlans.sorted { lhs, rhs in
            ContinuationLoop.rankingScore(for: lhs, affinity: affinityByPlanID[lhs.id]) >
                ContinuationLoop.rankingScore(for: rhs, affinity: affinityByPlanID[rhs.id])
        }

        self.visiblePlans = visiblePlans
        self.affinityByPlanID = affinityByPlanID
        self.rankedPlans = rankedPlans
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

    func affinity(for id: UUID) -> PlanAffinity? {
        affinityByPlanID[id]
    }

    private static func rankingScore(for plan: AfterPlan, affinity: PlanAffinity?) -> Int {
        var score = 0

        if affinity?.isInSelectedContext == true {
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

        if let affinity {
            score += affinity.knownPeopleCount * 12

            if affinity.hasPriorContextHistory {
                score += 10
            }

            if affinity.hostMemory != nil {
                score += 6
            }
        }

        return score + plan.joinedCount + plan.interestedCount
    }
}
