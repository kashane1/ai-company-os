import Foundation

/// One sample on the Future tab's trajectory chart. The chart plots
/// `years` against `week` (weeks-relative-to-now, negative for past,
/// zero for current, positive for future projection).
///
/// `Identifiable` + `Equatable` are SwiftUI Charts requirements —
/// without `Equatable`, the `.animation(.smooth, value: points)`
/// modifier silently no-ops on changes that differ only in metadata.
///
/// `confidence` (0...1) feeds the chart line/area opacity per the
/// sparse-data rendering rule (Phase 3 §Sparse-data rendering).
struct TrajectoryPoint: Identifiable, Equatable, Hashable {
    /// Stable per-week identity for chart diffing.
    let id: Int
    /// Weeks relative to "now." Negative = past, 0 = current,
    /// positive = projected forward.
    let week: Int
    /// Projected healthspan in years for the week.
    let years: Double
    /// 0...1 — chart line/area opacity scales with this.
    let confidence: Double

    init(week: Int, years: Double, confidence: Double = 1.0) {
        self.id = week
        self.week = week
        self.years = years
        self.confidence = max(0, min(1, confidence))
    }
}
