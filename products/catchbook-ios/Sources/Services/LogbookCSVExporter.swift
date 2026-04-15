import Foundation
import SwiftData
import SwiftUI
import UniformTypeIdentifiers

/// Flat-file CSV export for catches — the spreadsheet counterpart to the
/// full Logbook Backup. The backup format is a package with JSON + photos
/// designed for round-tripping; the CSV is a single table designed for
/// analysis in Numbers / Excel / Sheets and is read-only.
///
/// One row per catch, with trip/spot/waterbody context denormalized so the
/// file is useful without joining anything.
struct LogbookCSVDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.commaSeparatedText] }
    static var writableContentTypes: [UTType] { [.commaSeparatedText] }

    let csv: String

    init(csv: String) {
        self.csv = csv
    }

    init(configuration: ReadConfiguration) throws {
        throw CocoaError(.fileReadUnsupportedScheme)
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        guard let data = csv.data(using: .utf8) else {
            throw CocoaError(.fileWriteUnknown)
        }
        return FileWrapper(regularFileWithContents: data)
    }
}

enum LogbookCSVExporter {
    static let defaultFilename = "Catchbook Catches"

    /// Header order is locked — users may depend on column positions for
    /// spreadsheets they've already built against an earlier export.
    static let header: [String] = [
        "caught_at",
        "species",
        "weight_kg",
        "length_cm",
        "water_depth_m",
        "disposition",
        "lure_or_bait",
        "method",
        "gear",
        "note",
        "photo_count",
        "trip_id",
        "trip_title",
        "trip_start_at",
        "trip_end_at",
        "trip_outcome",
        "trip_target_species",
        "spot_title",
        "spot_latitude",
        "spot_longitude",
        "waterbody_name",
        "waterbody_type",
        "temperature_c",
        "weather_summary",
        "wind_summary",
        "water_clarity",
        "moon_phase",
        "tide_state",
    ]

    static func makeDocument(context: ModelContext) throws -> LogbookCSVDocument {
        let catches = try context.fetch(FetchDescriptor<CatchRecord>())
        return LogbookCSVDocument(csv: makeCSV(catches: catches))
    }

    /// Pure, deterministic string-producing step — unit-testable without
    /// touching SwiftData, file I/O, or UIKit.
    static func makeCSV(catches: [CatchRecord]) -> String {
        let sorted = catches.sorted { $0.caughtAt < $1.caughtAt }
        let isoFormatter = ISO8601DateFormatter()
        isoFormatter.formatOptions = [.withInternetDateTime]

        var lines: [String] = []
        lines.append(header.map(escape).joined(separator: ","))

        for record in sorted {
            let trip = record.trip
            let spot = trip?.spot
            let waterbody = trip?.waterbody ?? spot?.waterbody
            let snapshot = trip?.conditionSnapshot

            let fields: [String] = [
                isoFormatter.string(from: record.caughtAt),
                record.species,
                formatNumber(record.weightKg),
                formatNumber(record.lengthCm),
                formatNumber(record.waterDepthM),
                record.disposition == .notRecorded ? "" : record.disposition.rawValue,
                record.lureOrBait,
                record.method,
                record.gear,
                record.note,
                String(record.photoCount),
                trip?.id.uuidString ?? "",
                trip?.title ?? "",
                trip.map { isoFormatter.string(from: $0.startAt) } ?? "",
                trip?.endAt.map { isoFormatter.string(from: $0) } ?? "",
                trip?.outcome.rawValue ?? "",
                trip?.targetSpecies ?? "",
                spot?.title ?? "",
                formatNumber(spot?.latitude),
                formatNumber(spot?.longitude),
                waterbody?.name ?? "",
                waterbody?.type.rawValue ?? "",
                formatNumber(snapshot?.temperatureC),
                snapshot?.weatherSummary ?? "",
                snapshot?.windSummary ?? "",
                snapshot.map { $0.waterClarity == .notRecorded ? "" : $0.waterClarity.rawValue } ?? "",
                snapshot?.moonPhase.rawValue ?? "",
                snapshot.map { $0.tideState == .notRecorded ? "" : $0.tideState.rawValue } ?? "",
            ]

            lines.append(fields.map(escape).joined(separator: ","))
        }

        // Trailing newline so POSIX tools treat the last row as a real line.
        return lines.joined(separator: "\n") + "\n"
    }

    /// RFC 4180-ish escaping: wrap in quotes if the field contains a
    /// comma, quote, newline, or carriage return. Internal quotes are
    /// doubled. Keeps the output safe to paste into any spreadsheet.
    static func escape(_ field: String) -> String {
        let needsQuoting = field.contains(where: { $0 == "," || $0 == "\"" || $0 == "\n" || $0 == "\r" })
        guard needsQuoting else { return field }
        let escaped = field.replacingOccurrences(of: "\"", with: "\"\"")
        return "\"\(escaped)\""
    }

    private static func formatNumber(_ value: Double?) -> String {
        guard let value else { return "" }
        // Use a stable, locale-independent format so CSVs parse the same
        // way in every region. Strip trailing zeros past the third decimal.
        var s = String(format: "%.3f", value)
        while s.hasSuffix("0") { s.removeLast() }
        if s.hasSuffix(".") { s.removeLast() }
        return s
    }
}
