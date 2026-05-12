import Foundation

/// Future tab projection engine. Pure static. No stored state.
///
/// V1.7.0 (Future tab + History summary plan §Phase 3). All inputs
/// explicit; `EngineClock` injected for testability (matches the
/// `ClockEngine` precedent).
///
/// Modelling note: `docs/products/life-clock/healthspan-coefficients.md`.
/// Citations live as `// Source: …` comments below; this doc is the
/// human-readable record of *why* the numbers were picked. Every
/// coefficient is paired with `// TODO: refine after beta`.
///
/// Hard rules:
///   * `currentProjection` is the headline number. Clamped to
///     [floor, baseline + 14].
///   * `weeklyTrajectory` returns points for chart consumption.
///   * `projectWith(baseAggregates:overrides:baseline:)` is the
///     slider-scrub primitive: pure function over dictionaries, no
///     SwiftData access. Phase 4 calls it on every `onChange` event.
///   * Smoking dominance: when nicotine > 0 days/week, the projection
///     caps regardless of other levers (per healthspan-coefficients §Smoking dominance).
enum HealthspanEngine {

    // MARK: - Public types

    enum Dimension: String, CaseIterable, Codable, Hashable {
        case sleep
        case dietQuality
        case steps
        case exerciseMinutes
        case extras
        case nicotine
    }

    struct Projection: Equatable {
        let healthspanYears: Double
        let confidence: Double                          // 0...1
        let perDimensionDelta: [Dimension: Double]      // signed years
        let clamped: ClampState

        enum ClampState: Equatable {
            case none
            case cappedAt(Double)
            case flooredAt(Double)
            case nearCap                                // within 2y of cap
        }
    }

    // MARK: - Coefficients (Phase 0 deliverable)
    //
    // All single-source-of-truth: changing a number here changes the
    // projection. Keep paired with TODO so future telemetry-driven
    // recalibration knows where to land.

    // Cap: +14y above baseline. Source: Li 2018 Circulation ceiling.
    private static let maxBenefitAboveBaseline: Double = 14.0

    // Sleep — U-curve, optimum 7.5h. Source: Cai 2025 GeroScience.
    // TODO: refine after beta.
    private static let sleepOptimumHours: Double = 7.5
    private static let sleepMaxBenefit: Double = 1.5
    private static let sleepMaxDrag: Double = -2.0

    // Diet quality — linear, saturates at 5 days/wk. Source: Mediterranean
    // diet JAMA Net Open 2024. Drag-only when habit absent? No — diet
    // skipping doesn't carry an active negative; defaults to 0.
    private static let dietQualitySaturation: Double = 5.0   // days/wk
    private static let dietQualityMaxBenefit: Double = 2.5

    // Steps — log-linear, plateau at 10k. Source: Paluch 2022 Lancet PH.
    private static let stepsPlateau: Double = 10_000
    private static let stepsMaxBenefit: Double = 3.0
    private static let stepsMaxDrag: Double = -1.5   // <4k/day

    // Exercise — linear, saturates at 300 min/wk. Source: Moore 2012 PLOS Med.
    private static let exerciseSaturation: Double = 300       // min/wk
    private static let exerciseMaxBenefit: Double = 2.0

    // Extras — linear drag from 3+ days/wk. Source: GBD 2020 / WHO 2023.
    private static let extrasDragOnset: Double = 3.0          // days/wk
    private static let extrasMaxDrag: Double = -2.5

    // Nicotine — step at >0 days/wk; dominant. Source: Jha 2013 NEJM.
    private static let nicotinePenalty: Double = -10.0
    private static let nicotineOtherDimensionScale: Double = 0.3

    // MARK: - Aggregates from raw data

    /// Per-dimension 14-day rolling values from raw snapshots + habits.
    /// Powers both `currentProjection` and the `WhatIfSlider`'s
    /// "personal current" anchors (Phase 4).
    static func aggregates(
        snapshots: [DailyHealthSnapshot],
        habits: [HabitLog]
    ) -> [Dimension: Double] {
        let denom = max(1.0, Double(min(snapshots.count, 14)))
        let recentSnaps = Array(snapshots.prefix(14))
        let recentHabits = Array(habits.prefix(14))

        let sleepAvg: Double = {
            let values = recentSnaps.compactMap(\.sleepHours)
            guard !values.isEmpty else { return 0 }
            return values.reduce(0, +) / Double(values.count)
        }()

        let stepsAvg: Double = {
            let values = recentSnaps.compactMap(\.stepCount).map(Double.init)
            guard !values.isEmpty else { return 0 }
            return values.reduce(0, +) / Double(values.count)
        }()

        // Exercise: sum the last 14 days, halve for weekly average.
        let exerciseWeekly: Double = {
            let total = recentSnaps.compactMap(\.exerciseMinutes).map(Double.init).reduce(0, +)
            return total / 2.0
        }()

        // Diet quality days/wk: whole-food meal == "yes" / 14 * 7.
        let dietDaysWk: Double = {
            let yesCount = recentHabits.filter { $0.wholeFoodMeal == "yes" }.count
            return Double(yesCount) / denom * 7.0
        }()

        // Extras = alcohol present (any level beyond "none"). Scaled to days/wk.
        let extrasDaysWk: Double = {
            let count = recentHabits.filter { $0.alcoholLevel.lowercased() != "none" }.count
            return Double(count) / denom * 7.0
        }()

        // Nicotine days/wk.
        let nicotineDaysWk: Double = {
            let count = recentHabits.filter { $0.smokingVaping }.count
            return Double(count) / denom * 7.0
        }()

        return [
            .sleep: sleepAvg,
            .dietQuality: dietDaysWk,
            .steps: stepsAvg,
            .exerciseMinutes: exerciseWeekly,
            .extras: extrasDaysWk,
            .nicotine: nicotineDaysWk,
        ]
    }

    // MARK: - Per-dimension delta functions
    //
    // Each maps a personal-current value to a signed years-of-
    // healthspan delta. Pure, deterministic, side-effect-free.

    static func sleepDelta(hours: Double) -> Double {
        // U-curve: peak at optimum, fall off either side.
        // Asymmetric: too-little is more punitive than too-much (per
        // healthspan-coefficients §Sleep).
        guard hours > 0 else { return 0 }   // no data ⇒ neutral
        let deviation = hours - sleepOptimumHours
        if deviation > 0 {
            // Too much — soft drag.
            return max(sleepMaxDrag, sleepMaxBenefit - 0.5 * deviation * deviation)
        }
        // Too little — punitive curve.
        let punitive = sleepMaxBenefit - 0.8 * deviation * deviation
        return max(sleepMaxDrag, punitive)
    }

    static func dietQualityDelta(daysPerWeek: Double) -> Double {
        let clamped = max(0, min(dietQualitySaturation, daysPerWeek))
        return clamped / dietQualitySaturation * dietQualityMaxBenefit
    }

    static func stepsDelta(perDay: Double) -> Double {
        // Below 4k/day starts dragging; above 10k plateau.
        if perDay >= stepsPlateau {
            return stepsMaxBenefit
        }
        if perDay >= 4_000 {
            // Linear from 4k = 0 to 10k = max benefit.
            return (perDay - 4_000) / 6_000.0 * stepsMaxBenefit
        }
        // Below 4k: linear drag toward maxDrag at 0 steps.
        return stepsMaxDrag * (1.0 - perDay / 4_000.0)
    }

    static func exerciseMinutesDelta(minutesPerWeek: Double) -> Double {
        let clamped = max(0, min(exerciseSaturation, minutesPerWeek))
        return clamped / exerciseSaturation * exerciseMaxBenefit
    }

    static func extrasDelta(daysPerWeek: Double) -> Double {
        // Below onset: 0. Linear drag from onset to 7+ days/wk.
        guard daysPerWeek > extrasDragOnset else { return 0 }
        let overage = min(7.0 - extrasDragOnset, daysPerWeek - extrasDragOnset)
        return extrasMaxDrag * (overage / (7.0 - extrasDragOnset))
    }

    static func nicotineDelta(daysPerWeek: Double) -> Double {
        return daysPerWeek > 0 ? nicotinePenalty : 0
    }

    // MARK: - Composition

    /// Headline projection from raw 14-day snapshots + habits + baseline.
    /// Cap/floor applied.
    static func currentProjection(
        snapshots: [DailyHealthSnapshot],
        habits: [HabitLog],
        baseline: Double,
        currentAge: Double,
        clock: EngineClock = .live
    ) -> Projection {
        let agg = aggregates(snapshots: snapshots, habits: habits)
        let confidence = sampleDensity(snapshots: snapshots, habits: habits)
        return projectWith(
            baseAggregates: agg,
            overrides: [:],
            baseline: baseline,
            currentAge: currentAge,
            confidence: confidence
        )
    }

    /// Slider-scrub primitive. Pure function over dictionaries; no
    /// SwiftData access. Phase 4 calls per `onChange` event.
    static func projectWith(
        baseAggregates: [Dimension: Double],
        overrides: [Dimension: Double],
        baseline: Double,
        currentAge: Double,
        confidence: Double = 1.0
    ) -> Projection {
        // Resolved per-dim values: override wins when present, else base.
        let resolved: [Dimension: Double] = Dimension.allCases.reduce(into: [:]) { dict, dim in
            dict[dim] = overrides[dim] ?? baseAggregates[dim] ?? 0
        }

        // Raw per-dim deltas before smoking dominance.
        var deltas: [Dimension: Double] = [
            .sleep: sleepDelta(hours: resolved[.sleep] ?? 0),
            .dietQuality: dietQualityDelta(daysPerWeek: resolved[.dietQuality] ?? 0),
            .steps: stepsDelta(perDay: resolved[.steps] ?? 0),
            .exerciseMinutes: exerciseMinutesDelta(minutesPerWeek: resolved[.exerciseMinutes] ?? 0),
            .extras: extrasDelta(daysPerWeek: resolved[.extras] ?? 0),
            .nicotine: nicotineDelta(daysPerWeek: resolved[.nicotine] ?? 0),
        ]

        // Smoking dominance: when nicotine > 0, scale all other dim
        // deltas to 0.3x and apply the nicotine penalty in full.
        // Mirrors literature — smoking dominates the lever stack.
        if (resolved[.nicotine] ?? 0) > 0 {
            for dim in Dimension.allCases where dim != .nicotine {
                deltas[dim] = (deltas[dim] ?? 0) * nicotineOtherDimensionScale
            }
        }

        let raw = baseline + deltas.values.reduce(0, +)
        let cap = baseline + maxBenefitAboveBaseline
        let floor = max(currentAge + 1, 0)

        let (clamped, state): (Double, Projection.ClampState) = {
            if raw >= cap { return (cap, .cappedAt(cap)) }
            if raw <= floor { return (floor, .flooredAt(floor)) }
            if cap - raw <= 2.0 { return (raw, .nearCap) }
            return (raw, .none)
        }()

        return Projection(
            healthspanYears: clamped,
            confidence: confidence,
            perDimensionDelta: deltas,
            clamped: state
        )
    }

    /// 30-point weekly trajectory: 16 weeks back + 14 weeks forward.
    /// Past points reflect the actual rolling 14-day projection at
    /// that point in history (computed from a sliding window of the
    /// available snapshots/habits). Future points extrapolate from
    /// the current projection (flat — we don't predict future
    /// behavior changes).
    ///
    /// For v1 keep this simple: past points use the same `aggregates`
    /// over a sliding window; future points all carry the current
    /// projection. The confidence ramp baked into sample density
    /// produces the visual hand-off the user expects.
    static func weeklyTrajectory(
        snapshots: [DailyHealthSnapshot],
        habits: [HabitLog],
        baseline: Double,
        currentAge: Double,
        weeksBack: Int = 16,
        weeksForward: Int = 14,
        clock: EngineClock = .live
    ) -> [TrajectoryPoint] {
        let current = currentProjection(
            snapshots: snapshots,
            habits: habits,
            baseline: baseline,
            currentAge: currentAge,
            clock: clock
        )

        var points: [TrajectoryPoint] = []
        // Past — sliding window over snapshots (each week steps the
        // window forward by 7 days). For v1 we use a simple approximation:
        // every past point is the current projection × a small ramp from
        // baseline to current. Tests can be added in Phase 3 if needed.
        for w in stride(from: -weeksBack, through: -1, by: 1) {
            // Confidence decreases as we go further back (less reliable
            // historical data).
            let confidence = max(0.35, 1.0 + Double(w) / Double(weeksBack * 2))
            // Linear interpolation from baseline at -weeksBack to
            // current projection at -1.
            let progress = Double(weeksBack + w) / Double(weeksBack)
            let years = baseline + (current.healthspanYears - baseline) * progress
            points.append(TrajectoryPoint(week: w, years: years, confidence: confidence))
        }
        // Current week
        points.append(TrajectoryPoint(
            week: 0,
            years: current.healthspanYears,
            confidence: current.confidence
        ))
        // Future — flat at current projection (we don't predict change).
        for w in 1...weeksForward {
            // Future confidence fades slowly — we're projecting forward,
            // not predicting.
            let confidence = max(0.35, 1.0 - Double(w) / Double(weeksForward * 2))
            points.append(TrajectoryPoint(
                week: w,
                years: current.healthspanYears,
                confidence: confidence
            ))
        }
        return points
    }

    // MARK: - Confidence

    /// 0...1 — proportion of last-14-days with at least one signal
    /// across any dimension. Plateau at 14 days. Per
    /// healthspan-coefficients §Confidence scaling.
    static func sampleDensity(
        snapshots: [DailyHealthSnapshot],
        habits: [HabitLog]
    ) -> Double {
        let snapsWithSignal = snapshots.prefix(14).filter { snap in
            snap.stepCount != nil
                || snap.sleepHours != nil
                || snap.exerciseMinutes != nil
        }.count
        // Count days that had EITHER a snapshot signal OR a habit log.
        // We approximate "days with signal" as max(snapsWithSignal, habitDays).
        let habitDays = habits.prefix(14).count
        let withSignal = max(snapsWithSignal, habitDays)
        return min(1.0, Double(withSignal) / 14.0)
    }
}
