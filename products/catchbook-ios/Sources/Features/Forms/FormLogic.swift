import Foundation

struct SpotFormDraft {
    let title: String
    let notes: String
}

enum SpotFormLogic {
    static func canSave(title: String, selectedWaterbodyID: UUID?) -> Bool {
        !TripEditingLogic.normalizedText(title).isEmpty && selectedWaterbodyID != nil
    }

    static func draft(title: String, notes: String) -> SpotFormDraft {
        SpotFormDraft(
            title: TripEditingLogic.normalizedText(title),
            notes: TripEditingLogic.normalizedText(notes)
        )
    }
}

enum WaterbodyFormLogic {
    static func canSave(name: String) -> Bool {
        !TripEditingLogic.normalizedText(name).isEmpty
    }

    static func normalizedName(_ name: String) -> String {
        TripEditingLogic.normalizedText(name)
    }
}
