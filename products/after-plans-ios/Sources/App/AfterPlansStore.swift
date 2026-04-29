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
    /// Plans surfaced via the publicMatch path (Phase 6). Distinct from
    /// `plans` so the Home feed can show them in a separate section
    /// without polluting the context-rooted feed.
    @Published private(set) var publicFeedPlans: [AfterPlan] = []
    /// Recommendation rows surfaced post-wrap or as co-invite suggestions
    /// (Phase 6). Empty in the in-memory shell; populated by the Phase 7
    /// worker against the live backend.
    @Published private(set) var coInviteSuggestionsByPlanID: [UUID: [PlanRecommendation]] = [:]
    @Published private(set) var postWrapRecommendationsByPlanID: [UUID: [PlanRecommendation]] = [:]

    let reportReasons: [SafetyReason]

    private let backend: AfterPlansBackend
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
        backend: AfterPlansBackend,
        analyticsService: AnalyticsService = NoopAnalyticsService()
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
        self.backend = backend
        self.analyticsService = analyticsService
    }

    static func bootstrap(kind: AfterPlansBackendKind = AfterPlansConfiguration.defaultBackend) -> AfterPlansStore {
        // For inMemory we need a single seed shared between the store's
        // @Published cache and the backend's actor — the seed contains UUIDs
        // that must match. For supabase, the cache is empty until the first
        // feed() call hydrates it.
        switch kind {
        case .inMemory:
            let seed = InMemoryBackendSeed.default
            return AfterPlansStore(
                currentUser: seed.user,
                availableContexts: seed.contexts,
                selectedContext: seed.contexts.first,
                plans: seed.plans,
                reportReasons: seed.reasons,
                backend: InMemoryBackendFactory.make(seed: seed)
            )
        case .supabase:
            let seed = InMemoryBackendSeed.default
            return AfterPlansStore(
                currentUser: seed.user,
                availableContexts: seed.contexts,
                selectedContext: seed.contexts.first,
                plans: [],
                reportReasons: seed.reasons,
                backend: AfterPlansConfiguration.makeBackend(kind)
            )
        }
    }

    /// Test-only convenience: build a store wired to an in-memory backend
    /// seeded with the supplied state. Lets unit tests inject specific plans
    /// and contexts without standing up a custom backend manually.
    static func testStore(
        currentUser: UserProfile,
        availableContexts: [ContextOption],
        selectedContext: ContextOption?,
        plans: [AfterPlan],
        reportReasons: [SafetyReason] = InMemorySafetyService().reportReasons
    ) -> AfterPlansStore {
        let seed = InMemoryBackendSeed(
            user: currentUser,
            contexts: availableContexts,
            plans: plans,
            reasons: reportReasons
        )
        let backend = InMemoryBackendFactory.make(seed: seed)
        return AfterPlansStore(
            currentUser: currentUser,
            availableContexts: availableContexts,
            selectedContext: selectedContext,
            plans: plans,
            reportReasons: reportReasons,
            backend: backend
        )
    }

    var feedPlans: [AfterPlan] { continuation.rankedPlans }
    var currentContextPlans: [AfterPlan] { continuation.currentContextPlans }
    var secondaryFeedPlans: [AfterPlan] { continuation.secondaryPlans }
    var focusedPlan: AfterPlan? { continuation.focusedPlan }
    var livePlans: [AfterPlan] { continuation.livePlans }
    var historyPlans: [AfterPlan] { continuation.historyPlans }
    var recentPartners: [String] { continuation.recentPartners }
    var recapSummary: RecapSummary { continuation.recapSummary }

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

    // MARK: - Onboarding actions (Phase 4)

    /// Persist the onboarding profile (first name + privacy mode) through
    /// the identity service. Errors are swallowed for the in-memory shell;
    /// in the live backend the supabase client surfaces them through its
    /// own error reporting path.
    func updateOnboardingProfile(firstName: String, privacyMode: PrivacyMode) async {
        var updated = currentUser
        updated.firstName = firstName
        updated.privacyMode = privacyMode
        do {
            let saved = try await backend.identity.updateProfile(updated)
            self.currentUser = saved
        } catch {
            self.currentUser = updated
        }
        analyticsService.record(event: "onboarding_profile_set")
    }

    /// Declare a single activity (and optional venue) interest. Returns
    /// the matching context_id when the backend already has one for this
    /// pair, so callers can show "joined X" feedback. The in-memory shell
    /// always returns nil; only the live backend with auto-context
    /// formation populates a value.
    @discardableResult
    func declareActivityInterest(activityID: UUID, venueID: UUID?) async -> ContextID? {
        do {
            let matched = try await backend.activities.declareInterest(activityID: activityID, venueID: venueID)
            analyticsService.record(event: "onboarding_interest_declared")
            return matched
        } catch {
            return nil
        }
    }

    /// Bulk-resolve any interests that already match a real context. Used
    /// at the end of the activity step to avoid N round-trips. Returns
    /// the count of newly joined contexts.
    func autoJoinMatchingContexts() async -> Int {
        do {
            return try await backend.activities.autoJoinMatchingContexts()
        } catch {
            return 0
        }
    }

    /// Resolve an invite code to a plan. Returns true if the code matched
    /// a real plan; the resolved plan is added to the visible plan set so
    /// the user lands on Home with it already focused.
    // MARK: - Phase 6 — public feed + recommendations

    /// Load plans that match the user's declared activity interests.
    /// Empty in the in-memory shell because the InMemoryBackend has no
    /// publicMatch plans seeded; the Supabase backend returns rows where
    /// visibility = 'public' and activity_id is in the user's interest set.
    func loadPublicFeed() async {
        // The in-memory shell has no real publicMatch plans, so this
        // surface ends up empty there. Against the Supabase backend the
        // existing `feed(in:)` RPC plus a future RPC for closeness will
        // populate it; v1 just filters the visible plans by visibility.
        let visible = continuation.visiblePlans
        publicFeedPlans = visible.filter { $0.visibility == .publicMatch }
    }

    /// Pull co-invite suggestions for a plan in creation/forming state.
    func loadCoInviteSuggestions(for planID: UUID) async {
        do {
            let rows = try await backend.recommendations.coInviteSuggestions(planID: planID)
            coInviteSuggestionsByPlanID[planID] = rows
        } catch {
            coInviteSuggestionsByPlanID[planID] = []
        }
    }

    /// Pull post-wrap recommendations for a freshly closed plan.
    func loadPostWrapRecommendations(for planID: UUID) async {
        do {
            let rows = try await backend.recommendations.postWrapRecommendations(planID: planID)
            postWrapRecommendationsByPlanID[planID] = rows
        } catch {
            postWrapRecommendationsByPlanID[planID] = []
        }
    }

    func dismissRecommendation(_ recommendationID: UUID) async {
        try? await backend.recommendations.dismiss(recommendationID: recommendationID)
        for (planID, rows) in coInviteSuggestionsByPlanID {
            coInviteSuggestionsByPlanID[planID] = rows.filter { $0.id != recommendationID }
        }
        for (planID, rows) in postWrapRecommendationsByPlanID {
            postWrapRecommendationsByPlanID[planID] = rows.filter { $0.id != recommendationID }
        }
    }

    // MARK: - Push registration (Phase 7)

    /// Register the APNs device token with the backend. Idempotent on
    /// the token; `push_devices` is upserted on conflict (token) so a
    /// device that switches users updates user_id (security H3).
    func registerPushToken(_ token: String) async {
        try? await backend.push.register(deviceToken: token, platform: "ios")
    }

    func unregisterPushToken(_ token: String) async {
        try? await backend.push.unregister(deviceToken: token)
    }

    @discardableResult
    func redeemInviteCode(_ code: String) async -> Bool {
        do {
            let plan = try await backend.invites.resolveInvite(code: code)
            if !plans.contains(where: { $0.id == plan.id }) {
                plans.append(plan)
            }
            focusedPlanID = plan.id
            analyticsService.record(event: "onboarding_invite_redeemed")
            return true
        } catch {
            return false
        }
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

    /// Local-only preview rendering. The contract `invite_preview` op is
    /// available on `backend.invites` for cases where the server needs to
    /// stamp the invite code or audience headline; SwiftUI surfaces compute
    /// the preview directly from the plan to keep `body` synchronous.
    func invitePreview(for plan: AfterPlan) -> InvitePreview {
        InMemoryInviteService().preview(for: plan)
    }

    func inviteShareState(for planID: UUID) -> InviteShareState? {
        inviteShareStates[planID]
    }

    func inviteChannels(for plan: AfterPlan) -> [InviteShareChannel] {
        plan.inviteChannels
    }

    @discardableResult
    func handleIncomingURL(_ url: URL) -> Bool {
        guard url.scheme == "afterplans", url.host == "join" else { return false }

        let planIDString = url.pathComponents.dropFirst().first
        guard
            let planIDString,
            let planID = UUID(uuidString: planIDString),
            let plan = plan(with: planID)
        else {
            lastActionMessage = "That invite is no longer available."
            selectedTab = .home
            return false
        }

        hasCompletedOnboarding = true
        selectedTab = .home
        focusedPlanID = plan.id
        if let context = availableContexts.first(where: { $0.title == plan.contextTitle }) {
            selectedContext = context
        }
        lastActionMessage = "Opened invite for \(plan.title)."
        analyticsService.record(event: "invite_link_opened")
        return true
    }

    func join(_ planID: UUID) async {
        guard let updated = try? await backend.plans.join(planID: planID) else { return }
        upsertPlan(updated)
        focus(on: planID)
        lastActionMessage = "You're in for \(updated.title)."
        analyticsService.record(event: "join_tapped")
    }

    func expressInterest(in planID: UUID) async {
        guard let updated = try? await backend.plans.expressInterest(planID: planID) else { return }
        upsertPlan(updated)
        focus(on: planID)
        lastActionMessage = "Marked interest in \(updated.title)."
        analyticsService.record(event: "interested_tapped")
    }

    func suggestDefaultPlace(for planID: UUID) async {
        guard let existingPlan = plans.first(where: { $0.id == planID }) else { return }
        let defaults = ["Tea House", "Corner Slice", "Mercado", "Rooftop Coffee"]
        let suggestion = defaults[existingPlan.placeSuggestions.count % defaults.count]

        guard let updated = try? await backend.plans.suggestPlace(planID: planID, place: suggestion) else { return }
        upsertPlan(updated)
        focus(on: planID)
        lastActionMessage = "Suggested \(suggestion) for \(updated.title)."
        analyticsService.record(event: "suggest_place_tapped")
    }

    func confirm(_ planID: UUID) async {
        guard let updated = try? await backend.plans.confirm(planID: planID) else { return }
        upsertPlan(updated)
        focus(on: planID)
        lastActionMessage = "\(updated.title) is now locked for \(updated.timeLabel)."
        analyticsService.record(event: "plan_confirmed")
    }

    func markPlanActive(_ planID: UUID) async {
        guard let updated = try? await backend.plans.markActive(planID: planID) else { return }
        upsertPlan(updated)
        focus(on: planID)
        lastActionMessage = "\(updated.title) is now in motion."
        analyticsService.record(event: "plan_active")
    }

    func wrapPlan(_ planID: UUID) async {
        guard let updated = try? await backend.plans.wrap(planID: planID) else { return }
        upsertPlan(updated)
        lastActionMessage = "\(updated.title) is wrapped. Check your activity for the recap."
        analyticsService.record(event: "plan_closed")
    }

    func prepareInviteShare(for planID: UUID, channel: InviteShareChannel) async {
        guard let plan = plan(with: planID), plan.inviteChannels.contains(channel) else { return }

        try? await backend.invites.recordShare(planID: planID, channel: channel)

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

    func runConfirmationAction(for planID: UUID) async {
        guard let plan = plan(with: planID) else { return }

        switch plan.confirmationAction {
        case .join:
            await join(planID)
        case .confirm:
            await confirm(planID)
        case .markActive:
            await markPlanActive(planID)
        case .wrapPlan:
            await wrapPlan(planID)
        case .none:
            break
        }
    }

    @discardableResult
    func createPlan(from draft: CreatePlanDraft) async -> Bool {
        var draft = draft
        let isPublicMatch = draft.visibility == .publicMatch

        // For publicMatch plans we materialize a freeform venue from
        // the typed-in hint so the plan can carry a real venue_id. Real
        // typeahead-resolved venues come through Phase 6's UI seam; v1
        // accepts freeform-only and lets the worker reconcile later.
        // If upsert fails, surface it instead of silently creating a
        // plan with no venue — the relaxed UI validation otherwise lets
        // a half-success ship.
        if isPublicMatch && draft.venueID == nil {
            let trimmed = draft.trimmedVenueHint
            if !trimmed.isEmpty {
                let freeform = StubVenueSearchService().freeformVenue(named: trimmed)
                do {
                    let stored = try await backend.venues.upsertVenue(freeform)
                    draft.venueID = stored.id
                } catch {
                    lastActionMessage = "Couldn't save the place — try again."
                    return false
                }
            }
        }

        guard draft.validationMessage(hasContext: selectedContext != nil) == nil else {
            return false
        }

        // contextID is required by the protocol; SupabaseBackend nulls
        // it out for publicMatch plans before insert. For non-public
        // plans we still need a real selectedContext.
        let routingContextID: ContextID
        if let selected = selectedContext {
            routingContextID = selected.id
        } else if isPublicMatch, let fallback = availableContexts.first?.id {
            routingContextID = fallback
        } else {
            return false
        }

        guard let plan = try? await backend.plans.createPlan(from: draft, in: routingContextID) else {
            return false
        }

        plans.insert(plan, at: 0)
        focus(on: plan.id)
        lastActionMessage = isPublicMatch
            ? "Your plan is live for everyone who declared this activity."
            : "Your plan is live for \(selectedContext?.title ?? "your context")."
        selectedTab = .home
        analyticsService.record(event: "plan_created")
        return true
    }

    func reportPlan(_ plan: AfterPlan) async {
        try? await backend.reports.reportPlan(plan.id, reasonID: "unspecified", note: nil)
        reportLog.append("Reported plan: \(plan.title)")
        focus(on: plan.id)
        analyticsService.record(event: "report_submitted")
    }

    func reportUser(named name: String) async {
        // Without a stable userID for the named participant in the in-memory
        // shell, we record a local log entry only. The cloud backend will
        // accept the userID lookup once participant IDs are stable.
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

    private func upsertPlan(_ plan: AfterPlan) {
        if let index = plans.firstIndex(where: { $0.id == plan.id }) {
            plans[index] = plan
        } else {
            plans.insert(plan, at: 0)
        }
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
