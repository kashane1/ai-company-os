import Foundation

// MARK: - In-memory backend
// A complete in-memory conformance to the network-shaped contract in
// NetworkProtocols.swift. Used for tests, SwiftUI previews, and the
// development build until SupabaseBackend is wired up.
//
// All reads and writes route through `InMemoryStore`, an actor that owns
// the canonical state. Mutations return the updated plan in the same shape
// the network adapter would.

actor InMemoryStore {
    private var user: UserProfile
    private var contexts: [ContextOption]
    private var plansByID: [PlanID: AfterPlan]
    private var blockedUserIDs: Set<UserID>
    private let reasons: [SafetyReason]
    private var reportLog: [(PlanID?, UserID?, String, String?)]
    private var shareLog: [(PlanID, InviteShareChannel)]

    init(seed: InMemoryBackendSeed = .default) {
        self.user = seed.user
        self.contexts = seed.contexts
        self.plansByID = Dictionary(uniqueKeysWithValues: seed.plans.map { ($0.id, $0) })
        self.blockedUserIDs = []
        self.reasons = seed.reasons
        self.reportLog = []
        self.shareLog = []
    }

    // Identity
    func currentUser() -> UserProfile { user }

    func updateProfile(_ profile: UserProfile) -> UserProfile {
        user = profile
        return user
    }

    // Contexts
    func suggestedContexts() -> [ContextOption] { contexts }

    // Plans
    func feed(in contextID: ContextID) -> [AfterPlan] {
        let contextTitle = contexts.first(where: { $0.id == contextID })?.title
        return plansByID.values
            .filter { $0.lifecycle != .closed }
            .filter { plan in
                guard let title = contextTitle else { return true }
                return plan.contextTitle == title || plan.visibility == .knownPeople
            }
            .sorted { $0.lifecycle.rankWeight < $1.lifecycle.rankWeight }
    }

    func plan(id: PlanID) throws -> AfterPlan {
        guard let plan = plansByID[id] else { throw AfterPlansServiceError.notFound }
        return plan
    }

    func createPlan(from draft: CreatePlanDraft, in contextID: ContextID, host: UserProfile) throws -> AfterPlan {
        guard let context = contexts.first(where: { $0.id == contextID }) else {
            throw AfterPlansServiceError.notFound
        }
        let plan = InMemoryPlanComposerService().createPlan(from: draft, in: context, host: host)
        plansByID[plan.id] = plan
        return plan
    }

    func mutate(planID: PlanID, action: PlanAction) throws -> AfterPlan {
        guard var plan = plansByID[planID] else { throw AfterPlansServiceError.notFound }
        plan = InMemoryPlanParticipationService().apply(action, to: plan, currentUser: user)
        plansByID[planID] = plan
        return plan
    }

    func setLifecycle(planID: PlanID, to state: PlanLifecycleState) throws -> AfterPlan {
        guard var plan = plansByID[planID] else { throw AfterPlansServiceError.notFound }
        if plan.lifecycle == .closed && state != .closed {
            throw AfterPlansServiceError.conflict
        }
        plan.lifecycle = state
        if state == .active && plan.participationState == .joined {
            plan.participationState = .confirmed
        }
        plansByID[planID] = plan
        return plan
    }

    // Invites
    func resolveInvite(code: InviteCode) throws -> AfterPlan {
        guard let id = UUID(uuidString: code), let plan = plansByID[id] else {
            throw AfterPlansServiceError.notFound
        }
        return plan
    }

    func recordShare(planID: PlanID, channel: InviteShareChannel) throws {
        guard plansByID[planID] != nil else { throw AfterPlansServiceError.notFound }
        shareLog.append((planID, channel))
    }

    // Reports
    func reportReasons() -> [SafetyReason] { reasons }

    func recordReport(planID: PlanID?, userID: UserID?, reasonID: String, note: String?) throws {
        if planID == nil && userID == nil { throw AfterPlansServiceError.invalid }
        reportLog.append((planID, userID, reasonID, note))
    }

    func block(userID: UserID) {
        blockedUserIDs.insert(userID)
    }
}

private extension PlanLifecycleState {
    var rankWeight: Int {
        switch self {
        case .confirmed: return 0
        case .forming: return 1
        case .open: return 2
        case .active: return 3
        case .closed: return 4
        }
    }
}

// MARK: - Seed data

struct InMemoryBackendSeed {
    let user: UserProfile
    let contexts: [ContextOption]
    let plans: [AfterPlan]
    let reasons: [SafetyReason]

    static var `default`: InMemoryBackendSeed {
        let user = InMemoryAuthService().currentUser()
        let contexts = InMemoryContextService().suggestedContexts()
        let plans = InMemoryDiscoveryFeedService(contexts: contexts).seededPlans()
        let reasons = InMemorySafetyService().reportReasons
        return InMemoryBackendSeed(user: user, contexts: contexts, plans: plans, reasons: reasons)
    }
}

// MARK: - Service conformances

struct InMemoryIdentityService: IdentityServiceProtocol {
    let store: InMemoryStore
    func currentUser() async throws -> UserProfile { await store.currentUser() }
    func updateProfile(_ profile: UserProfile) async throws -> UserProfile {
        await store.updateProfile(profile)
    }
}

struct InMemoryContextNetworkService: NetworkedContextServiceProtocol {
    let store: InMemoryStore
    func suggestedContexts() async throws -> [ContextOption] { await store.suggestedContexts() }
}

struct InMemoryPlanService: PlanServiceProtocol {
    let store: InMemoryStore

    func feed(in contextID: ContextID) async throws -> [AfterPlan] {
        await store.feed(in: contextID)
    }

    func plan(id: PlanID) async throws -> AfterPlan {
        try await store.plan(id: id)
    }

    func createPlan(from draft: CreatePlanDraft, in contextID: ContextID) async throws -> AfterPlan {
        let host = await store.currentUser()
        return try await store.createPlan(from: draft, in: contextID, host: host)
    }

    func join(planID: PlanID) async throws -> AfterPlan {
        try await store.mutate(planID: planID, action: .join)
    }

    func expressInterest(planID: PlanID) async throws -> AfterPlan {
        try await store.mutate(planID: planID, action: .interested)
    }

    func suggestPlace(planID: PlanID, place: String) async throws -> AfterPlan {
        try await store.mutate(planID: planID, action: .suggestPlace(place))
    }

    func confirm(planID: PlanID) async throws -> AfterPlan {
        try await store.mutate(planID: planID, action: .confirm)
    }

    func markActive(planID: PlanID) async throws -> AfterPlan {
        try await store.setLifecycle(planID: planID, to: .active)
    }

    func wrap(planID: PlanID) async throws -> AfterPlan {
        try await store.setLifecycle(planID: planID, to: .closed)
    }
}

struct InMemoryNetworkedInviteService: NetworkedInviteServiceProtocol {
    let store: InMemoryStore

    func preview(planID: PlanID) async throws -> InvitePreview {
        let plan = try await store.plan(id: planID)
        return InMemoryInviteService().preview(for: plan)
    }

    func resolveInvite(code: InviteCode) async throws -> AfterPlan {
        try await store.resolveInvite(code: code)
    }

    func recordShare(planID: PlanID, channel: InviteShareChannel) async throws {
        try await store.recordShare(planID: planID, channel: channel)
    }
}

struct InMemoryReportService: ReportServiceProtocol {
    let store: InMemoryStore

    func reportReasons() async throws -> [SafetyReason] { await store.reportReasons() }

    func reportPlan(_ planID: PlanID, reasonID: String, note: String?) async throws {
        try await store.recordReport(planID: planID, userID: nil, reasonID: reasonID, note: note)
    }

    func reportUser(_ userID: UserID, reasonID: String, note: String?) async throws {
        try await store.recordReport(planID: nil, userID: userID, reasonID: reasonID, note: note)
    }

    func blockUser(_ userID: UserID) async throws {
        await store.block(userID: userID)
    }
}

// MARK: - Backend factory

enum InMemoryBackendFactory {
    static func make(seed: InMemoryBackendSeed = .default) -> AfterPlansBackend {
        let store = InMemoryStore(seed: seed)
        return AfterPlansBackend(
            identity: InMemoryIdentityService(store: store),
            plans: InMemoryPlanService(store: store),
            invites: InMemoryNetworkedInviteService(store: store),
            reports: InMemoryReportService(store: store),
            contexts: InMemoryContextNetworkService(store: store),
            realtime: nil
        )
    }
}
