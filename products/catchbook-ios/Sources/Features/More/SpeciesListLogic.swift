import Foundation

enum SpeciesListLogic {
    struct SpeciesEntry: Identifiable {
        let id: String
        let species: String
        let count: Int
    }

    static func speciesEntries(from catches: [CatchRecord]) -> [SpeciesEntry] {
        let grouped = Dictionary(grouping: catches) { catch_ in
            TripEditingLogic.normalizedText(catch_.species)
        }

        return grouped
            .filter { !$0.key.isEmpty }
            .map { SpeciesEntry(id: $0.key, species: $0.key, count: $0.value.count) }
            .sorted { $0.count > $1.count }
    }
}
