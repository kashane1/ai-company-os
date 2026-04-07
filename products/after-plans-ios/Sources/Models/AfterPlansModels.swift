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
    case knownPeople
    case friendsOfParticipants

    var id: String { rawValue }

    static var launchModes: [PlanVisibility] {
        [.sameContextOnly, .inviteOnly, .knownPeople]
    }

    var title: String {
        switch self {
        case .sameContextOnly:
            "Same context only"
        case .inviteOnly:
            "Invite only"
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
        switch participationState {
        case .browsing, .interested:
            "Join"
        case .joined:
            "Joined"
        case .confirmed:
            "Confirmed"
        }
    }

    var interestedActionTitle: String {
        switch participationState {
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
            lifecycle != .closed
        case .joined, .confirmed:
            false
        }
    }

    var canExpressInterest: Bool {
        participationState == .browsing && lifecycle != .closed
    }

    var suggestPlaceActionTitle: String {
        placeSuggestions.isEmpty ? "Suggest place" : "Suggest another place"
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

    var confirmationActionTitle: String {
        switch participationState {
        case .browsing:
            "Join first"
        case .interested:
            "Join and lock it"
        case .joined:
            lifecycle == .confirmed || lifecycle == .active ? "You're confirmed" : "Lock this plan"
        case .confirmed:
            "You're confirmed"
        }
    }

    var confirmationRoomSubtitle: String {
        switch lifecycle {
        case .open:
            "The plan is still open. One clear place and a few committed people should pull it into focus."
        case .forming:
            "The group has momentum. This is the moment to converge on one option."
        case .confirmed:
            "The details are locked. The room now acts as the final alignment surface."
        case .active:
            "This plan is already in motion, so the room just reflects the agreed details."
        case .closed:
            "This room is closed because the plan already wrapped."
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
    var linkLabel: String
    var qrLabel: String
}

struct SafetyReason: Identifiable, Equatable {
    let id: String
    var title: String
    var explanation: String
}
