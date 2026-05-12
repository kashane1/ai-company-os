import Foundation

/// V1.7.0 — Future tab + History summary plan §Phase 4 telemetry.
///
/// Reuses the existing observability surface (the subscription-
/// conversion channel referenced in §Success metrics). The plan
/// explicitly defers a separate `LifeClockTelemetry` channel as its
/// own architectural surface — for v1 we just emit names and
/// dimension enum cases, never values.
///
/// Privacy stance (documented decision per plan §Phase 4):
///   * HealthKit values never traverse telemetry payloads.
///   * Dimension-enum events ARE behavioral telemetry; the boundary
///     is values-not-categories. Operator-acknowledged scope.
///
/// `LIFECLOCK_TELEMETRY_CAPTURE_PATH=/tmp/...json` enables an
/// in-memory ring buffer that's flushed to disk on demand for
/// UITest assertions. nil disables capture entirely.
final class TelemetryRecorder {
    enum Event {
        case futureTabViewed
        case futureSliderScrubbed(dimension: HealthspanEngine.Dimension)
        case futureProPaywallPresented
        case historySummaryViewed

        var name: String {
            switch self {
            case .futureTabViewed: return "future_tab_viewed"
            case .futureSliderScrubbed: return "future_slider_scrubbed"
            case .futureProPaywallPresented: return "future_pro_paywall_presented"
            case .historySummaryViewed: return "history_summary_viewed"
            }
        }

        var dimensionName: String? {
            if case let .futureSliderScrubbed(dim) = self {
                return dim.rawValue
            }
            return nil
        }
    }

    static let shared = TelemetryRecorder()

    private let lock = NSLock()
    private var buffer: [[String: String]] = []
    private var capturePath: String?
    private var captureEnabled: Bool = false

    private init() {
        let path = LifeClockLaunchConfiguration.current.telemetryCapturePath
        self.capturePath = path
        self.captureEnabled = path != nil
    }

    /// Emits an event. Always logs the event name; appends to the
    /// in-memory ring buffer when capture is enabled. Flushes
    /// synchronously to `capturePath` so UITests can read after a
    /// single tap (no debounce / no async write).
    func emit(_ event: Event) {
        // Real-world observability hook would call into the existing
        // analytics channel here. For v1 this is a no-op on the
        // production path — the architecture is documented in the
        // plan; concrete integration lands when a second consumer
        // demands the seam.
        guard captureEnabled else { return }
        var payload: [String: String] = [
            "name": event.name,
            "ts": ISO8601DateFormatter().string(from: Date()),
        ]
        if let dim = event.dimensionName {
            payload["dim"] = dim
        }
        lock.lock()
        buffer.append(payload)
        lock.unlock()
        flushToDisk()
    }

    /// Used by tests to inspect the captured events without going to disk.
    func capturedEvents() -> [[String: String]] {
        lock.lock()
        defer { lock.unlock() }
        return buffer
    }

    private func flushToDisk() {
        guard let path = capturePath else { return }
        lock.lock()
        let snapshot = buffer
        lock.unlock()
        guard let data = try? JSONSerialization.data(withJSONObject: snapshot, options: []) else {
            return
        }
        try? data.write(to: URL(fileURLWithPath: path), options: .atomic)
    }
}
