import Foundation

enum CatchOptionalField: String, CaseIterable, Identifiable {
    case disposition
    case method
    case gear
    case weight
    case length
    case waterDepth
    case note
    case photo

    static let appStorageKey = "catchbook.catch.visibleOptionalFields"
    static let defaultFields: Set<CatchOptionalField> = [
        .disposition,
        .method,
        .gear,
        .note,
        .photo,
    ]

    var id: String { rawValue }

    var label: String {
        switch self {
        case .disposition: return "Disposition"
        case .method: return "Method"
        case .gear: return "Gear"
        case .weight: return "Weight"
        case .length: return "Length"
        case .waterDepth: return "Water depth"
        case .note: return "Notes"
        case .photo: return "Photos"
        }
    }

    static func storedValue(for fields: Set<CatchOptionalField>) -> String {
        fields.map(\.rawValue)
            .sorted()
            .joined(separator: ",")
    }

    static func fields(from storedValue: String) -> Set<CatchOptionalField> {
        let trimmed = storedValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return defaultFields }

        let values = trimmed
            .split(separator: ",")
            .compactMap { CatchOptionalField(rawValue: String($0)) }
        return values.isEmpty ? defaultFields : Set(values)
    }
}

enum QuickCatchEntryMode: String, CaseIterable, Identifiable {
    case full
    case tally

    static let appStorageKey = "catchbook.log.quickCatchEntryMode"

    var id: String { rawValue }

    var label: String {
        switch self {
        case .full: return "Quick Catch"
        case .tally: return "Tally Mode"
        }
    }
}
