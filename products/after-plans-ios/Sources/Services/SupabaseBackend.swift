import Foundation

// MARK: - Supabase backend adapter
//
// Conforms to the contract in docs/products/after-plans/api/CONTRACT.md
// against a real Supabase project. Tables and RLS are defined in
// infra/supabase/migrations/0001_init.sql.
//
// Gated behind `#if canImport(Supabase)` so the build always succeeds even
// before the supabase-swift Swift Package has been added — once the package
// is linked the gated implementation activates automatically.

#if canImport(Supabase)
import Supabase

// MARK: - Wire DTOs
//
// Postgres uses snake_case; the domain types in AfterPlansModels.swift use
// camelCase. These DTOs serialize the wire shape and map to/from the domain
// types. Separating them keeps the domain layer free of database concerns.

private struct ProfileRow: Codable {
    let id: UUID
    let firstName: String
    let visibilityDefault: String
    enum CodingKeys: String, CodingKey {
        case id
        case firstName = "first_name"
        case visibilityDefault = "visibility_default"
    }
}

private struct ContextRow: Codable {
    let id: UUID
    let type: String
    let title: String
    let venueName: String?
    let trustNote: String?
    enum CodingKeys: String, CodingKey {
        case id, type, title
        case venueName = "venue_name"
        case trustNote = "trust_note"
    }
}

private struct PlanRow: Codable {
    let id: UUID
    let contextId: UUID
    let hostId: UUID
    let title: String
    let summary: String?
    let mode: String
    let visibility: String
    let lifecycle: String
    let timeLabel: String?
    let venueLabel: String?
    let distanceLabel: String?
    let inviteCode: String
    enum CodingKeys: String, CodingKey {
        case id
        case contextId = "context_id"
        case hostId = "host_id"
        case title, summary, mode, visibility, lifecycle
        case timeLabel = "time_label"
        case venueLabel = "venue_label"
        case distanceLabel = "distance_label"
        case inviteCode = "invite_code"
    }
}

private struct PlanParticipantRow: Codable {
    let planId: UUID
    let userId: UUID
    let role: String
    let descriptor: String?
    enum CodingKeys: String, CodingKey {
        case planId = "plan_id"
        case userId = "user_id"
        case role, descriptor
    }
}

private struct PlanInsert: Encodable {
    let id: UUID
    let context_id: UUID
    let host_id: UUID
    let title: String
    let summary: String?
    let mode: String
    let visibility: String
    let lifecycle: String
    let time_label: String?
    let venue_label: String?
    let distance_label: String?
}

private struct ReportInsert: Encodable {
    let reporter_id: UUID
    let target: String
    let plan_id: UUID?
    let user_id: UUID?
    let reason_id: String
    let note: String?
}

private struct InviteShareInsert: Encodable {
    let plan_id: UUID
    let user_id: UUID
    let channel: String
}

private struct BlockInsert: Encodable {
    let blocker_id: UUID
    let blocked_id: UUID
}

// MARK: - Mappers

private extension PlanLifecycleState {
    init(wire: String) {
        switch wire {
        case "open":      self = .open
        case "forming":   self = .forming
        case "confirmed": self = .confirmed
        case "active":    self = .active
        case "closed":    self = .closed
        default:          self = .open
        }
    }
    var wire: String {
        switch self {
        case .open:      return "open"
        case .forming:   return "forming"
        case .confirmed: return "confirmed"
        case .active:    return "active"
        case .closed:    return "closed"
        }
    }
}

private extension PlanVisibility {
    init(wire: String) {
        switch wire {
        case "same_context_only":       self = .sameContextOnly
        case "known_people":            self = .knownPeople
        case "invite_only":             self = .inviteOnly
        case "friends_of_participants": self = .friendsOfParticipants
        default:                        self = .sameContextOnly
        }
    }
    var wire: String {
        switch self {
        case .sameContextOnly:       return "same_context_only"
        case .knownPeople:           return "known_people"
        case .inviteOnly:            return "invite_only"
        case .friendsOfParticipants: return "friends_of_participants"
        }
    }
}

private extension PlanMode {
    init(wire: String) {
        switch wire {
        case "default_option": self = .defaultOption
        case "open_intent":    self = .openIntent
        case "exact":          self = .exact
        default:               self = .defaultOption
        }
    }
    var wire: String {
        switch self {
        case .defaultOption: return "default_option"
        case .openIntent:    return "open_intent"
        case .exact:         return "exact"
        }
    }
}

// MARK: - Service conformances

struct SupabaseIdentityService: IdentityServiceProtocol {
    let client: SupabaseClient

    func currentUser() async throws -> UserProfile {
        let session = try await ensureSession()
        let userID = session.user.id

        if let row = try? await fetchProfile(userID: userID) {
            return UserProfile.from(row: row)
        }

        // First call after anonymous sign-in: bootstrap a profile.
        let firstName = String(userID.uuidString.prefix(8))
        try await client.from("profiles").insert(
            ProfileRow(id: userID, firstName: firstName, visibilityDefault: "same_context_only")
        ).execute()

        return UserProfile(
            id: userID,
            firstName: firstName,
            descriptor: "Anonymous start",
            visibilityDefault: .sameContextOnly,
            trustHeadline: "Identity-light, but real"
        )
    }

    func updateProfile(_ profile: UserProfile) async throws -> UserProfile {
        let session = try await ensureSession()
        try await client.from("profiles")
            .update([
                "first_name": profile.firstName,
                "visibility_default": profile.visibilityDefault.wire,
            ])
            .eq("id", value: session.user.id)
            .execute()
        return profile
    }

    private func ensureSession() async throws -> Session {
        if let session = try? await client.auth.session { return session }
        return try await client.auth.signInAnonymously()
    }

    private func fetchProfile(userID: UUID) async throws -> ProfileRow {
        try await client.from("profiles")
            .select()
            .eq("id", value: userID)
            .single()
            .execute()
            .value
    }
}

private extension UserProfile {
    static func from(row: ProfileRow) -> UserProfile {
        UserProfile(
            id: row.id,
            firstName: row.firstName,
            descriptor: "",
            visibilityDefault: PlanVisibility(wire: row.visibilityDefault),
            trustHeadline: "Identity-light, but real"
        )
    }
}

struct SupabaseContextService: NetworkedContextServiceProtocol {
    let client: SupabaseClient

    func suggestedContexts() async throws -> [ContextOption] {
        let rows: [ContextRow] = try await client.from("contexts")
            .select()
            .execute()
            .value
        return rows.map { row in
            ContextOption(
                id: row.id,
                type: ContextType(wire: row.type),
                title: row.title,
                venueName: row.venueName ?? "",
                endedAtLabel: "",
                proximityLabel: "",
                trustNote: row.trustNote ?? ""
            )
        }
    }
}

private extension ContextType {
    init(wire: String) {
        switch wire {
        case "class_session": self = .classSession
        case "community":     self = .community
        case "meetup":        self = .meetup
        case "dinner":        self = .dinner
        case "conference":    self = .conference
        case "hangout":       self = .hangout
        default:              self = .meetup
        }
    }
}

struct SupabasePlanService: PlanServiceProtocol {
    let client: SupabaseClient

    func feed(in contextID: ContextID) async throws -> [AfterPlan] {
        let rows: [PlanRow] = try await client.from("plans")
            .select()
            .eq("context_id", value: contextID)
            .neq("lifecycle", value: "closed")
            .execute()
            .value
        // Hydrating participants per plan is a follow-up — for v1 the feed
        // shows hosts only and detail screens fetch full participants.
        return rows.map { try? hydrate($0, participants: []) }.compactMap { $0 }
    }

    func plan(id: PlanID) async throws -> AfterPlan {
        let row: PlanRow = try await client.from("plans")
            .select()
            .eq("id", value: id)
            .single()
            .execute()
            .value
        let participants = try await fetchParticipants(planID: id)
        return try hydrate(row, participants: participants)
    }

    func createPlan(from draft: CreatePlanDraft, in contextID: ContextID) async throws -> AfterPlan {
        let session = try await client.auth.session
        let id = UUID()
        let title = draft.trimmedTitle.isEmpty
            ? "\(draft.mode.defaultTitlePrefix) plan"
            : draft.trimmedTitle
        let venue = draft.trimmedVenueHint.isEmpty
            ? (draft.mode == .openIntent ? "Figure it out together" : "Pick once people join")
            : draft.trimmedVenueHint

        let insert = PlanInsert(
            id: id,
            context_id: contextID,
            host_id: session.user.id,
            title: title,
            summary: draft.summary.trimmingCharacters(in: .whitespacesAndNewlines),
            mode: draft.mode.wire,
            visibility: draft.visibility.wire,
            lifecycle: PlanLifecycleState.open.wire,
            time_label: draft.timeHint,
            venue_label: venue,
            distance_label: nil
        )
        try await client.from("plans").insert(insert).execute()
        try await client.from("plan_participants").insert(
            PlanParticipantRow(planId: id, userId: session.user.id, role: "host", descriptor: "Hosting")
        ).execute()
        return try await plan(id: id)
    }

    func join(planID: PlanID) async throws -> AfterPlan {
        let session = try await client.auth.session
        try await client.from("plan_participants")
            .upsert(PlanParticipantRow(
                planId: planID,
                userId: session.user.id,
                role: "joined",
                descriptor: "Joined from feed"
            )).execute()
        // Lifecycle promotion from open → forming should be a server-side
        // trigger or RPC for atomicity. For v1 we do it client-side and the
        // RLS policy ensures only the host or confirmed participants can flip
        // lifecycle further.
        // Best-effort lifecycle promotion. Idempotent on the eq("lifecycle", "open") guard.
        _ = try? await client.from("plans")
            .update(["lifecycle": "forming"])
            .eq("id", value: planID)
            .eq("lifecycle", value: "open")
            .execute()
        return try await plan(id: planID)
    }

    func expressInterest(planID: PlanID) async throws -> AfterPlan {
        let session = try await client.auth.session
        try await client.from("plan_interest")
            .upsert([
                "plan_id": planID.uuidString,
                "user_id": session.user.id.uuidString,
            ])
            .execute()
        return try await plan(id: planID)
    }

    func suggestPlace(planID: PlanID, place: String) async throws -> AfterPlan {
        let session = try await client.auth.session
        try await client.from("plan_place_suggestions")
            .upsert([
                "plan_id": planID.uuidString,
                "place": place,
                "suggested_by": session.user.id.uuidString,
            ])
            .execute()
        return try await plan(id: planID)
    }

    func confirm(planID: PlanID) async throws -> AfterPlan {
        let session = try await client.auth.session
        try await client.from("plan_participants")
            .update(["role": "confirmed"])
            .eq("plan_id", value: planID)
            .eq("user_id", value: session.user.id)
            .execute()
        try await client.from("plans")
            .update(["lifecycle": "confirmed"])
            .eq("id", value: planID)
            .execute()
        return try await plan(id: planID)
    }

    func markActive(planID: PlanID) async throws -> AfterPlan {
        try await client.from("plans")
            .update(["lifecycle": "active"])
            .eq("id", value: planID)
            .execute()
        return try await plan(id: planID)
    }

    func wrap(planID: PlanID) async throws -> AfterPlan {
        try await client.from("plans")
            .update([
                "lifecycle": "closed",
                "closed_at": ISO8601DateFormatter().string(from: Date()),
            ])
            .eq("id", value: planID)
            .execute()
        return try await plan(id: planID)
    }

    private func fetchParticipants(planID: PlanID) async throws -> [PlanParticipantRow] {
        try await client.from("plan_participants")
            .select()
            .eq("plan_id", value: planID)
            .execute()
            .value
    }

    private func hydrate(_ row: PlanRow, participants: [PlanParticipantRow]) throws -> AfterPlan {
        AfterPlan(
            id: row.id,
            title: row.title,
            summary: row.summary ?? "",
            contextTitle: "",  // populated by a follow-up join or denorm in v2
            hostName: "",
            hostDescriptor: "",
            mode: PlanMode(wire: row.mode),
            visibility: PlanVisibility(wire: row.visibility),
            lifecycle: PlanLifecycleState(wire: row.lifecycle),
            timeLabel: row.timeLabel ?? "",
            venueLabel: row.venueLabel ?? "",
            distanceLabel: row.distanceLabel ?? "",
            trustBlurb: "",
            participants: participants.map {
                ParticipantSummary(
                    id: $0.userId,
                    name: "",
                    descriptor: $0.descriptor ?? "",
                    isOrganizer: $0.role == "host",
                    isKnown: false
                )
            },
            interestedCount: 0,
            placeSuggestions: [],
            participationState: .browsing
        )
    }
}

struct SupabaseInviteService: NetworkedInviteServiceProtocol {
    let client: SupabaseClient

    func preview(planID: PlanID) async throws -> InvitePreview {
        // Server-side preview is a future enhancement; for now build it
        // locally from the fetched plan.
        let plan: PlanRow = try await client.from("plans")
            .select()
            .eq("id", value: planID)
            .single()
            .execute()
            .value
        return InvitePreview(
            title: plan.title,
            subtitle: PlanVisibility(wire: plan.visibility).title,
            audienceHeadline: "Bounded to your context.",
            audienceDetail: "Only people who shared the moment will see this.",
            joinFraming: "Low-pressure invite",
            linkLabel: "Copy invite link",
            qrLabel: "Show QR for people nearby",
            nextStepTitle: "What happens next",
            nextStepDetail: "Sharing here helps the right people join quickly."
        )
    }

    func resolveInvite(code: InviteCode) async throws -> AfterPlan {
        let row: PlanRow = try await client.from("plans")
            .select()
            .eq("invite_code", value: code)
            .single()
            .execute()
            .value
        return AfterPlan(
            id: row.id, title: row.title, summary: row.summary ?? "",
            contextTitle: "", hostName: "", hostDescriptor: "",
            mode: PlanMode(wire: row.mode),
            visibility: PlanVisibility(wire: row.visibility),
            lifecycle: PlanLifecycleState(wire: row.lifecycle),
            timeLabel: row.timeLabel ?? "", venueLabel: row.venueLabel ?? "",
            distanceLabel: row.distanceLabel ?? "", trustBlurb: "",
            participants: [], interestedCount: 0, placeSuggestions: [],
            participationState: .browsing
        )
    }

    func recordShare(planID: PlanID, channel: InviteShareChannel) async throws {
        let session = try await client.auth.session
        let wireChannel: String
        switch channel {
        case .sameContext: wireChannel = "same_context"
        case .knownPeople: wireChannel = "known_people"
        case .nearbyQR:    wireChannel = "nearby_qr"
        }
        try await client.from("invite_shares").insert(
            InviteShareInsert(plan_id: planID, user_id: session.user.id, channel: wireChannel)
        ).execute()
    }
}

struct SupabaseReportService: ReportServiceProtocol {
    let client: SupabaseClient

    func reportReasons() async throws -> [SafetyReason] {
        // The contract treats reasons as a server-side constant. Until we add
        // a dedicated `report_reasons` table or RPC we return the same list
        // the in-memory backend uses.
        InMemorySafetyService().reportReasons
    }

    func reportPlan(_ planID: PlanID, reasonID: String, note: String?) async throws {
        let session = try await client.auth.session
        try await client.from("reports").insert(
            ReportInsert(
                reporter_id: session.user.id, target: "plan",
                plan_id: planID, user_id: nil,
                reason_id: reasonID, note: note
            )
        ).execute()
    }

    func reportUser(_ userID: UserID, reasonID: String, note: String?) async throws {
        let session = try await client.auth.session
        try await client.from("reports").insert(
            ReportInsert(
                reporter_id: session.user.id, target: "user",
                plan_id: nil, user_id: userID,
                reason_id: reasonID, note: note
            )
        ).execute()
    }

    func blockUser(_ userID: UserID) async throws {
        let session = try await client.auth.session
        try await client.from("user_blocks").upsert(
            BlockInsert(blocker_id: session.user.id, blocked_id: userID)
        ).execute()
    }
}

enum SupabaseBackendFactory {
    static func make(url: URL, anonKey: String) -> AfterPlansBackend? {
        let client = SupabaseClient(supabaseURL: url, supabaseKey: anonKey)
        return AfterPlansBackend(
            identity: SupabaseIdentityService(client: client),
            plans: SupabasePlanService(client: client),
            invites: SupabaseInviteService(client: client),
            reports: SupabaseReportService(client: client),
            contexts: SupabaseContextService(client: client),
            realtime: nil
        )
    }

    /// Test-only: clears any cached anonymous session so the next call to
    /// IdentityService.currentUser() bootstraps a fresh auth.users row.
    /// Necessary because supabase-swift persists sessions across runs and
    /// `supabase db reset` invalidates the cached user_id.
    static func resetSessionForTesting(url: URL, anonKey: String) async {
        let client = SupabaseClient(supabaseURL: url, supabaseKey: anonKey)
        try? await client.auth.signOut()
    }
}

#else

// supabase-swift is not linked. Return nil so callers fall back to the
// in-memory backend. See infra/supabase/README.md for how to add the
// package when ready to go live.
enum SupabaseBackendFactory {
    static func make(url: URL, anonKey: String) -> AfterPlansBackend? { nil }
    static func resetSessionForTesting(url: URL, anonKey: String) async {}
}

#endif
