import CoreLocation
import Foundation
import ImageIO

struct PhotoCaptureMetadata {
    let coordinate: CLLocationCoordinate2D?
    let capturedAt: Date?
    let source: String
}

struct PhotoSpotMatch: Identifiable, Equatable {
    let spotID: UUID
    let title: String
    let distanceMeters: CLLocationDistance

    var id: UUID { spotID }

    var distanceText: String {
        let rounded = Int(distanceMeters.rounded())
        return rounded <= 0 ? "Here" : "\(rounded)m away"
    }
}

struct CatchPhotoLocationSuggestion {
    let coordinate: CLLocationCoordinate2D
    let matches: [PhotoSpotMatch]
}

enum CatchPhotoMetadataService {
    static let defaultSpotMatchRadiusMeters: CLLocationDistance = 120

    static func metadata(from imageData: Data, source: String = "embedded-photo") -> PhotoCaptureMetadata? {
        guard let imageSource = CGImageSourceCreateWithData(imageData as CFData, nil),
              let properties = CGImageSourceCopyPropertiesAtIndex(imageSource, 0, nil) as? [CFString: Any] else {
            return nil
        }

        return metadata(from: properties, source: source)
    }

    static func metadata(from properties: [CFString: Any], source: String = "embedded-photo") -> PhotoCaptureMetadata? {
        let coordinate = coordinate(from: properties)
        let capturedAt = capturedAt(from: properties)

        guard coordinate != nil || capturedAt != nil else { return nil }
        return PhotoCaptureMetadata(coordinate: coordinate, capturedAt: capturedAt, source: source)
    }

    static func coordinate(from properties: [CFString: Any]) -> CLLocationCoordinate2D? {
        guard let gps = properties[kCGImagePropertyGPSDictionary] as? [CFString: Any],
              let latitude = gps[kCGImagePropertyGPSLatitude] as? CLLocationDegrees,
              let longitude = gps[kCGImagePropertyGPSLongitude] as? CLLocationDegrees else {
            return nil
        }

        let latitudeRef = (gps[kCGImagePropertyGPSLatitudeRef] as? String)?.uppercased()
        let longitudeRef = (gps[kCGImagePropertyGPSLongitudeRef] as? String)?.uppercased()

        let signedLatitude = latitudeRef == "S" ? -latitude : latitude
        let signedLongitude = longitudeRef == "W" ? -longitude : longitude
        return CLLocationCoordinate2D(latitude: signedLatitude, longitude: signedLongitude)
    }

    static func capturedAt(from properties: [CFString: Any]) -> Date? {
        let exifDate = (properties[kCGImagePropertyExifDictionary] as? [CFString: Any])?[kCGImagePropertyExifDateTimeOriginal] as? String
        let tiffDate = (properties[kCGImagePropertyTIFFDictionary] as? [CFString: Any])?[kCGImagePropertyTIFFDateTime] as? String

        return parse(dateString: exifDate) ?? parse(dateString: tiffDate)
    }

    static func nearbySpotMatches(
        for coordinate: CLLocationCoordinate2D,
        spots: [Spot],
        radiusMeters: CLLocationDistance = defaultSpotMatchRadiusMeters
    ) -> [PhotoSpotMatch] {
        let captureLocation = CLLocation(latitude: coordinate.latitude, longitude: coordinate.longitude)

        return spots.compactMap { spot in
            guard let latitude = spot.latitude, let longitude = spot.longitude else { return nil }
            let distance = captureLocation.distance(from: CLLocation(latitude: latitude, longitude: longitude))
            guard distance <= radiusMeters else { return nil }
            return PhotoSpotMatch(spotID: spot.id, title: spot.title, distanceMeters: distance)
        }
        .sorted { lhs, rhs in
            if lhs.distanceMeters != rhs.distanceMeters {
                return lhs.distanceMeters < rhs.distanceMeters
            }
            return lhs.title.localizedCaseInsensitiveCompare(rhs.title) == .orderedAscending
        }
    }

    private static func parse(dateString: String?) -> Date? {
        guard let dateString, !dateString.isEmpty else { return nil }

        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy:MM:dd HH:mm:ss"
        return formatter.date(from: dateString)
    }
}
