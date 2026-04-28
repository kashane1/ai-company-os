import Foundation

enum ContextType: String, CaseIterable, Identifiable {
    case meetup
    case classSession
    case dinner
    case conference
    case community
    case hangout

    var id: String { rawValue }

    var title: String {
        switch self {
        case .meetup:
            "Meetup"
        case .classSession:
            "Class"
        case .dinner:
            "Dinner"
        case .conference:
            "Conference"
        case .community:
            "Community"
        case .hangout:
            "Hangout"
        }
    }
}

struct ContextOption: Identifiable, Equatable {
    let id: UUID
    var type: ContextType
    var title: String
    var venueName: String
    var endedAtLabel: String
    var proximityLabel: String
    var trustNote: String

    var timingSummary: String {
        "\(venueName) · \(endedAtLabel)"
    }
}

enum PlanMode: String, CaseIterable, Identifiable {
    case exact
    case defaultOption
    case openIntent

    var id: String { rawValue }

    var title: String {
        switch self {
        case .exact:
            "Exact plan"
        case .defaultOption:
            "Default option"
        case .openIntent:
            "Open intent"
        }
    }

    var subtitle: String {
        switch self {
        case .exact:
            "Pick the place and timing now."
        case .defaultOption:
            "Offer one easy next move."
        case .openIntent:
            "Signal the vibe before the details."
        }
    }

    var defaultTitlePrefix: String {
        switch self {
        case .exact:
            "Head to"
        case .defaultOption:
            "Anyone up for"
        case .openIntent:
            "Keep it going after"
        }
    }
}

enum PlanVisibility: String, CaseIterable, Identifiable {
    case sameContextOnly
    case inviteOnly
    case publicMatch  // wire: "public" — Swift `public` is reserved
    // Legacy values kept so stored data hydrates without crashing. Never
    // surfaced via launchModes; new code never creates plans with these.
    // TODO: drop in v2 once data backfill is run.
    case knownPeople
    case friendsOfParticipants

    var id: String { rawValue }

    static var launchModes: [PlanVisibility] {
        [.sameContextOnly, .publicMatch, .inviteOnly]
    }

    var title: String {
        switch self {
        case .sameContextOnly:
            "Same context only"
        case .inviteOnly:
            "Invite only"
        case .publicMatch:
            "Public to your activities"
        case .knownPeople:
            "Known people"
        case .friendsOfParticipants:
            "Friends of participants"
        }
    }

    var subtitle: String {
        switch self {
        case .sameContextOnly:
            "Only people leaving this same moment can see it."
        case .inviteOnly:
            "Visible only through link or QR."
        case .publicMatch:
            "Visible to people who do this same activity at this same place."
        case .knownPeople:
            "Shown to people with prior trust context."
        case .friendsOfParticipants:
            "Available later if the product proves it needs it."
        }
    }

    var trustBadge: String {
        switch self {
        case .sameContextOnly:
            "Bounded"
        case .inviteOnly:
            "Direct"
        case .publicMatch:
            "Activity-matched"
        case .knownPeople:
            "Trusted"
        case .friendsOfParticipants:
            "Expanded"
        }
    }
}

enum PlanLifecycleState: String, CaseIterable, Identifiable {
    case open
    case forming
    case confirmed
    case active
    case closed

    var id: String { rawValue }

    var title: String {
        switch self {
        case .open:
            "Open"
        case .forming:
            "Forming"
        case .confirmed:
            "Confirmed"
        case .active:
            "Active"
        case .closed:
            "Closed"
        }
    }

    var summary: String {
        switch self {
        case .open:
            "Visible, lightweight, and easy to join."
        case .forming:
            "Momentum is building around one option."
        case .confirmed:
            "The next move is decided."
        case .active:
            "People are on the way or already there."
        case .closed:
            "This after-plan has wrapped."
        }
    }

    var shortActionLabel: String {
        switch self {
        case .open:
            "Needs a first yes"
        case .forming:
            "Close to locking"
        case .confirmed:
            "Ready to go"
        case .active:
            "In motion"
        case .closed:
            "Wrapped"
        }
    }

    var allowsConfirmationRoom: Bool {
        self != .closed
    }

    var progressLabel: String {
        switch self {
        case .open:
            "Step 1 of 5"
        case .forming:
            "Step 2 of 5"
        case .confirmed:
            "Step 3 of 5"
        case .active:
            "Step 4 of 5"
        case .closed:
            "Step 5 of 5"
        }
    }
}

enum ConfirmationAction: Equatable {
    case join
    case confirm
    case markActive
    case wrapPlan
    case none
}

enum InviteShareChannel: String, CaseIterable, Identifiable, Equatable {
    case sameContext
    case knownPeople
    case nearbyQR

    var id: String { rawValue }

    var title: String {
        switch self {
        case .sameContext:
            "People from this moment"
        case .knownPeople:
            "Known people"
        case .nearbyQR:
            "Nearby QR"
        }
    }

    var subtitle: String {
        switch self {
        case .sameContext:
            "Best when the plan is still forming and the right people are leaving the same thing."
        case .knownPeople:
            "Use this when one or two familiar faces would make joining feel easier."
        case .nearbyQR:
            "Keep it in-person for people already around you instead of widening the plan."
        }
    }

    var actionTitle: String {
        switch self {
        case .sameContext:
            "Prep same-context share"
        case .knownPeople:
            "Prep known-people invite"
        case .nearbyQR:
            "Show nearby QR"
        }
    }

    var systemImage: String {
        switch self {
        case .sameContext:
            "person.2.wave.2"
        case .knownPeople:
            "person.crop.circle.badge.checkmark"
        case .nearbyQR:
            "qrcode"
        }
    }
}

enum PlanParticipationState: String, Equatable {
    case browsing
    case interested
    case joined
    case confirmed

    var title: String {
        switch self {
        case .browsing:
            "Browsing"
        case .interested:
            "Interested"
        case .joined:
            "Joined"
        case .confirmed:
            "Confirmed"
        }
    }
}

struct ParticipantSummary: Identifiable, Equatable {
    let id: UUID
    var name: String
    var descriptor: String
    var isOrganizer: Bool
    var isKnown: Bool
}

struct AfterPlan: Identifiable, Equatable {
    let id: UUID
    var title: String
    var summary: String
    var contextTitle: String
    var hostName: String
    var hostDescriptor: String
    var mode: PlanMode
    var visibility: PlanVisibility
    var lifecycle: PlanLifecycleState
    var timeLabel: String
    var venueLabel: String
    var distanceLabel: String
    var trustBlurb: String
    var participants: [ParticipantSummary]
    var interestedCount: Int
    var placeSuggestions: [String]
    var participationState: PlanParticipationState

    var joinedCount: Int {
        participants.count
    }

    var meaningfulHostMemory: String? {
        let trimmed = hostDescriptor.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        guard trimmed != "Host", trimmed != "Hosting", trimmed != "Hosted" else { return nil }
        return trimmed
    }

    var momentumLine: String {
        switch lifecycle {
        case .open:
            "\(joinedCount) joined · \(interestedCount) interested"
        case .forming:
            "Picking up with \(joinedCount) joined"
        case .confirmed:
            "Locked with \(joinedCount) people"
        case .active:
            "Already in motion"
        case .closed:
            "Finished with \(joinedCount) people"
        }
    }

    /// Short, reassuring cue about how ready this plan is to join. Shown on discovery cards.
    var joinConfidenceCue: String {
        switch lifecycle {
        case .open:
            if joinedCount == 0 {
                return "Still early — soft interest helps"
            }
            return "\(joinedCount) joined · a few more makes it real"
        case .forming:
            if joinedCount >= 3 {
                return "Close to confirming"
            }
            return "Already taking shape"
        case .confirmed:
            return "Good to join — this is happening"
        case .active:
            return "Already in motion"
        case .closed:
            return ""
        }
    }

    /// Slightly longer readiness cue for Plan Detail, helping the viewer decide whether to commit.
    var readinessHint: String {
        switch lifecycle {
        case .open:
            if joinedCount == 0 {
                return "This plan is waiting for a first yes. Joining now helps it feel real."
            }
            return "A couple more people and this starts to take shape."
        case .forming:
            if joinedCount >= 3 {
                return "Waiting on one more person to lock this in."
            }
            return "There's enough interest to converge. Joining now locks your spot."
        case .confirmed:
            return "The details are set. You can join with confidence."
        case .active:
            return "Already underway — no more setup needed."
        case .closed:
            return ""
        }
    }

    /// Warm recap line for closed plans, summarizing the continuation outcome for the Activity surface.
    var recapLine: String {
        guard lifecycle == .closed else { return "" }
        if joinedCount >= 3 {
            return "You kept the moment going with \(joinedCount) people after \(contextTitle)."
        }
        if joinedCount > 0 {
            return "You followed through after \(contextTitle)."
        }
        return "A continuation from \(contextTitle)."
    }

    /// Lifecycle-aware explanation when the confirmation CTA is disabled.
    var confirmationDisabledReason: String {
        switch lifecycle {
        case .open:
            return "Waiting on a first yes before this can move forward."
        case .forming:
            return "One or two more joins and this can lock in."
        case .confirmed:
            return "This is confirmed — ready when you are."
        case .active, .closed:
            return ""
        }
    }

    var participationLabel: String {
        switch participationState {
        case .browsing:
            "You have not reacted yet."
        case .interested:
            "You signaled soft interest."
        case .joined:
            "You joined the plan."
        case .confirmed:
            "You are confirmed."
        }
    }

    var joinActionTitle: String {
        if lifecycle == .active {
            return "Already started"
        }

        if lifecycle == .closed {
            return "Wrapped"
        }

        return switch participationState {
        case .browsing, .interested:
            "Join"
        case .joined:
            "Joined"
        case .confirmed:
            "Confirmed"
        }
    }

    var interestedActionTitle: String {
        if lifecycle == .active {
            return "In motion"
        }

        if lifecycle == .closed {
            return "Wrapped"
        }

        return switch participationState {
        case .browsing:
            "Interested"
        case .interested:
            "Interested"
        case .joined:
            "Joined"
        case .confirmed:
            "Confirmed"
        }
    }

    var canJoin: Bool {
        switch participationState {
        case .browsing, .interested:
            lifecycle != .active && lifecycle != .closed
        case .joined, .confirmed:
            false
        }
    }

    var canExpressInterest: Bool {
        participationState == .browsing && lifecycle != .active && lifecycle != .closed
    }

    var canSuggestPlace: Bool {
        lifecycle == .open || lifecycle == .forming
    }

    var suggestPlaceActionTitle: String {
        if lifecycle == .confirmed {
            return "Place locked"
        }

        if lifecycle == .active {
            return "Already moving"
        }

        if lifecycle == .closed {
            return "Wrapped"
        }

        return placeSuggestions.isEmpty ? "Suggest place" : "Suggest another place"
    }

    var lifecycleHeadline: String {
        switch lifecycle {
        case .open:
            "Open for a first yes"
        case .forming:
            "Momentum is building"
        case .confirmed:
            "This next move is locked"
        case .active:
            "People are already on the way"
        case .closed:
            "This plan already wrapped"
        }
    }

    var nextStepGuidance: String {
        switch lifecycle {
        case .open:
            "A couple quick joins or a place suggestion will move this toward a real plan."
        case .forming:
            "There is enough signal to tighten the place and time without turning this into chat."
        case .confirmed:
            "Use the confirmation room to keep everyone aligned on one place and timing."
        case .active:
            "Keep the handoff simple. The plan already has enough detail to go."
        case .closed:
            "Closed plans stay visible in Activity so the shell feels like a real continuation loop."
        }
    }

    var lifecycleWindowTitle: String {
        switch lifecycle {
        case .open:
            "Open now"
        case .forming:
            "Momentum window"
        case .confirmed:
            "Locked in"
        case .active:
            "Already happening"
        case .closed:
            "Wrapped up"
        }
    }

    var lifecycleWindowDetail: String {
        switch lifecycle {
        case .open:
            "Best action now: join or mark interest so the plan feels real quickly."
        case .forming:
            "Best action now: tighten the place and move the group toward one committed option."
        case .confirmed:
            "Best action now: help people shift from \"sounds good\" to actually heading there."
        case .active:
            "No more setup is needed. The plan should read as real, not still collecting reactions."
        case .closed:
            "This plan stays visible as history only. Setup and participation actions should be over."
        }
    }

    var confirmationAction: ConfirmationAction {
        switch lifecycle {
        case .open, .forming:
            switch participationState {
            case .browsing, .interested:
                .join
            case .joined, .confirmed:
                .confirm
            }
        case .confirmed:
            switch participationState {
            case .browsing, .interested:
                .join
            case .joined, .confirmed:
                .markActive
            }
        case .active:
            switch participationState {
            case .joined, .confirmed:
                .wrapPlan
            default:
                .none
            }
        case .closed:
            .none
        }
    }

    var confirmationActionTitle: String {
        switch confirmationAction {
        case .join:
            return participationState == .interested ? "Join this plan" : "Join first"
        case .confirm:
            return "Lock this plan"
        case .markActive:
            return "Mark as on the way"
        case .wrapPlan:
            return "Wrap this plan"
        case .none:
            return lifecycle == .closed ? "Plan wrapped" : "Already in motion"
        }
    }

    var canTakeConfirmationAction: Bool {
        confirmationAction != .none
    }

    var confirmationRoomSubtitle: String {
        switch lifecycle {
        case .open:
            "The plan is still open. One clear place and a few committed people should pull it into focus."
        case .forming:
            "The group has momentum. This is the moment to converge on one option."
        case .confirmed:
            "The details are locked. The room should now help people shift from confirmed to actually moving."
        case .active:
            "This plan is already in motion, so the room should only reflect the agreed details."
        case .closed:
            "This room is closed because the plan already wrapped."
        }
    }

    var visibilityHeadline: String {
        switch visibility {
        case .sameContextOnly:
            "Visible to people from this context"
        case .inviteOnly:
            "Visible only through direct share"
        case .publicMatch:
            "Visible to people who do this activity here"
        case .knownPeople:
            "Visible to known or trust-linked people"
        case .friendsOfParticipants:
            "Visibility stays bounded"
        }
    }

    var visibilityDetail: String {
        switch lifecycle {
        case .open, .forming, .confirmed:
            return switch visibility {
            case .sameContextOnly:
                "People already leaving \(contextTitle) can see this while the plan is still live."
            case .inviteOnly:
                "This only moves through direct share paths, not broad discovery."
            case .publicMatch:
                "People who declared this same activity at this same place will see it. No broad discovery."
            case .knownPeople:
                "This reaches familiar or previously trusted people before anyone else."
            case .friendsOfParticipants:
                "This mode stays out of the MVP shell unless the trust model proves it is needed."
            }
        case .active:
            return "The plan is already in motion, so visibility should read as bounded status, not fresh outreach."
        case .closed:
            return "This plan remains readable as history only and should no longer circulate as a live option."
        }
    }

    var visibilityFootnote: String {
        switch visibility {
        case .sameContextOnly:
            "This should feel like shared activity follow-through, not random local discovery."
        case .inviteOnly:
            "People need a direct handoff to see this plan."
        case .publicMatch:
            "Match is exact on activity + venue. Not a city-wide feed."
        case .knownPeople:
            "Known people outrank strangers in this trust model."
        case .friendsOfParticipants:
            "Expanded visibility is intentionally deferred."
        }
    }

    var safetyEntryTitle: String {
        "Need help? Open Safety Center"
    }

    var safetyEntryDetail: String {
        switch lifecycle {
        case .open, .forming, .confirmed:
            "Report or block from this plan if the context, host, or participant behavior feels off."
        case .active:
            "Safety options still apply even after the plan is in motion."
        case .closed:
            "Safety options remain available for follow-up on a plan that already wrapped."
        }
    }

    var canShareInvite: Bool {
        lifecycle == .open || lifecycle == .forming || lifecycle == .confirmed
    }

    var canHandoffToText: Bool {
        lifecycle == .confirmed || lifecycle == .active
    }

    var handoffTextBody: String {
        var lines = [title]
        if !venueLabel.isEmpty { lines.append(venueLabel) }
        if !timeLabel.isEmpty { lines.append(timeLabel) }
        lines.append("afterplans://join/\(id.uuidString)")
        return lines.joined(separator: "\n")
    }

    var handoffCTATitle: String {
        lifecycle == .active ? "Share details with the group" : "Continue in Messages"
    }

    var handoffSubtitle: String {
        switch lifecycle {
        case .confirmed:
            return "Send the final details to a group text so everyone knows where to go."
        case .active:
            return "Share the plan details with anyone still coordinating."
        default:
            return ""
        }
    }

    var shareable: ShareablePayload {
        let urlString = "afterplans://join/\(id.uuidString)"
        let url = URL(string: urlString) ?? URL(string: "afterplans://join")!
        return ShareablePayload(
            url: url,
            text: "Join \"\(title)\" on After Plans — what's next after \(contextTitle).",
            qrString: urlString
        )
    }

    var shareActionTitle: String {
        switch lifecycle {
        case .open:
            "Invite from this moment"
        case .forming:
            "Bring in the right people"
        case .confirmed:
            "Bring in the last right people"
        case .active:
            "Already in motion"
        case .closed:
            "Wrapped"
        }
    }

    var shareActionSubtitle: String {
        switch lifecycle {
        case .open:
            "Keep sharing lightweight so a first yes feels easy."
        case .forming:
            "Use bounded invites to help this plan feel real without opening it wider."
        case .confirmed:
            "Use sharing only for the last people who already fit this plan."
        case .active:
            "Avoid sending new invites once the group is already moving."
        case .closed:
            "Closed plans should not keep circulating."
        }
    }

    var shareAudienceHeadline: String {
        switch visibility {
        case .sameContextOnly:
            "Start with people from this same context."
        case .inviteOnly:
            "Keep it direct and intentional."
        case .publicMatch:
            "Reaches people who declared this activity here."
        case .knownPeople:
            "Favor familiar people over broad outreach."
        case .friendsOfParticipants:
            "Do not widen this in the MVP shell."
        }
    }

    var shareAudienceDetail: String {
        switch visibility {
        case .sameContextOnly:
            "This plan should reach the people already leaving \(contextTitle), not a generic nearby crowd."
        case .inviteOnly:
            "This plan only makes sense if someone already close to the moment passes it along."
        case .publicMatch:
            "Match is exact on activity + venue from people's onboarding declarations. No broader local discovery."
        case .knownPeople:
            "A small nudge to familiar people is enough. The goal is easy joining, not recruiting."
        case .friendsOfParticipants:
            "This visibility mode stays out of launch share flows."
        }
    }

    var shareJoinFraming: String {
        switch lifecycle {
        case .open:
            "Share it like an easy next move, not a commitment. A soft yes should be enough to get momentum started."
        case .forming:
            "Share it as a lightweight join for people already nearby or already known to the group."
        case .confirmed:
            "Share it as a last-call join for the people who were likely coming anyway."
        case .active:
            "The plan is already real. Sharing should stop before it feels like late outreach."
        case .closed:
            "There is nothing left to join here."
        }
    }

    var inviteChannels: [InviteShareChannel] {
        guard canShareInvite else { return [] }

        return switch visibility {
        case .sameContextOnly:
            [InviteShareChannel.sameContext, InviteShareChannel.nearbyQR]
        case .inviteOnly:
            [InviteShareChannel.knownPeople, InviteShareChannel.nearbyQR]
        case .publicMatch:
            [InviteShareChannel.sameContext, InviteShareChannel.nearbyQR]
        case .knownPeople:
            [InviteShareChannel.knownPeople, InviteShareChannel.sameContext]
        case .friendsOfParticipants:
            [InviteShareChannel.sameContext]
        }
    }
}

struct UserProfile: Equatable {
    let id: UUID
    var firstName: String
    var descriptor: String
    var visibilityDefault: PlanVisibility
    var trustHeadline: String
}

struct InvitePreview: Equatable {
    var title: String
    var subtitle: String
    var audienceHeadline: String
    var audienceDetail: String
    var joinFraming: String
    var linkLabel: String
    var qrLabel: String
    var nextStepTitle: String
    var nextStepDetail: String
}

struct InviteShareState: Equatable {
    var channel: InviteShareChannel
    var statusTitle: String
    var statusDetail: String
}

struct SafetyReason: Identifiable, Equatable {
    let id: String
    var title: String
    var explanation: String
}

struct ShareablePayload: Equatable {
    var url: URL
    var text: String
    var qrString: String
}
