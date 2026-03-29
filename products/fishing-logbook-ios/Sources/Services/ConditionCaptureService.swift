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

    static func snapshot(
        waterbody: Waterbody?,
        spot: Spot?,
        location: CLLocation?,
        capturedAt: Date
    ) -> ConditionSnapshot {
        let coordinate = bestAvailableCoordinate(location: location, spot: spot, waterbody: waterbody)
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
            source: isLocationReady ? .deviceLocation : .tripFallback
        )
    }
}
