import Foundation

// MARK: - Contract types
// Source of truth: docs/products/after-plans/api/CONTRACT.md
// These protocols describe operations that will cross the network in production.
// They are intentionally async/throws so any conformance — in-memory or
// Supabase — can satisfy the same surface.

// Stable, cross-platform identifiers.
typealias UserID = UUID
typealias PlanID = UUID
typealias ContextID = UUID
typealias InviteCode = String

enum AfterPlansServiceError: Error, Equatable {
    case unauthorized
    case notFound
    case forbidden
    case conflict
    case rateLimited
    case transient
    case invalid
}

// MARK: - Identity

protocol IdentityServiceProtocol {
    func currentUser() async throws -> UserProfile
    func updateProfile(_ profile: UserProfile) async throws -> UserProfile
}

// MARK: - Plans (feed + lifecycle)

protocol PlanServiceProtocol {
    func feed(in contextID: ContextID) async throws -> [AfterPlan]
    func plan(id: PlanID) async throws -> AfterPlan
    func createPlan(from draft: CreatePlanDraft, in contextID: ContextID) async throws -> AfterPlan
    func join(planID: PlanID) async throws -> AfterPlan
    func expressInterest(planID: PlanID) async throws -> AfterPlan
    func suggestPlace(planID: PlanID, place: String) async throws -> AfterPlan
    func confirm(planID: PlanID) async throws -> AfterPlan
    func markActive(planID: PlanID) async throws -> AfterPlan
    func wrap(planID: PlanID) async throws -> AfterPlan
}

// MARK: - Invites

protocol NetworkedInviteServiceProtocol {
    func preview(planID: PlanID) async throws -> InvitePreview
    func resolveInvite(code: InviteCode) async throws -> AfterPlan
    func recordShare(planID: PlanID, channel: InviteShareChannel) async throws
}

// MARK: - Reports & blocks

protocol ReportServiceProtocol {
    func reportReasons() async throws -> [SafetyReason]
    func reportPlan(_ planID: PlanID, reasonID: String, note: String?) async throws
    func reportUser(_ userID: UserID, reasonID: String, note: String?) async throws
    func blockUser(_ userID: UserID) async throws
}

// MARK: - Context discovery

protocol NetworkedContextServiceProtocol {
    func suggestedContexts() async throws -> [ContextOption]
}

// MARK: - Activity taxonomy + declared interests (Phase 2c)

protocol ActivityServiceProtocol {
    /// Founder-curated activity taxonomy. Stable across app lifetime.
    func listActivities() async throws -> [Activity]
    /// User declares an activity (and optional venue) they do regularly.
    /// Returns the matching context_id if one already exists for this
    /// activity+venue combination so the client can show "joined Westside
    /// Run Club" feedback; nil if no match (interest is recorded as a
    /// pending row to be converted at auto-context formation time).
    func declareInterest(activityID: UUID, venueID: UUID?) async throws -> ContextID?
    /// Bulk auto-join the contexts that already match a user's declared
    /// interests. Returns the count of newly joined contexts. Used by
    /// onboarding to avoid N round-trips (per performance review #5).
    func autoJoinMatchingContexts() async throws -> Int
    /// User's currently declared interests (for the Profile screen).
    func myInterests() async throws -> [UserActivityInterest]
}

// MARK: - Venue search (Apple MKLocalSearch backed on iOS)

protocol VenueServiceProtocol {
    /// Persist a venue from a typeahead pick or freeform entry. If a
    /// venue with the same Apple Place ID already exists, returns the
    /// existing row.
    func upsertVenue(_ venue: Venue) async throws -> Venue
}

// MARK: - Recommendation surfaces

protocol RecommendationServiceProtocol {
    /// Recommendations to surface in the post-wrap "did you know" card
    /// for a freshly closed plan.
    func postWrapRecommendations(planID: PlanID) async throws -> [PlanRecommendation]
    /// Co-invite suggestions for a plan in creation/forming state:
    /// other users the host frequently plans with.
    func coInviteSuggestions(planID: PlanID) async throws -> [PlanRecommendation]
    /// Mark a recommendation dismissed.
    func dismiss(recommendationID: UUID) async throws
}

// MARK: - Push notification registration

protocol PushRegistrationProtocol {
    func register(deviceToken: String, platform: String) async throws
    func unregister(deviceToken: String) async throws
}

// MARK: - Realtime (additive, optional)

enum PlanRealtimeEvent: Equatable {
    case planCreated(AfterPlan)
    case planUpdated(AfterPlan)
    case planClosed(PlanID)
}

protocol PlanRealtimeProtocol {
    func subscribe(toContext contextID: ContextID) -> AsyncStream<PlanRealtimeEvent>
    func subscribe(toPlan planID: PlanID) -> AsyncStream<PlanRealtimeEvent>
}

// MARK: - Backend bundle

// A single bundle of services representing a complete backend implementation
// of the contract. The store and feature views depend on this bundle, not on
// individual protocol references, so wiring stays one-line.
struct AfterPlansBackend {
    let identity: IdentityServiceProtocol
    let plans: PlanServiceProtocol
    let invites: NetworkedInviteServiceProtocol
    let reports: ReportServiceProtocol
    let contexts: NetworkedContextServiceProtocol
    let activities: ActivityServiceProtocol
    let venues: VenueServiceProtocol
    let recommendations: RecommendationServiceProtocol
    let push: PushRegistrationProtocol
    let realtime: PlanRealtimeProtocol?
}
