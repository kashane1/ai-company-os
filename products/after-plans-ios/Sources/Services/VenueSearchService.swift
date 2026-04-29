import Foundation
import MapKit

// MARK: - Venue search
// Wraps `MKLocalSearchCompleter` for typeahead suggestions, with a
// follow-up `MKLocalSearch` request to resolve a chosen completion into
// a full venue (address, lat/lng, Apple Place ID).
//
// Why MKLocalSearchCompleter instead of MKLocalSearch.start() per
// keystroke: per WWDC23 guidance, completer is the typeahead-shaped
// surface — one MKLocalSearch fires per keystroke would burn the
// throttle quota fast. Completer streams suggestions as the user types
// and we resolve only on selection.
//
// Privacy posture: we never set `region` and never instantiate
// `CLLocationManager`, so the app does NOT need
// `NSLocationWhenInUseUsageDescription`.

struct VenueSuggestion: Identifiable, Hashable {
    let id: UUID
    let title: String
    let subtitle: String

    init(id: UUID = UUID(), title: String, subtitle: String) {
        self.id = id
        self.title = title
        self.subtitle = subtitle
    }
}

protocol VenueSearchServiceProtocol: AnyObject {
    /// Stream of suggestions for the most recent query. Drives the
    /// typeahead UI directly.
    var suggestionsStream: AsyncStream<[VenueSuggestion]> { get }
    /// Update the query. Debounce + cancellation handled internally.
    func updateQuery(_ query: String)
    /// Resolve a chosen suggestion to a fully-formed `Venue`. May return
    /// nil if MKLocalSearch returns no map items.
    func resolve(_ suggestion: VenueSuggestion) async throws -> Venue?
    /// Build a freeform venue from raw user input. Place ID stays nil;
    /// `is_freeform = true`, `verified = false`.
    func freeformVenue(named name: String) -> Venue
}

extension VenueSearchServiceProtocol {
    func freeformVenue(named name: String) -> Venue {
        Venue(
            id: UUID(),
            name: name,
            address: nil,
            latitude: nil,
            longitude: nil,
            applePlaceID: nil,
            isFreeform: true,
            verified: false
        )
    }
}

// MARK: - MKLocalSearch-backed implementation

@MainActor
final class MKVenueSearchService: NSObject, VenueSearchServiceProtocol {
    private let completer: MKLocalSearchCompleter
    private var continuation: AsyncStream<[VenueSuggestion]>.Continuation?
    private var debounceTask: Task<Void, Never>?
    private var resultCache: [String: [VenueSuggestion]] = [:]
    private let cacheLimit = 20
    private let debounceMillis: UInt64

    let suggestionsStream: AsyncStream<[VenueSuggestion]>

    init(debounceMillis: UInt64 = 300) {
        self.debounceMillis = debounceMillis
        self.completer = MKLocalSearchCompleter()
        var localContinuation: AsyncStream<[VenueSuggestion]>.Continuation?
        self.suggestionsStream = AsyncStream { localContinuation = $0 }
        self.continuation = localContinuation
        super.init()
        completer.resultTypes = [.pointOfInterest, .address]
        completer.delegate = self
    }

    func updateQuery(_ query: String) {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        debounceTask?.cancel()

        guard !trimmed.isEmpty else {
            completer.queryFragment = ""
            continuation?.yield([])
            return
        }

        if let cached = resultCache[trimmed] {
            continuation?.yield(cached)
            return
        }

        debounceTask = Task { [weak self, debounceMillis] in
            try? await Task.sleep(nanoseconds: debounceMillis * 1_000_000)
            guard !Task.isCancelled else { return }
            await self?.applyQuery(trimmed)
        }
    }

    private func applyQuery(_ query: String) {
        completer.queryFragment = query
    }

    func resolve(_ suggestion: VenueSuggestion) async throws -> Venue? {
        let request = MKLocalSearch.Request()
        request.naturalLanguageQuery = "\(suggestion.title) \(suggestion.subtitle)"
            .trimmingCharacters(in: .whitespaces)
        request.resultTypes = [.pointOfInterest, .address]
        let response = try await MKLocalSearch(request: request).start()
        guard let item = response.mapItems.first else { return nil }
        let placeID: String? = {
            if #available(iOS 18.0, *) { return item.identifier?.rawValue }
            return nil
        }()
        return Venue(
            id: UUID(),
            name: item.name ?? suggestion.title,
            address: formattedAddress(for: item.placemark),
            latitude: item.placemark.coordinate.latitude,
            longitude: item.placemark.coordinate.longitude,
            applePlaceID: placeID,
            isFreeform: placeID == nil,
            verified: placeID != nil
        )
    }

    private func formattedAddress(for placemark: MKPlacemark) -> String? {
        var parts: [String] = []
        if let n = placemark.subThoroughfare, let s = placemark.thoroughfare {
            parts.append("\(n) \(s)")
        } else if let s = placemark.thoroughfare {
            parts.append(s)
        }
        if let city = placemark.locality { parts.append(city) }
        if let region = placemark.administrativeArea { parts.append(region) }
        return parts.isEmpty ? nil : parts.joined(separator: ", ")
    }

    private func cache(_ key: String, _ value: [VenueSuggestion]) {
        if resultCache.count >= cacheLimit, let firstKey = resultCache.keys.first {
            resultCache.removeValue(forKey: firstKey)
        }
        resultCache[key] = value
    }
}

extension MKVenueSearchService: MKLocalSearchCompleterDelegate {
    nonisolated func completerDidUpdateResults(_ completer: MKLocalSearchCompleter) {
        let results = completer.results.map { VenueSuggestion(title: $0.title, subtitle: $0.subtitle) }
        let query = completer.queryFragment
        Task { @MainActor [weak self] in
            self?.cache(query, results)
            self?.continuation?.yield(results)
        }
    }

    nonisolated func completer(_ completer: MKLocalSearchCompleter, didFailWithError error: Error) {
        // Throttle errors (MKError code 3) are a soft failure — the
        // cache or empty list is the right fallback. Any other failure
        // also surfaces as empty rather than crashing the typeahead.
        Task { @MainActor [weak self] in
            self?.continuation?.yield([])
        }
    }
}

// MARK: - In-memory stub for previews + tests

final class StubVenueSearchService: VenueSearchServiceProtocol, @unchecked Sendable {
    var suggestionsStream: AsyncStream<[VenueSuggestion]> { stream }
    private let stream: AsyncStream<[VenueSuggestion]>
    private let continuation: AsyncStream<[VenueSuggestion]>.Continuation
    var stubbedSuggestions: [String: [VenueSuggestion]] = [:]
    var stubbedVenues: [VenueSuggestion: Venue] = [:]
    private(set) var queriesReceived: [String] = []

    init() {
        var localContinuation: AsyncStream<[VenueSuggestion]>.Continuation!
        self.stream = AsyncStream { localContinuation = $0 }
        self.continuation = localContinuation
    }

    func updateQuery(_ query: String) {
        queriesReceived.append(query)
        let suggestions = stubbedSuggestions[query] ?? []
        continuation.yield(suggestions)
    }

    func resolve(_ suggestion: VenueSuggestion) async throws -> Venue? {
        stubbedVenues[suggestion]
    }
}
