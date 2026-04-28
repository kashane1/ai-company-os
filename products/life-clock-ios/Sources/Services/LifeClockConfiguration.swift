import Foundation

/// Runtime configuration knobs. Plain struct — no env-var driven backend
/// switching in v1 (no backend exists).
struct LifeClockConfiguration {
    static let appName = "Life Clock"
    static let bundleId = "io.aicompanyos.products.lifeclock"
    static let medicalDisclaimer =
        "Life Clock provides wellness and habit insights for informational purposes only. " +
        "It is not medical advice, diagnosis, treatment, or a forecast of lifespan. Talk to a " +
        "qualified clinician for medical decisions."
}
