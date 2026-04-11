import CoreLocation
import Foundation
import WeatherKit

/// Current weather conditions for a fishing location.
/// Maps directly to ConditionSnapshot weather fields.
struct WeatherConditions: Sendable {
    let temperatureC: Double
    let weatherSummary: String
    let windSummary: String
    let cloudCoverSummary: String
    let precipitationSummary: String
}

/// Thread-safe service for fetching weather data from Apple WeatherKit.
///
/// Includes a 30-second cache so rapid calls (e.g. trip start preview refresh)
/// do not hit the API repeatedly. Returns nil gracefully on any error —
/// weather is always optional in the logging flow.
@available(iOS 16.0, *)
actor WeatherKitService {
    static let shared = WeatherKitService()

    private struct CacheEntry {
        let conditions: WeatherConditions
        let timestamp: Date
    }

    private static let cacheDuration: TimeInterval = 30
    private var cache: [String: CacheEntry] = [:]
    private var cachedAttribution: WeatherAttribution?

    private init() {}

    // MARK: - Attribution

    /// Fetch Apple WeatherKit legal attribution (logo, legal page, service name).
    /// Cached for the actor lifetime since the attribution URLs are static.
    /// Returns nil if the fetch fails — callers should show a minimal fallback.
    func attribution() async -> WeatherAttribution? {
        if let cachedAttribution {
            return cachedAttribution
        }
        do {
            let attribution = try await WeatherService.shared.attribution
            cachedAttribution = attribution
            return attribution
        } catch {
            return nil
        }
    }

    // MARK: - Public

    /// Fetch current weather for a location. Returns nil if WeatherKit
    /// is unavailable, network is down, or any other error occurs.
    func fetchConditions(for location: CLLocation) async -> WeatherConditions? {
        let key = cacheKey(for: location)

        if let cached = cache[key],
           Date().timeIntervalSince(cached.timestamp) < Self.cacheDuration {
            return cached.conditions
        }

        guard let conditions = await fetchFromService(for: location) else {
            return nil
        }

        cache[key] = CacheEntry(conditions: conditions, timestamp: Date())
        return conditions
    }

    // MARK: - Private

    private func fetchFromService(for location: CLLocation) async -> WeatherConditions? {
        do {
            let weather = try await WeatherService.shared.weather(for: location)
            let current = weather.currentWeather

            let temperatureC = current.temperature.converted(to: .celsius).value

            let weatherSummary = current.condition.description

            let speedKnots = current.wind.speed.converted(to: .knots).value
            let cardinal = degreesToCardinal(
                current.wind.direction.converted(to: .degrees).value
            )
            let windSummary = String(format: "%.0f kt %@", speedKnots, cardinal)

            let cloudPct = current.cloudCover // 0.0 – 1.0
            let cloudCoverSummary = cloudCoverLabel(cloudPct)

            let precipitationSummary: String
            switch current.precipitationIntensity.converted(to: .millimetersPerHour).value {
            case let rate where rate > 7.5:
                precipitationSummary = "Heavy rain"
            case let rate where rate > 2.5:
                precipitationSummary = "Moderate rain"
            case let rate where rate > 0.1:
                precipitationSummary = "Light rain"
            default:
                precipitationSummary = "Dry"
            }

            return WeatherConditions(
                temperatureC: temperatureC,
                weatherSummary: weatherSummary,
                windSummary: windSummary,
                cloudCoverSummary: cloudCoverSummary,
                precipitationSummary: precipitationSummary
            )
        } catch {
            // Network down, service unavailable, entitlement missing, etc.
            return nil
        }
    }

    private func cloudCoverLabel(_ fraction: Double) -> String {
        switch fraction {
        case ..<0.20: return "Clear skies"
        case ..<0.50: return "Partly cloudy"
        case ..<0.80: return "Mostly cloudy"
        default:       return "Overcast"
        }
    }

    private func degreesToCardinal(_ degrees: Double) -> String {
        let directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
        ]
        let index = Int((degrees + 11.25).truncatingRemainder(dividingBy: 360) / 22.5)
        return directions[min(max(index, 0), 15)]
    }

    private func cacheKey(for location: CLLocation) -> String {
        // Two decimal places ≈ 1.1 km precision, enough to avoid cache misses
        // while the angler stays in the same area.
        String(format: "%.2f,%.2f", location.coordinate.latitude, location.coordinate.longitude)
    }
}
