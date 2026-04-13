import CoreLocation
import Foundation

struct ConditionCapturePreview {
    let snapshot: ConditionSnapshot
    let isLocationReady: Bool
}

enum ConditionCaptureService {
    static func preview(
        waterbody: Waterbody?,
        spot: Spot?,
        location: CLLocation?
    ) -> ConditionCapturePreview {
        let snapshot = snapshot(
            waterbody: waterbody,
            spot: spot,
            location: location,
            capturedAt: .now
        )
        return ConditionCapturePreview(snapshot: snapshot, isLocationReady: location != nil)
    }

    /// Creates a condition snapshot with location data populated immediately.
    /// Weather fields remain nil until enriched via `enrichWithWeather(_:location:)`.
    static func snapshot(
        waterbody: Waterbody?,
        spot: Spot?,
        location: CLLocation?,
        capturedAt: Date
    ) -> ConditionSnapshot {
        let coordinate = bestAvailableCoordinate(location: location, spot: spot, waterbody: waterbody)
        let source = bestAvailableConditionSource(location: location, spot: spot, waterbody: waterbody)
        let isLocationReady = location != nil
        let placeSummary = [spot?.title, waterbody?.name]
            .compactMap { value -> String? in
                guard let value, !value.isEmpty else { return nil }
                return value
            }
            .joined(separator: " • ")

        let status: ConditionCaptureStatus
        if isLocationReady {
            status = .ready
        } else if coordinate != nil || !placeSummary.isEmpty {
            status = .fallback
        } else {
            status = .pending
        }

        return ConditionSnapshot(
            capturedAt: capturedAt,
            latitude: coordinate?.latitude,
            longitude: coordinate?.longitude,
            placeSummary: placeSummary.isEmpty ? nil : placeSummary,
            timeWindowSummary: timeWindowLabel(for: capturedAt),
            lightLevelSummary: lightLevelLabel(for: capturedAt),
            temperatureC: nil,
            weatherSummary: nil,
            windSummary: nil,
            cloudCoverSummary: nil,
            precipitationSummary: nil,
            captureStatus: status,
            source: source
        )
    }

    /// Enrich a snapshot with live weather data from WeatherKit.
    /// Safe to call on any iOS version — silently no-ops below iOS 16.
    /// Safe to call without network — returns the snapshot unchanged on failure.
    static func enrichWithWeather(
        _ snapshot: ConditionSnapshot,
        location: CLLocation?
    ) async {
        guard let location else { return }

        if #available(iOS 16.0, *) {
            guard let weather = await WeatherKitService.shared.fetchConditions(for: location) else {
                return
            }
            snapshot.temperatureC = weather.temperatureC
            snapshot.weatherSummary = weather.weatherSummary
            snapshot.windSummary = weather.windSummary
            snapshot.cloudCoverSummary = weather.cloudCoverSummary
            snapshot.precipitationSummary = weather.precipitationSummary
            snapshot.pressureHPa = weather.pressureHPa
        }
    }
}
