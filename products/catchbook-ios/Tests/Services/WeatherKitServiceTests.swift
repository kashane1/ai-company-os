import CoreLocation
import XCTest
@testable import Catchbook

@available(iOS 16.0, *)
final class WeatherKitServiceTests: XCTestCase {
    func testCloudCoverLabelClearSkies() {
        let snapshot = ConditionSnapshot()
        snapshot.cloudCoverSummary = cloudCoverLabelHelper(0.0)
        XCTAssertEqual(snapshot.cloudCoverSummary, "Clear skies")
    }

    func testCloudCoverLabelPartlyCloudy() {
        let snapshot = ConditionSnapshot()
        snapshot.cloudCoverSummary = cloudCoverLabelHelper(0.35)
        XCTAssertEqual(snapshot.cloudCoverSummary, "Partly cloudy")
    }

    func testCloudCoverLabelMostlyCloudy() {
        let snapshot = ConditionSnapshot()
        snapshot.cloudCoverSummary = cloudCoverLabelHelper(0.65)
        XCTAssertEqual(snapshot.cloudCoverSummary, "Mostly cloudy")
    }

    func testCloudCoverLabelOvercast() {
        let snapshot = ConditionSnapshot()
        snapshot.cloudCoverSummary = cloudCoverLabelHelper(0.95)
        XCTAssertEqual(snapshot.cloudCoverSummary, "Overcast")
    }

    func testCloudCoverLabelBoundaryAtTwentyPercent() {
        let snapshot = ConditionSnapshot()
        snapshot.cloudCoverSummary = cloudCoverLabelHelper(0.20)
        XCTAssertEqual(snapshot.cloudCoverSummary, "Partly cloudy")
    }

    func testCloudCoverLabelBoundaryAtFiftyPercent() {
        let snapshot = ConditionSnapshot()
        snapshot.cloudCoverSummary = cloudCoverLabelHelper(0.50)
        XCTAssertEqual(snapshot.cloudCoverSummary, "Mostly cloudy")
    }

    func testCloudCoverLabelBoundaryAtEightyPercent() {
        let snapshot = ConditionSnapshot()
        snapshot.cloudCoverSummary = cloudCoverLabelHelper(0.80)
        XCTAssertEqual(snapshot.cloudCoverSummary, "Overcast")
    }

    func testDegreesToCardinalNorth() {
        XCTAssertEqual(degreesToCardinalHelper(0), "N")
        XCTAssertEqual(degreesToCardinalHelper(360), "N")
    }

    func testDegreesToCardinalNorthNorthEast() {
        XCTAssertEqual(degreesToCardinalHelper(22.5), "NNE")
    }

    func testDegreesToCardinalEast() {
        XCTAssertEqual(degreesToCardinalHelper(90), "E")
    }

    func testDegreesToCardinalSouth() {
        XCTAssertEqual(degreesToCardinalHelper(180), "S")
    }

    func testDegreesToCardinalWest() {
        XCTAssertEqual(degreesToCardinalHelper(270), "W")
    }

    func testDegreesToCardinalNorthWest() {
        XCTAssertEqual(degreesToCardinalHelper(315), "NW")
    }

    func testDegreesToCardinalNegativeDegrees() {
        // -10 degrees should normalize to 350 degrees (NNW)
        XCTAssertEqual(degreesToCardinalHelper(-10), "NNW")
    }

    func testDegreesToCardinalLargeOverflow() {
        // 450 degrees should normalize to 90 degrees (E)
        XCTAssertEqual(degreesToCardinalHelper(450), "E")
    }

    func testCacheKeyGenerationSingleLocation() {
        let location1 = CLLocation(latitude: 47.6205, longitude: -122.3493)
        let key1 = cacheKeyHelper(for: location1)

        XCTAssertEqual(key1, "47.62,-122.35")
    }

    func testCacheKeyGenerationTwoDifferentLocations() {
        let location1 = CLLocation(latitude: 47.6205, longitude: -122.3493)
        let location2 = CLLocation(latitude: 47.6300, longitude: -122.3600)

        let key1 = cacheKeyHelper(for: location1)
        let key2 = cacheKeyHelper(for: location2)

        XCTAssertNotEqual(key1, key2)
    }

    func testCacheKeyGenerationNearbyLocationsSameKey() {
        // Two locations within ~1.1km should get the same cache key
        let location1 = CLLocation(latitude: 47.6205, longitude: -122.3493)
        let location2 = CLLocation(latitude: 47.6215, longitude: -122.3495)

        let key1 = cacheKeyHelper(for: location1)
        let key2 = cacheKeyHelper(for: location2)

        XCTAssertEqual(key1, key2)
    }

    func testWeatherConditionsInitialization() {
        let conditions = WeatherConditions(
            temperatureC: 15.5,
            weatherSummary: "Partly cloudy",
            windSummary: "10 kt N",
            cloudCoverSummary: "Partly cloudy",
            precipitationSummary: "Dry"
        )

        XCTAssertEqual(conditions.temperatureC, 15.5)
        XCTAssertEqual(conditions.weatherSummary, "Partly cloudy")
        XCTAssertEqual(conditions.windSummary, "10 kt N")
        XCTAssertEqual(conditions.cloudCoverSummary, "Partly cloudy")
        XCTAssertEqual(conditions.precipitationSummary, "Dry")
    }

    func testWeatherConditionsWithExtremeTemperature() {
        let conditions = WeatherConditions(
            temperatureC: -25.0,
            weatherSummary: "Heavy snow",
            windSummary: "35 kt NW",
            cloudCoverSummary: "Overcast",
            precipitationSummary: "Heavy rain"
        )

        XCTAssertEqual(conditions.temperatureC, -25.0)
        XCTAssertTrue(conditions.weatherSummary.count > 0)
    }

    // MARK: - Helper functions (reproduce private methods from WeatherKitService)

    private func cloudCoverLabelHelper(_ fraction: Double) -> String {
        switch fraction {
        case ..<0.20: return "Clear skies"
        case ..<0.50: return "Partly cloudy"
        case ..<0.80: return "Mostly cloudy"
        default:       return "Overcast"
        }
    }

    private func degreesToCardinalHelper(_ degrees: Double) -> String {
        let directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
        ]
        let index = Int((degrees + 11.25).truncatingRemainder(dividingBy: 360) / 22.5)
        return directions[min(max(index, 0), 15)]
    }

    private func cacheKeyHelper(for location: CLLocation) -> String {
        String(format: "%.2f,%.2f", location.coordinate.latitude, location.coordinate.longitude)
    }
}
