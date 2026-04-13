import Foundation
import SwiftData
import SwiftUI
import UniformTypeIdentifiers

extension UTType {
    static let fishingLogbookBackup = UTType(
        exportedAs: "io.aicompanyos.products.fishinglogbook.backup",
        conformingTo: .package
    )
}

struct LogbookBackupAppMetadata: Codable, Equatable {
    let appBundleIdentifier: String
    let appVersion: String
    let buildNumber: String

    static func current(bundle: Bundle = .main) -> LogbookBackupAppMetadata {
        LogbookBackupAppMetadata(
            appBundleIdentifier: bundle.bundleIdentifier ?? "io.aicompanyos.products.fishinglogbook",
            appVersion: bundle.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "0.0.0",
            buildNumber: bundle.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "0"
        )
    }
}

struct LogbookBackupCounts: Codable, Equatable {
    let waterbodies: Int
    let spots: Int
    let conditionSnapshots: Int
    let trips: Int
    let catches: Int
    let photos: Int
}

struct LogbookBackupManifest: Codable, Equatable {
    let formatVersion: Int
    let exportedAt: Date
    let appBundleIdentifier: String
    let appVersion: String
    let buildNumber: String
    let counts: LogbookBackupCounts
}

struct WaterbodyExportRecord: Codable, Equatable {
    let id: UUID
    let name: String
    let type: String
    let latitude: Double?
    let longitude: Double?
    let isPrivate: Bool
    let createdAt: Date
}

struct SpotExportRecord: Codable, Equatable {
    let id: UUID
    let waterbodyId: UUID?
    let title: String
    let latitude: Double?
    let longitude: Double?
    let notes: String
    let isPrivate: Bool
    let createdAt: Date
}

struct ConditionSnapshotExportRecord: Codable, Equatable {
    let id: UUID
    let capturedAt: Date
    let latitude: Double?
    let longitude: Double?
    let placeSummary: String?
    let timeWindowSummary: String?
    let lightLevelSummary: String?
    let temperatureC: Double?
    let weatherSummary: String?
    let windSummary: String?
    let cloudCoverSummary: String?
    let precipitationSummary: String?
    let waterClarity: String
    let moonPhase: String
    let pressureHPa: Double?
    let tideState: String
    let captureStatus: String
    let source: String
}

struct TripExportRecord: Codable, Equatable {
    let id: UUID
    let waterbodyId: UUID?
    let spotId: UUID?
    let conditionSnapshotId: UUID?
    let startAt: Date
    let endAt: Date?
    let targetSpecies: String
    let notes: String
    let outcome: String
}

struct CatchExportRecord: Codable, Equatable {
    let id: UUID
    let tripId: UUID?
    let species: String
    let caughtAt: Date
    let lureOrBait: String
    let method: String
    let weightKg: Double?
    let lengthCm: Double?
    let waterDepthM: Double?
    let note: String
    let disposition: String
    let photoContentType: String?
    let photoFilename: String?
    let photoFilenames: [String]?
}

struct LogbookBackupPhotoAsset: Equatable {
    let filename: String
    let data: Data
}

struct LogbookBackupPackage {
    let manifest: LogbookBackupManifest
    let waterbodies: [WaterbodyExportRecord]
    let spots: [SpotExportRecord]
    let conditionSnapshots: [ConditionSnapshotExportRecord]
    let trips: [TripExportRecord]
    let catches: [CatchExportRecord]
    let photos: [LogbookBackupPhotoAsset]

    static func placeholder() -> LogbookBackupPackage {
        .init(
            manifest: LogbookBackupManifest(
                formatVersion: 1,
                exportedAt: .now,
                appBundleIdentifier: LogbookBackupAppMetadata.current().appBundleIdentifier,
                appVersion: LogbookBackupAppMetadata.current().appVersion,
                buildNumber: LogbookBackupAppMetadata.current().buildNumber,
                counts: LogbookBackupCounts(
                    waterbodies: 0,
                    spots: 0,
                    conditionSnapshots: 0,
                    trips: 0,
                    catches: 0,
                    photos: 0
                )
            ),
            waterbodies: [],
            spots: [],
            conditionSnapshots: [],
            trips: [],
            catches: [],
            photos: []
        )
    }

    func makeFileWrapper() throws -> FileWrapper {
        let encoder = LogbookBackupExporter.makeJSONEncoder()

        let manifestWrapper = FileWrapper(regularFileWithContents: try encoder.encode(manifest))

        let dataDirectory = FileWrapper(directoryWithFileWrappers: [
            "waterbodies.json": FileWrapper(regularFileWithContents: try encoder.encode(waterbodies)),
            "spots.json": FileWrapper(regularFileWithContents: try encoder.encode(spots)),
            "condition_snapshots.json": FileWrapper(regularFileWithContents: try encoder.encode(conditionSnapshots)),
            "trips.json": FileWrapper(regularFileWithContents: try encoder.encode(trips)),
            "catches.json": FileWrapper(regularFileWithContents: try encoder.encode(catches)),
        ])

        let catchMediaDirectory = FileWrapper(
            directoryWithFileWrappers: Dictionary(
                uniqueKeysWithValues: photos.map { asset in
                    (asset.filename, FileWrapper(regularFileWithContents: asset.data))
                }
            )
        )

        let mediaDirectory = FileWrapper(directoryWithFileWrappers: [
            "catches": catchMediaDirectory,
        ])

        return FileWrapper(directoryWithFileWrappers: [
            "manifest.json": manifestWrapper,
            "data": dataDirectory,
            "media": mediaDirectory,
        ])
    }
}

struct LogbookBackupDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.fishingLogbookBackup] }
    static var writableContentTypes: [UTType] { [.fishingLogbookBackup] }

    let package: LogbookBackupPackage

    init(package: LogbookBackupPackage) {
        self.package = package
    }

    init(configuration: ReadConfiguration) throws {
        throw CocoaError(.fileReadUnsupportedScheme)
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        try package.makeFileWrapper()
    }
}

enum LogbookBackupExporter {
    static let formatVersion = 1
    static let defaultFilename = "Catchbook Backup"

    static func makeDocument(
        context: ModelContext,
        exportedAt: Date = .now,
        appMetadata: LogbookBackupAppMetadata = .current()
    ) throws -> LogbookBackupDocument {
        let waterbodies = try context.fetch(FetchDescriptor<Waterbody>())
        let spots = try context.fetch(FetchDescriptor<Spot>())
        let conditionSnapshots = try context.fetch(FetchDescriptor<ConditionSnapshot>())
        let trips = try context.fetch(FetchDescriptor<Trip>())
        let catches = try context.fetch(FetchDescriptor<CatchRecord>())

        let package = makePackage(
            waterbodies: waterbodies,
            spots: spots,
            conditionSnapshots: conditionSnapshots,
            trips: trips,
            catches: catches,
            exportedAt: exportedAt,
            appMetadata: appMetadata
        )

        return LogbookBackupDocument(package: package)
    }

    static func makePackage(
        waterbodies: [Waterbody],
        spots: [Spot],
        conditionSnapshots: [ConditionSnapshot],
        trips: [Trip],
        catches: [CatchRecord],
        exportedAt: Date = .now,
        appMetadata: LogbookBackupAppMetadata
    ) -> LogbookBackupPackage {
        let sortedWaterbodies = waterbodies.sorted {
            ($0.createdAt, $0.id.uuidString) < ($1.createdAt, $1.id.uuidString)
        }
        let sortedSpots = spots.sorted {
            ($0.createdAt, $0.id.uuidString) < ($1.createdAt, $1.id.uuidString)
        }
        let sortedConditionSnapshots = conditionSnapshots.sorted {
            ($0.capturedAt, $0.id.uuidString) < ($1.capturedAt, $1.id.uuidString)
        }
        let sortedTrips = trips.sorted {
            ($0.startAt, $0.id.uuidString) < ($1.startAt, $1.id.uuidString)
        }
        let sortedCatches = catches.sorted {
            ($0.caughtAt, $0.id.uuidString) < ($1.caughtAt, $1.id.uuidString)
        }

        let photoAssets = sortedCatches.flatMap(photoAssets(for:))

        let waterbodyRecords = sortedWaterbodies.map { waterbody in
            WaterbodyExportRecord(
                id: waterbody.id,
                name: waterbody.name,
                type: waterbody.type.rawValue,
                latitude: waterbody.latitude,
                longitude: waterbody.longitude,
                isPrivate: waterbody.isPrivate,
                createdAt: waterbody.createdAt
            )
        }

        let spotRecords = sortedSpots.map { spot in
            SpotExportRecord(
                id: spot.id,
                waterbodyId: spot.waterbody?.id,
                title: spot.title,
                latitude: spot.latitude,
                longitude: spot.longitude,
                notes: spot.notes,
                isPrivate: spot.isPrivate,
                createdAt: spot.createdAt
            )
        }

        let conditionSnapshotRecords = sortedConditionSnapshots.map { snapshot in
            ConditionSnapshotExportRecord(
                id: snapshot.id,
                capturedAt: snapshot.capturedAt,
                latitude: snapshot.latitude,
                longitude: snapshot.longitude,
                placeSummary: snapshot.placeSummary,
                timeWindowSummary: snapshot.timeWindowSummary,
                lightLevelSummary: snapshot.lightLevelSummary,
                temperatureC: snapshot.temperatureC,
                weatherSummary: snapshot.weatherSummary,
                windSummary: snapshot.windSummary,
                cloudCoverSummary: snapshot.cloudCoverSummary,
                precipitationSummary: snapshot.precipitationSummary,
                waterClarity: snapshot.waterClarity.rawValue,
                moonPhase: snapshot.moonPhase.rawValue,
                pressureHPa: snapshot.pressureHPa,
                tideState: snapshot.tideState.rawValue,
                captureStatus: snapshot.captureStatus.rawValue,
                source: snapshot.source.rawValue
            )
        }

        let tripRecords = sortedTrips.map { trip in
            TripExportRecord(
                id: trip.id,
                waterbodyId: trip.waterbody?.id,
                spotId: trip.spot?.id,
                conditionSnapshotId: trip.conditionSnapshot?.id,
                startAt: trip.startAt,
                endAt: trip.endAt,
                targetSpecies: trip.targetSpecies,
                notes: trip.notes,
                outcome: trip.outcome.rawValue
            )
        }

        let catchRecords = sortedCatches.map { catchRecord in
            CatchExportRecord(
                id: catchRecord.id,
                tripId: catchRecord.trip?.id,
                species: catchRecord.species,
                caughtAt: catchRecord.caughtAt,
                lureOrBait: catchRecord.lureOrBait,
                method: catchRecord.method,
                weightKg: catchRecord.weightKg,
                lengthCm: catchRecord.lengthCm,
                waterDepthM: catchRecord.waterDepthM,
                note: catchRecord.note,
                disposition: catchRecord.disposition.rawValue,
                photoContentType: catchRecord.primaryPhotoContentType,
                photoFilename: photoFilename(for: catchRecord),
                photoFilenames: photoFilenames(for: catchRecord)
            )
        }

        let counts = LogbookBackupCounts(
            waterbodies: waterbodyRecords.count,
            spots: spotRecords.count,
            conditionSnapshots: conditionSnapshotRecords.count,
            trips: tripRecords.count,
            catches: catchRecords.count,
            photos: photoAssets.count
        )

        let manifest = LogbookBackupManifest(
            formatVersion: formatVersion,
            exportedAt: exportedAt,
            appBundleIdentifier: appMetadata.appBundleIdentifier,
            appVersion: appMetadata.appVersion,
            buildNumber: appMetadata.buildNumber,
            counts: counts
        )

        return LogbookBackupPackage(
            manifest: manifest,
            waterbodies: waterbodyRecords,
            spots: spotRecords,
            conditionSnapshots: conditionSnapshotRecords,
            trips: tripRecords,
            catches: catchRecords,
            photos: photoAssets
        )
    }

    static func makeJSONEncoder() -> JSONEncoder {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }

    private static func photoAssets(for catchRecord: CatchRecord) -> [LogbookBackupPhotoAsset] {
        let assets = catchRecord.sortedPhotos.enumerated().compactMap { index, photo -> LogbookBackupPhotoAsset? in
            guard let photoData = photo.photoData else { return nil }
            guard let filename = photoFilename(for: catchRecord, index: index, contentType: photo.photoContentType) else { return nil }
            return LogbookBackupPhotoAsset(filename: filename, data: photoData)
        }

        if !assets.isEmpty {
            return assets
        }

        guard let photoData = catchRecord.photoData else { return [] }
        guard let filename = photoFilename(for: catchRecord) else { return [] }
        return [LogbookBackupPhotoAsset(filename: filename, data: photoData)]
    }

    private static func photoFilename(for catchRecord: CatchRecord) -> String? {
        guard catchRecord.primaryPhotoData != nil else { return nil }
        return photoFilename(for: catchRecord, index: 0, contentType: catchRecord.primaryPhotoContentType)
    }

    private static func photoFilenames(for catchRecord: CatchRecord) -> [String]? {
        let filenames = catchRecord.sortedPhotos.enumerated().compactMap { index, photo in
            photoFilename(for: catchRecord, index: index, contentType: photo.photoContentType)
        }

        if !filenames.isEmpty {
            return filenames
        }

        return photoFilename(for: catchRecord).map { [$0] }
    }

    private static func photoFilename(for catchRecord: CatchRecord, index: Int, contentType: String?) -> String? {
        let resolvedExtension: String
        if let contentType = contentType?.lowercased(),
           contentType == "image/jpeg" || contentType == "image/jpg" {
            resolvedExtension = "jpg"
        } else if let contentType,
                  let type = UTType(mimeType: contentType),
                  let preferredExtension = type.preferredFilenameExtension {
            resolvedExtension = preferredExtension
        } else {
            resolvedExtension = "jpg"
        }

        if index == 0 {
            return "\(catchRecord.id.uuidString.lowercased()).\(resolvedExtension.lowercased())"
        }

        return "\(catchRecord.id.uuidString.lowercased())-\(index).\(resolvedExtension.lowercased())"
    }
}
