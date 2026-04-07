import Foundation

struct CreatePlanDraft: Equatable {
    var mode: PlanMode = .defaultOption
    var title: String = ""
    var summary: String = ""
    var venueHint: String = ""
    var timeHint: String = "Right after this"
    var visibility: PlanVisibility = .sameContextOnly

    var trimmedTitle: String {
        title.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var trimmedVenueHint: String {
        venueHint.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    func validationMessage(hasContext: Bool) -> String? {
        guard hasContext else {
            return "Pick the activity that just ended before you start what's next."
        }

        guard !trimmedTitle.isEmpty else {
            return "Give people a simple headline so they can join quickly."
        }

        if mode == .exact && trimmedVenueHint.isEmpty {
            return "Exact plans should name the place up front."
        }

        return nil
    }
}
