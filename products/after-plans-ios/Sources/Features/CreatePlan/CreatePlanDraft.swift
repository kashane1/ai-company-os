import Foundation

struct CreatePlanDraft: Equatable {
    var mode: PlanMode = .defaultOption
    var title: String = ""
    var summary: String = ""
    var venueHint: String = ""
    var timeHint: String = "Right after this"
    var visibility: PlanVisibility = .sameContextOnly
    /// Required when `visibility == .publicMatch`. Pinned to a specific
    /// activity so the plan only surfaces to people who declared it.
    var activityID: UUID?
    /// Required when `visibility == .publicMatch`. Anchors the plan to
    /// a real (or freeform) venue.
    var venueID: UUID?

    var trimmedTitle: String {
        title.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var trimmedVenueHint: String {
        venueHint.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    func validationMessage(hasContext: Bool) -> String? {
        if visibility == .publicMatch {
            // Public-match plans don't need a context — they reach
            // people through declared activities — but they DO need
            // both an activity and a venue.
            guard activityID != nil else {
                return "Pick an activity so the right people see this."
            }
            guard venueID != nil else {
                return "Pick a place so people know where to show up."
            }
        } else {
            guard hasContext else {
                return "Pick the activity that just ended before you start what's next."
            }
        }

        guard !trimmedTitle.isEmpty else {
            return "Give people a simple headline so they can join quickly."
        }

        if mode == .exact && visibility != .publicMatch && trimmedVenueHint.isEmpty {
            return "Exact plans should name the place up front."
        }

        return nil
    }
}
