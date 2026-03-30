import Foundation
import SwiftData

enum PersonalBestService {
    static func refresh(with catchRecord: CatchRecord, in context: ModelContext) throws {
        let species = catchRecord.species.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !species.isEmpty else { return }

        let descriptor = FetchDescriptor<PersonalBest>(
            predicate: #Predicate { record in
                record.species == species
            }
        )
        let existing = try context.fetch(descriptor).first

        if let existing {
            if let length = catchRecord.lengthCm {
                existing.longestLengthCm = max(existing.longestLengthCm ?? 0, length)
            }
            if let weight = catchRecord.weightKg {
                existing.heaviestWeightKg = max(existing.heaviestWeightKg ?? 0, weight)
            }
            existing.updatedAt = .now
        } else {
            let personalBest = PersonalBest(
                species: species,
                longestLengthCm: catchRecord.lengthCm,
                heaviestWeightKg: catchRecord.weightKg,
                updatedAt: .now
            )
            context.insert(personalBest)
        }
    }

    static func rebuild(in context: ModelContext) throws {
        let existingRecords = try context.fetch(FetchDescriptor<PersonalBest>())
        for record in existingRecords {
            context.delete(record)
        }

        let catches = try context.fetch(FetchDescriptor<CatchRecord>())
        let grouped = Dictionary(grouping: catches) { catchRecord in
            catchRecord.species.trimmingCharacters(in: .whitespacesAndNewlines)
        }

        for (species, records) in grouped where !species.isEmpty {
            let personalBest = PersonalBest(
                species: species,
                longestLengthCm: records.compactMap(\.lengthCm).max(),
                heaviestWeightKg: records.compactMap(\.weightKg).max(),
                updatedAt: .now
            )
            context.insert(personalBest)
        }
    }
}
