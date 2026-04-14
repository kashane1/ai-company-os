import Foundation

enum SavedLuresLogic {
    static func canSave(name: String) -> Bool {
        !TripEditingLogic.normalizedText(name).isEmpty
    }

    struct LureDraft {
        let name: String
        let color: String
        let notes: String
    }

    static func draft(name: String, color: String, notes: String) -> LureDraft {
        LureDraft(
            name: TripEditingLogic.normalizedText(name),
            color: TripEditingLogic.normalizedText(color),
            notes: notes.trimmingCharacters(in: .whitespacesAndNewlines)
        )
    }
}
