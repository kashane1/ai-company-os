import Foundation

struct PlanAffinity: Equatable {
    let isInSelectedContext: Bool
    let knownPeopleCount: Int
    let hasPriorContextHistory: Bool
    let pastPartnerCount: Int
    let hostMemory: String?
    /// Server-supplied closeness score (Phase 6/7). Higher = closer to
    /// the host. Only populated when `publicFeedPlans` are loaded via
    /// the closeness_scores RPC; nil for the default ranking path.
    var closenessScore: Int? = nil

    var badges: [String] {
        var result: [String] = []

        if isInSelectedContext {
            result.append("Same moment")
        }

        if pastPartnerCount > 0 {
            result.append("Familiar crew")
        } else if knownPeopleCount > 0 {
            let noun = knownPeopleCount == 1 ? "known face" : "known faces"
            result.append("\(knownPeopleCount) \(noun)")
        }

        if hasPriorContextHistory {
            result.append("Repeat context")
        }

        return result
    }

    var detailLine: String {
        if pastPartnerCount > 0 {
            let noun = pastPartnerCount == 1 ? "person" : "people"
            return "You've planned with \(pastPartnerCount) of these \(noun) before."
        }

        if let hostMemory {
            return hostMemory
        }

        if knownPeopleCount > 0 {
            let noun = knownPeopleCount == 1 ? "person is" : "people are"
            return "\(knownPeopleCount) known \(noun) already in this plan."
        }

        if hasPriorContextHistory {
            return "You've kept going after this context before."
        }

        if isInSelectedContext {
            return "Shared context keeps this visible to the people who just left the same moment."
        }

        return "This stays lower in the stack because it comes from a nearby context instead of the current one."
    }
}

/// Lightweight social-memory stats derived from the current plan set.
struct RecapSummary: Equatable {
    /// Number of closed plans (successful follow-throughs).
    let followThroughCount: Int
    /// Distinct context titles that have at least one closed plan.
    let distinctContextsFollowedThrough: [String]
    /// Context title that appears most often in closed plans, if any.
    let repeatContextTitle: String?
    /// A warm summary headline for the Activity surface.
    var headline: String {
        if followThroughCount == 0 {
            return "Your first continuation is waiting."
        }
        if let repeatContext = repeatContextTitle {
            return "You keep coming back after \(repeatContext)."
        }
        if distinctContextsFollowedThrough.count > 1 {
            return "\(followThroughCount) follow-throughs across \(distinctContextsFollowedThrough.count) contexts."
        }
        return "You followed through once so far."
    }
    /// Short, warm detail line about social momentum.
    var detail: String {
        if followThroughCount == 0 {
            return "Plans that wrap will show up here as your continuation history."
        }
        if followThroughCount == 1 {
            return "One real follow-through is a start."
        }
        return "That kind of follow-through builds real momentum."
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

        // Count how many plans each participant name appears in (to detect past partners).
        var partnerPlanCount: [String: Int] = [:]
        for plan in visiblePlans {
            for participant in plan.participants where participant.name != currentUserName {
                partnerPlanCount[participant.name, default: 0] += 1
            }
        }

        let affinityByPlanID = Dictionary(uniqueKeysWithValues: visiblePlans.map { plan in
            // A "past partner" is someone in this plan who also appears in at least one other plan.
            let pastPartnerCount = plan.participants.filter { participant in
                participant.name != currentUserName &&
                    (partnerPlanCount[participant.name] ?? 0) > 1
            }.count

            return (
                plan.id,
                PlanAffinity(
                    isInSelectedContext: plan.contextTitle == selectedContext?.title,
                    knownPeopleCount: plan.participants.filter(\.isKnown).count,
                    hasPriorContextHistory: visiblePlans.contains { candidate in
                        candidate.id != plan.id &&
                            candidate.contextTitle == plan.contextTitle &&
                            candidate.lifecycle == .closed
                    },
                    pastPartnerCount: pastPartnerCount,
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

    var recapSummary: RecapSummary {
        let closed = historyPlans
        let contextCounts = Dictionary(grouping: closed, by: \.contextTitle)
            .mapValues(\.count)
        let distinctContexts = contextCounts.keys.sorted()
        let repeatContext = contextCounts.max(by: { $0.value < $1.value })
        let repeatTitle = (repeatContext?.value ?? 0) >= 2 ? repeatContext?.key : nil

        return RecapSummary(
            followThroughCount: closed.count,
            distinctContextsFollowedThrough: distinctContexts,
            repeatContextTitle: repeatTitle
        )
    }

    private static func rankingScore(for plan: AfterPlan, affinity: PlanAffinity?) -> Int {
        var score = 0

        if affinity?.isInSelectedContext == true {
            score += 100
        }

        // Closeness scores from the server-side RPC dominate the public-
        // match ranking; absent (nil) defers to the existing factor mix.
        if let closeness = affinity?.closenessScore {
            score += closeness * 10
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
        case .publicMatch:
            score += 11  // Slightly below same-context: declared interest but not in same moment
        case .knownPeople:
            score += 9
        case .inviteOnly:
            score += 6
        case .friendsOfParticipants:
            score += 2
        }

        if let affinity {
            score += affinity.pastPartnerCount * 15
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
