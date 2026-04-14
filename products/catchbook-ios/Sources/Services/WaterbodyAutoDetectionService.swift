import CoreLocation
import Foundation
import MapKit
import SwiftData

/// Auto-detects a nearby waterbody from a coordinate using CLGeocoder's
/// inlandWater/ocean hints, falling back to a single combined MKLocalSearch.
///
/// The service is split into a **pure** detection step (`detect(at:)`) and an
/// **impure** persistence step (`findOrCreate(_:in:)`) so callers can defer the
/// SwiftData write until their own save path fires. This lets forms like
/// NewSpotForm hold a `Detected` value as pending state and only insert a
/// `Waterbody` row inside their `save()` transaction — dismissing the form
/// without saving leaves zero phantom records.
///
/// `detect(at:)` is silent on failure: any network or throttling error returns
/// `nil` and the caller falls through to the "no waterbody" path. A 6-second
/// timeout guards against CLGeocoder/MKLocalSearch hangs on flaky networks.
enum WaterbodyAutoDetectionService {
    struct Detected: Equatable {
        let name: String
        let type: WaterbodyType
        let coordinate: CLLocationCoordinate2D

        static func == (lhs: Detected, rhs: Detected) -> Bool {
            lhs.name == rhs.name
                && lhs.type == rhs.type
                && lhs.coordinate.latitude == rhs.coordinate.latitude
                && lhs.coordinate.longitude == rhs.coordinate.longitude
        }
    }

    /// Timeout for the whole detection chain. Late results past this deadline
    /// are discarded so the user doesn't get a surprise prefill after they've
    /// already moved on.
    static let detectionTimeout: Duration = .seconds(6)

    /// Pure. Runs CLGeocoder reverse geocode for inlandWater/ocean, then one
    /// combined MKLocalSearch for "lake river reservoir" as fallback. Returns
    /// `nil` on failure, no results, timeout, or cancellation. Does NOT touch
    /// SwiftData.
    static func detect(at coordinate: CLLocationCoordinate2D) async -> Detected? {
        await withTaskGroup(of: Detected?.self) { group in
            group.addTask {
                await runDetection(at: coordinate)
            }
            group.addTask {
                try? await Task.sleep(for: detectionTimeout)
                return nil
            }

            defer { group.cancelAll() }
            for await result in group {
                if let result {
                    return result
                }
            }
            return nil
        }
    }

    /// Impure. Finds an existing `Waterbody` by case-insensitive name match via
    /// a `FetchDescriptor`, or inserts a new one. Does NOT call
    /// `context.save()` — the caller is responsible for committing inside its
    /// own write coordinator so detection never leaves orphaned rows when a
    /// form is dismissed mid-flow.
    ///
    /// The case-insensitive name predicate is also the dedupe mechanism for
    /// the unlikely race where two callers detect the same waterbody
    /// concurrently; it must stay case-insensitive.
    @MainActor
    static func findOrCreate(
        _ detected: Detected,
        in context: ModelContext
    ) throws -> Waterbody {
        // Fetch all and match in Swift. SwiftData's #Predicate macro has strict
        // limits on string APIs (localizedLowercase is not supported), and the
        // waterbody list is typically small (0–50 rows), so a full fetch is
        // cheaper than fighting the macro.
        let loweredName = detected.name.lowercased()
        let allWaterbodies = try context.fetch(FetchDescriptor<Waterbody>())
        if let existing = allWaterbodies.first(where: { $0.name.lowercased() == loweredName }) {
            return existing
        }

        let waterbody = Waterbody(
            name: detected.name,
            type: detected.type,
            latitude: detected.coordinate.latitude,
            longitude: detected.coordinate.longitude
        )
        context.insert(waterbody)
        return waterbody
    }

    /// Pure helper exposed for tests. Infers a likely `WaterbodyType` from a
    /// detected place name.
    static func inferType(from name: String) -> WaterbodyType {
        let lower = name.lowercased()
        if lower.contains("river") || lower.contains("creek") || lower.contains("stream") {
            return .river
        }
        if lower.contains("pond") {
            return .pond
        }
        if lower.contains("ocean") || lower.contains("sea") || lower.contains("gulf") || lower.contains("bay") {
            return .coastal
        }
        return .lake
    }

    // MARK: - Private

    private static func runDetection(at coordinate: CLLocationCoordinate2D) async -> Detected? {
        // Layer 1: CLGeocoder reverse geocode for named inland water or ocean.
        let geocoder = CLGeocoder()
        let location = CLLocation(latitude: coordinate.latitude, longitude: coordinate.longitude)
        if let placemarks = try? await geocoder.reverseGeocodeLocation(location),
           let placemark = placemarks.first {
            if let waterName = placemark.inlandWater {
                return Detected(
                    name: waterName,
                    type: inferType(from: waterName),
                    coordinate: coordinate
                )
            }
            if let oceanName = placemark.ocean {
                return Detected(
                    name: oceanName,
                    type: inferType(from: oceanName),
                    coordinate: coordinate
                )
            }
        }

        // Layer 2: Single combined MKLocalSearch for nearby water features.
        // One request instead of three sequential (lake → river → reservoir)
        // to respect Apple Maps rate limits and cut worst-case latency.
        let request = MKLocalSearch.Request()
        request.naturalLanguageQuery = "lake river reservoir"
        request.region = MKCoordinateRegion(
            center: coordinate,
            latitudinalMeters: 2_000,
            longitudinalMeters: 2_000
        )
        if let response = try? await MKLocalSearch(request: request).start(),
           let nearest = response.mapItems.first,
           let name = nearest.name {
            return Detected(
                name: name,
                type: inferType(from: name),
                coordinate: coordinate
            )
        }

        return nil
    }
}
