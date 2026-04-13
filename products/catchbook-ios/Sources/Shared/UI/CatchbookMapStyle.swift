import MapKit
import SwiftUI

enum CatchbookMapStyle: String, CaseIterable, Identifiable {
    static let appStorageKey = "catchbook.map-style"

    case standard
    case hybrid
    case satellite

    var id: String { rawValue }

    var iconName: String {
        switch self {
        case .standard:
            return "map"
        case .hybrid:
            return "square.3.layers.3d"
        case .satellite:
            return "globe.americas.fill"
        }
    }

    var accessibilityLabel: String {
        switch self {
        case .standard:
            return "Switch map style from standard to hybrid"
        case .hybrid:
            return "Switch map style from hybrid to satellite"
        case .satellite:
            return "Switch map style from satellite to standard"
        }
    }

    var next: CatchbookMapStyle {
        switch self {
        case .standard:
            return .hybrid
        case .hybrid:
            return .satellite
        case .satellite:
            return .standard
        }
    }

    @available(iOS 17.0, *)
    var mapStyle: MapStyle {
        switch self {
        case .standard:
            return .standard(elevation: .realistic)
        case .hybrid:
            return .hybrid(elevation: .realistic)
        case .satellite:
            return .imagery(elevation: .realistic)
        }
    }
}
