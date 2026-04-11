import Foundation
import SwiftData
import XCTest
@testable import Catchbook

final class LogbookBackupExporterTests: XCTestCase {
    func testMakePackagePreservesCanonicalEntitiesAndForeignKeys() {
        let waterbody = Waterbody(
            name: "Delta",
            type: .river,
            latitude: 38.12,
            longitude: -121.50,
            createdAt: Date(timeIntervalSince1970: 100)
        )
        let spot = Spot(
            title: "Rock Wall",
            waterbody: waterbody,
            latitude: 38.10,
            longitude: -121.55,
            notes: "Private cut",
            createdAt: Date(timeIntervalSince1970: 200)
        )
        let snapshot = ConditionSnapshot(
            capturedAt: Date(timeIntervalSince1970: 300),
            latitude: 38.10,
            longitude: -121.55,
            placeSummary: "Rock Wall",
            timeWindowSummary: "6-9 AM",
            lightLevelSummary: "Morning light",
            temperatureC: 18,
            weatherSummary: "Clear",
            windSummary: "5 mph",
            cloudCoverSummary: "Low clouds",
            precipitationSummary: "Dry",
            captureStatus: .ready,
            source: .deviceLocation
        )
        let trip = Trip(
            waterbody: waterbody,
            spot: spot,
            conditionSnapshot: snapshot,
            targetSpecies: "Bass",
            notes: "Started on the point",
            startAt: Date(timeIntervalSince1970: 400)
        )
        trip.endAt = Date(timeIntervalSince1970: 500)
        trip.outcomeRawValue = TripOutcome.caught.rawValue

        let catchRecord = CatchRecord(
            species: "Bass",
            trip: trip,
            caughtAt: Date(timeIntervalSince1970: 450),
            lureOrBait: "Spinnerbait",
            method: "Casting",
            weightKg: 2.4,
            lengthCm: 48,
            note: "Windy edge"
        )

        let package = LogbookBackupExporter.makePackage(
            waterbodies: [waterbody],
            spots: [spot],
            conditionSnapshots: [snapshot],
            trips: [trip],
            catches: [catchRecord],
            exportedAt: Date(timeIntervalSince1970: 600),
            appMetadata: fixedMetadata
        )

        XCTAssertEqual(package.manifest.formatVersion, 1)
        XCTAssertEqual(package.manifest.counts.waterbodies, 1)
        XCTAssertEqual(package.manifest.counts.spots, 1)
        XCTAssertEqual(package.manifest.counts.conditionSnapshots, 1)
        XCTAssertEqual(package.manifest.counts.trips, 1)
        XCTAssertEqual(package.manifest.counts.catches, 1)
        XCTAssertEqual(package.manifest.counts.photos, 0)

        XCTAssertEqual(package.waterbodies.first?.id, waterbody.id)
        XCTAssertEqual(package.spots.first?.waterbodyId, waterbody.id)
        XCTAssertEqual(package.conditionSnapshots.first?.id, snapshot.id)
        XCTAssertEqual(package.trips.first?.waterbodyId, waterbody.id)
        XCTAssertEqual(package.trips.first?.spotId, spot.id)
        XCTAssertEqual(package.trips.first?.conditionSnapshotId, snapshot.id)
        XCTAssertEqual(package.trips.first?.endAt, trip.endAt)
        XCTAssertEqual(package.catches.first?.tripId, trip.id)
        XCTAssertNil(package.catches.first?.photoFilename)
    }

    func testMakeDocumentExcludesPersonalBestRecordsFromCanonicalExport() throws {
        let store = try ModelTestSupport.makeStore()
        let waterbody = Waterbody(name: "Lake", type: .lake)
        let trip = Trip(waterbody: waterbody)
        let catchRecord = CatchRecord(species: "Bass", trip: trip)
        let personalBest = PersonalBest(species: "Bass", longestLengthCm: 40, heaviestWeightKg: 2.0)

        store.context.insert(waterbody)
        store.context.insert(trip)
        store.context.insert(catchRecord)
        store.context.insert(personalBest)

        let document = try LogbookBackupExporter.makeDocument(
            context: store.context,
            exportedAt: Date(timeIntervalSince1970: 100),
            appMetadata: fixedMetadata
        )

        XCTAssertEqual(document.package.manifest.counts.waterbodies, 1)
        XCTAssertEqual(document.package.manifest.counts.trips, 1)
        XCTAssertEqual(document.package.manifest.counts.catches, 1)

        let fileWrapper = try document.package.makeFileWrapper()
        XCTAssertNil(fileWrapper.fileWrappers?["personal_bests.json"])
        XCTAssertNil(fileWrapper.fileWrappers?["data"]?.fileWrappers?["personal_bests.json"])
    }

    func testPhotoBackedCatchEmitsMediaFileAndFilename() throws {
        let trip = Trip(waterbody: nil)
        let catchRecord = CatchRecord(
            species: "Trout",
            trip: trip,
            photoData: Data([0x01, 0x02, 0x03]),
            photoContentType: "image/jpeg"
        )

        let package = LogbookBackupExporter.makePackage(
            waterbodies: [],
            spots: [],
            conditionSnapshots: [],
            trips: [trip],
            catches: [catchRecord],
            exportedAt: Date(timeIntervalSince1970: 100),
            appMetadata: fixedMetadata
        )

        XCTAssertEqual(package.manifest.counts.photos, 1)
        XCTAssertEqual(package.photos.count, 1)
        XCTAssertEqual(package.catches.first?.photoFilename, "\(catchRecord.id.uuidString.lowercased()).jpg")

        let fileWrapper = try package.makeFileWrapper()
        let exportedMedia = try unwrapFileWrapper(
            root: fileWrapper,
            path: ["media", "catches", "\(catchRecord.id.uuidString.lowercased()).jpg"]
        )

        XCTAssertEqual(exportedMedia.regularFileContents, Data([0x01, 0x02, 0x03]))
    }

    func testCatchWithoutPhotoEmitsNoMediaFiles() throws {
        let trip = Trip(waterbody: nil)
        let catchRecord = CatchRecord(species: "Perch", trip: trip)

        let package = LogbookBackupExporter.makePackage(
            waterbodies: [],
            spots: [],
            conditionSnapshots: [],
            trips: [trip],
            catches: [catchRecord],
            exportedAt: Date(timeIntervalSince1970: 100),
            appMetadata: fixedMetadata
        )

        XCTAssertEqual(package.manifest.counts.photos, 0)
        XCTAssertTrue(package.photos.isEmpty)
        XCTAssertNil(package.catches.first?.photoFilename)

        let fileWrapper = try package.makeFileWrapper()
        let catchMediaDirectory = try unwrapFileWrapper(root: fileWrapper, path: ["media", "catches"])
        XCTAssertTrue(catchMediaDirectory.fileWrappers?.isEmpty ?? false)
    }

    func testEmptyLogbookExportProducesValidZeroCountManifestAndDataFiles() throws {
        let store = try ModelTestSupport.makeStore()

        let document = try LogbookBackupExporter.makeDocument(
            context: store.context,
            exportedAt: Date(timeIntervalSince1970: 100),
            appMetadata: fixedMetadata
        )

        XCTAssertEqual(
            document.package.manifest.counts,
            LogbookBackupCounts(
                waterbodies: 0,
                spots: 0,
                conditionSnapshots: 0,
                trips: 0,
                catches: 0,
                photos: 0
            )
        )

        let fileWrapper = try document.package.makeFileWrapper()
        let manifestData = try XCTUnwrap(
            unwrapFileWrapper(root: fileWrapper, path: ["manifest.json"]).regularFileContents
        )
        let manifest = try makeJSONDecoder().decode(LogbookBackupManifest.self, from: manifestData)
        XCTAssertEqual(manifest.counts.photos, 0)

        XCTAssertNotNil(try unwrapFileWrapper(root: fileWrapper, path: ["data", "waterbodies.json"]))
        XCTAssertNotNil(try unwrapFileWrapper(root: fileWrapper, path: ["data", "spots.json"]))
        XCTAssertNotNil(try unwrapFileWrapper(root: fileWrapper, path: ["data", "condition_snapshots.json"]))
        XCTAssertNotNil(try unwrapFileWrapper(root: fileWrapper, path: ["data", "trips.json"]))
        XCTAssertNotNil(try unwrapFileWrapper(root: fileWrapper, path: ["data", "catches.json"]))
    }

    func testManifestIncludesAppMetadataAndEntityCounts() throws {
        let waterbody = Waterbody(name: "River", type: .river)
        let trip = Trip(waterbody: waterbody)

        let package = LogbookBackupExporter.makePackage(
            waterbodies: [waterbody],
            spots: [],
            conditionSnapshots: [],
            trips: [trip],
            catches: [],
            exportedAt: Date(timeIntervalSince1970: 321),
            appMetadata: fixedMetadata
        )

        let fileWrapper = try package.makeFileWrapper()
        let manifestData = try XCTUnwrap(
            unwrapFileWrapper(root: fileWrapper, path: ["manifest.json"]).regularFileContents
        )
        let manifest = try makeJSONDecoder().decode(LogbookBackupManifest.self, from: manifestData)

        XCTAssertEqual(manifest.formatVersion, 1)
        XCTAssertEqual(manifest.exportedAt, Date(timeIntervalSince1970: 321))
        XCTAssertEqual(manifest.appBundleIdentifier, fixedMetadata.appBundleIdentifier)
        XCTAssertEqual(manifest.appVersion, fixedMetadata.appVersion)
        XCTAssertEqual(manifest.buildNumber, fixedMetadata.buildNumber)
        XCTAssertEqual(manifest.counts.waterbodies, 1)
        XCTAssertEqual(manifest.counts.trips, 1)
        XCTAssertEqual(manifest.counts.catches, 0)
    }

    private var fixedMetadata: LogbookBackupAppMetadata {
        LogbookBackupAppMetadata(
            appBundleIdentifier: "io.aicompanyos.products.fishinglogbook",
            appVersion: "0.1.0",
            buildNumber: "1"
        )
    }

    private func unwrapFileWrapper(root: FileWrapper, path: [String]) throws -> FileWrapper {
        var current = root
        for component in path {
            current = try XCTUnwrap(current.fileWrappers?[component], "Missing file wrapper at \(component)")
        }
        return current
    }

    private func makeJSONDecoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}
