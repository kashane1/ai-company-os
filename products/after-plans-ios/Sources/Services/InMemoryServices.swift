import Foundation

struct InMemoryAuthService: AuthService {
    func currentUser() -> UserProfile {
        UserProfile(
            id: UUID(),
            firstName: "Maya",
            descriptor: "Verified phone · ceramics regular",
            visibilityDefault: .sameContextOnly,
            trustHeadline: "Identity-light, but real"
        )
    }
}

struct InMemoryContextService: ContextService {
    func suggestedContexts() -> [ContextOption] {
        [
            ContextOption(
                id: UUID(),
                type: .classSession,
                title: "Pottery Night",
                venueName: "Clay House Studio",
                endedAtLabel: "Ended 12 min ago",
                proximityLabel: "3 min away",
                trustNote: "People leaving this class should see each other first."
            ),
            ContextOption(
                id: UUID(),
                type: .community,
                title: "Wednesday Run Club",
                venueName: "Civic Track",
                endedAtLabel: "Ends in 10 min",
                proximityLabel: "6 min away",
                trustNote: "Same-route regulars outrank broader city discovery."
            ),
            ContextOption(
                id: UUID(),
                type: .meetup,
                title: "Downtown Product Meetup",
                venueName: "Pier Hall",
                endedAtLabel: "Ended 20 min ago",
                proximityLabel: "8 min away",
                trustNote: "Visible to people who just shared the meetup context."
            ),
        ]
    }
}

struct InMemoryDiscoveryFeedService: DiscoveryFeedService {
    let contexts: [ContextOption]

    func seededPlans() -> [AfterPlan] {
        let pottery = contexts[0]
        let runClub = contexts[1]
        let meetup = contexts[2]

        return [
            AfterPlan(
                id: UUID(),
                title: "Tacos at Mercado",
                summary: "A simple same-group move while everyone is still nearby.",
                contextTitle: pottery.title,
                hostName: "Nia",
                hostDescriptor: "You've planned with Nia twice.",
                mode: .defaultOption,
                visibility: .sameContextOnly,
                lifecycle: .forming,
                timeLabel: "Leaving in 10 min",
                venueLabel: "Mercado Taqueria",
                distanceLabel: "4 min walk",
                trustBlurb: "Visible to people leaving pottery night right now.",
                participants: [
                    ParticipantSummary(id: UUID(), name: "Nia", descriptor: "Hosting", isOrganizer: true, isKnown: true),
                    ParticipantSummary(id: UUID(), name: "Jules", descriptor: "Met here before", isOrganizer: false, isKnown: true),
                ],
                interestedCount: 3,
                placeSuggestions: ["Mercado", "Late Bowls"],
                participationState: .browsing
            ),
            AfterPlan(
                id: UUID(),
                title: "Walk to the river steps",
                summary: "Low-pressure decompression before everyone heads home.",
                contextTitle: runClub.title,
                hostName: "Dev",
                hostDescriptor: "Same-route regular.",
                mode: .openIntent,
                visibility: .knownPeople,
                lifecycle: .open,
                timeLabel: "Right after cool-down",
                venueLabel: "River steps",
                distanceLabel: "7 min walk",
                trustBlurb: "Known runners and current club regulars see this first.",
                participants: [
                    ParticipantSummary(id: UUID(), name: "Dev", descriptor: "Hosting", isOrganizer: true, isKnown: false),
                ],
                interestedCount: 4,
                placeSuggestions: ["River steps"],
                participationState: .browsing
            ),
            AfterPlan(
                id: UUID(),
                title: "Tea before heading out",
                summary: "Confirmed spot for people who still want to keep talking.",
                contextTitle: meetup.title,
                hostName: "Alex",
                hostDescriptor: "Met at the last two product meetups.",
                mode: .exact,
                visibility: .inviteOnly,
                lifecycle: .confirmed,
                timeLabel: "7:40 PM",
                venueLabel: "Lantern Tea Room",
                distanceLabel: "5 min walk",
                trustBlurb: "Invite-only once the group narrows in on one place.",
                participants: [
                    ParticipantSummary(id: UUID(), name: "Alex", descriptor: "Hosting", isOrganizer: true, isKnown: true),
                    ParticipantSummary(id: UUID(), name: "Priya", descriptor: "Same meetup context", isOrganizer: false, isKnown: false),
                    ParticipantSummary(id: UUID(), name: "Theo", descriptor: "Planned together once", isOrganizer: false, isKnown: true),
                ],
                interestedCount: 1,
                placeSuggestions: ["Lantern Tea Room"],
                participationState: .browsing
            ),
            AfterPlan(
                id: UUID(),
                title: "Post-class slices",
                summary: "Closed example to make the history tab believable without adding chat.",
                contextTitle: pottery.title,
                hostName: "Mina",
                hostDescriptor: "Same studio circle.",
                mode: .defaultOption,
                visibility: .sameContextOnly,
                lifecycle: .closed,
                timeLabel: "Wrapped",
                venueLabel: "Corner Slice",
                distanceLabel: "2 min walk",
                trustBlurb: "Past continuation from the same pottery context.",
                participants: [
                    ParticipantSummary(id: UUID(), name: "Mina", descriptor: "Hosted", isOrganizer: true, isKnown: true),
                    ParticipantSummary(id: UUID(), name: "Rowan", descriptor: "Joined", isOrganizer: false, isKnown: false),
                ],
                interestedCount: 0,
                placeSuggestions: ["Corner Slice"],
                participationState: .browsing
            ),
        ]
    }
}

struct InMemoryPlanComposerService: PlanComposerService {
    func createPlan(from draft: CreatePlanDraft, in context: ContextOption, host: UserProfile) -> AfterPlan {
        let title = draft.trimmedTitle.isEmpty ? "\(draft.mode.defaultTitlePrefix) \(context.title)" : draft.trimmedTitle
        let venue = draft.trimmedVenueHint.isEmpty
            ? (draft.mode == .openIntent ? "Figure it out together" : "Pick once people join")
            : draft.trimmedVenueHint

        return AfterPlan(
            id: UUID(),
            title: title,
            summary: draft.summary.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                ? "A low-pressure continuation for people already in this context."
                : draft.summary,
            contextTitle: context.title,
            hostName: host.firstName,
            hostDescriptor: host.descriptor,
            mode: draft.mode,
            visibility: draft.visibility,
            lifecycle: .open,
            timeLabel: draft.timeHint,
            venueLabel: venue,
            distanceLabel: context.proximityLabel,
            trustBlurb: draft.visibility.subtitle,
            participants: [
                ParticipantSummary(
                    id: host.id,
                    name: host.firstName,
                    descriptor: "Hosting",
                    isOrganizer: true,
                    isKnown: true
                ),
            ],
            interestedCount: 0,
            placeSuggestions: venue == "Figure it out together" ? [] : [venue],
            participationState: .joined
        )
    }
}

struct InMemoryPlanParticipationService: PlanParticipationService {
    func apply(_ action: PlanAction, to plan: AfterPlan, currentUser: UserProfile) -> AfterPlan {
        var updated = plan

        switch action {
        case .join:
            if !updated.participants.contains(where: { $0.name == currentUser.firstName }) {
                updated.participants.append(
                    ParticipantSummary(
                        id: currentUser.id,
                        name: currentUser.firstName,
                        descriptor: "Joined from feed",
                        isOrganizer: false,
                        isKnown: true
                    )
                )
            }
            updated.participationState = updated.lifecycle == .confirmed ? .confirmed : .joined
            if updated.lifecycle == .open {
                updated.lifecycle = .forming
            }
        case .interested:
            if updated.participationState == .browsing {
                updated.interestedCount += 1
            }
            updated.participationState = .interested
        case let .suggestPlace(place):
            if !updated.placeSuggestions.contains(place) {
                updated.placeSuggestions.append(place)
            }
            if updated.lifecycle == .open {
                updated.lifecycle = .forming
            }
        case .confirm:
            updated.lifecycle = .confirmed
            updated.participationState = .confirmed
        }

        return updated
    }
}

struct InMemoryInviteService: InviteService {
    func preview(for plan: AfterPlan) -> InvitePreview {
        InvitePreview(
            title: plan.title,
            subtitle: "\(plan.contextTitle) · \(plan.visibility.title)",
            linkLabel: "Copy invite link",
            qrLabel: "Show QR for people nearby"
        )
    }
}

struct InMemorySafetyService: SafetyService {
    var reportReasons: [SafetyReason] {
        [
            SafetyReason(id: "harassment", title: "Harassment or creepy behavior", explanation: "Use when someone makes the plan feel unsafe or hostile."),
            SafetyReason(id: "hate", title: "Hate or abusive content", explanation: "Use for hateful, abusive, or discriminatory behavior."),
            SafetyReason(id: "spam", title: "Spam or fake plan", explanation: "Use when the plan is misleading, fake, or repeatedly noisy."),
            SafetyReason(id: "dating", title: "Dating misuse", explanation: "Use when someone turns the app into a dating or stranger-meetup surface."),
            SafetyReason(id: "unsafe", title: "Unsafe real-world behavior", explanation: "Use when the plan encourages unsafe or misleading behavior."),
        ]
    }
}

struct NoopAnalyticsService: AnalyticsService {
    func record(event: String) {}
}
