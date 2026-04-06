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
                if existing.longestLengthCm == nil || length >= (existing.longestLengthCm ?? 0) {
                    existing.longestLengthCm = length
                    existing.longestCatchID = catchRecord.id
                }
            }
            if let weight = catchRecord.weightKg {
                if existing.heaviestWeightKg == nil || weight >= (existing.heaviestWeightKg ?? 0) {
                    existing.heaviestWeightKg = weight
                    existing.heaviestCatchID = catchRecord.id
                }
            }
            existing.updatedAt = .now
        } else {
            let personalBest = PersonalBest(
                species: species,
                longestLengthCm: catchRecord.lengthCm,
                heaviestWeightKg: catchRecord.weightKg,
                longestCatchID: catchRecord.lengthCm == nil ? nil : catchRecord.id,
                heaviestCatchID: catchRecord.weightKg == nil ? nil : catchRecord.id,
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
            let longestRecord = records
                .filter { $0.lengthCm != nil }
                .max { lhs, rhs in
                    let lhsLength = lhs.lengthCm ?? 0
                    let rhsLength = rhs.lengthCm ?? 0
                    if lhsLength != rhsLength {
                        return lhsLength < rhsLength
                    }
                    return lhs.caughtAt < rhs.caughtAt
                }
            let heaviestRecord = records
                .filter { $0.weightKg != nil }
                .max { lhs, rhs in
                    let lhsWeight = lhs.weightKg ?? 0
                    let rhsWeight = rhs.weightKg ?? 0
                    if lhsWeight != rhsWeight {
                        return lhsWeight < rhsWeight
                    }
                    return lhs.caughtAt < rhs.caughtAt
                }
            let personalBest = PersonalBest(
                species: species,
                longestLengthCm: records.compactMap(\.lengthCm).max(),
                heaviestWeightKg: records.compactMap(\.weightKg).max(),
                longestCatchID: longestRecord?.id,
                heaviestCatchID: heaviestRecord?.id,
                updatedAt: .now
            )
            context.insert(personalBest)
        }
    }
}
