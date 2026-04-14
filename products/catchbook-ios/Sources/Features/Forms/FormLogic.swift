import CoreLocation
import Foundation

struct SpotFormDraft {
    let title: String
    let notes: String
    let latitude: Double?
    let longitude: Double?
}

struct WaterbodyFormDraft {
    let name: String
    let type: WaterbodyType
    let latitude: Double?
    let longitude: Double?
}

enum SpotFormLogic {
    static func canSave(title: String) -> Bool {
        !TripEditingLogic.normalizedText(title).isEmpty
    }

    static func draft(
        title: String,
        notes: String,
        coordinate: CLLocationCoordinate2D?
    ) -> SpotFormDraft {
        SpotFormDraft(
            title: TripEditingLogic.normalizedText(title),
            notes: TripEditingLogic.normalizedText(notes),
            latitude: coordinate?.latitude,
            longitude: coordinate?.longitude
        )
    }
}

enum WaterbodyFormLogic {
    static func canSave(name: String) -> Bool {
        !TripEditingLogic.normalizedText(name).isEmpty
    }

    static func normalizedName(_ name: String) -> String {
        TripEditingLogic.normalizedText(name)
    }

    static func draft(
        name: String,
        type: WaterbodyType,
        coordinate: CLLocationCoordinate2D?
    ) -> WaterbodyFormDraft {
        WaterbodyFormDraft(
            name: normalizedName(name),
            type: type,
            latitude: coordinate?.latitude,
            longitude: coordinate?.longitude
        )
    }
}
