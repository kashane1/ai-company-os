import CoreLocation
import Foundation
import OSLog

private let logger = Logger(subsystem: "io.aicompanyos.products.fishinglogbook", category: "LocationRecorder")

final class LocationRecorder: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published var lastLocation: CLLocation?
    @Published var authorizationStatus: CLAuthorizationStatus

    private let manager: CLLocationManager
    private let authorizationOverride: CLAuthorizationStatus?

    init(authorizationOverride: CLAuthorizationStatus? = CatchbookLaunchConfiguration.locationAuthorizationOverride) {
        let manager = CLLocationManager()
        self.manager = manager
        self.authorizationOverride = authorizationOverride
        self.authorizationStatus = authorizationOverride ?? manager.authorizationStatus
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
    }

    func requestIfNeeded() {
        guard authorizationOverride == nil else { return }

        switch authorizationStatus {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedAlways, .authorizedWhenInUse:
            manager.requestLocation()
        default:
            break
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        guard authorizationOverride == nil else { return }

        authorizationStatus = manager.authorizationStatus
        if authorizationStatus == .authorizedAlways || authorizationStatus == .authorizedWhenInUse {
            manager.requestLocation()
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        lastLocation = locations.last
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        // Ignore transient location failures so the trip flow can remain offline-friendly.
        logger.error("Location capture failed: \(error.localizedDescription)")
    }
}
