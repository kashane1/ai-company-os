import Foundation

/// Pure, deterministic rules engine. Translates user profile + daily snapshot +
/// optional habit log into a Life Clock estimate, a daily time delta, and a
/// list of explainable ledger entries.
///
/// Anchor: CDC US life expectancy at birth (Mortality in the United States,
/// 2024) — 79.0 both sexes / 76.5 male / 81.4 female. Used as a population
/// reference, not a personal guarantee.
struct ClockEngine {
    let clock: EngineClock

    init(clock: EngineClock = .live) {
        self.clock = clock
    }

    // MARK: - Baseline

    func calculateBaseline(profile: UserProfile) -> LifeClockEstimate {
        let baselineYears = populationBaseline(for: profile.biologicalSex)
        let lifestyleAdjustment = lifestyleAdjustmentYears(profile: profile)

        let projected = baselineYears + lifestyleAdjustment
        let now = clock.now()
        let estimate = LifeClockEstimate(date: now)
        estimate.projectedAgeYears = projected
        estimate.projectedDate = projectedDate(birth: profile.birthDate, projectedAge: projected)
        estimate.healthspanScore = healthspanScore(years: projected, baseline: baselineYears)
        estimate.dailyTimeDeltaMinutes = 0
        estimate.confidenceRaw = Confidence.medium.rawValue
        estimate.explanation = "Starting estimate based on population baseline plus your reported habits."
        return estimate
    }

    /// Population anchors. Source: CDC FastStats Life Expectancy.
    private func populationBaseline(for sex: String) -> Double {
        switch sex.lowercased() {
        case "male", "m": return 76.5
        case "female", "f": return 81.4
        default: return 79.0
        }
    }

    private func lifestyleAdjustmentYears(profile: UserProfile) -> Double {
        var adjustment = 0.0

        switch profile.smokingStatus.lowercased() {
        case "heavy": adjustment -= 8.0
        case "light", "occasional": adjustment -= 3.0
        case "former": adjustment -= 1.0
        default: break
        }

        switch profile.alcoholFrequency.lowercased() {
        case "heavy", "daily": adjustment -= 2.5
        case "frequent", "weekly": adjustment -= 0.5
        default: break
        }

        if profile.strengthFrequencyPerWeek >= 2 { adjustment += 1.5 }
        if profile.sleepGoalHours >= 7.0, profile.sleepGoalHours <= 9.0 { adjustment += 1.0 }

        return adjustment
    }

    private func projectedDate(birth: Date, projectedAge: Double) -> Date? {
        let totalDays = projectedAge * 365.2425
        return clock.calendar.date(byAdding: .day, value: Int(totalDays.rounded()), to: birth)
    }

    private func healthspanScore(years: Double, baseline: Double) -> Double {
        let delta = years - baseline
        // Map ±10 years around baseline to roughly 0..100.
        let normalized = (delta + 10.0) / 20.0
        return max(0.0, min(100.0, normalized * 100.0))
    }

    // MARK: - Daily delta

    struct DailyDeltaResult {
        let deltaMinutes: Int
        let drivers: [TimeLedgerEntry]
        let confidence: Confidence
    }

    func calculateDailyDelta(
        snapshot: DailyHealthSnapshot,
        habits: HabitLog?,
        profile: UserProfile
    ) -> DailyDeltaResult {
        var drivers: [TimeLedgerEntry] = []
        var totalDelta = 0

        // Movement
        if let steps = snapshot.stepCount {
            let entry = movementDriver(steps: steps, date: snapshot.date)
            drivers.append(entry)
            totalDelta += entry.deltaMinutes
        }

        // Exercise
        if let exercise = snapshot.exerciseMinutes, exercise > 0 {
            let delta = exercise >= 30 ? 25 : (exercise >= 15 ? 15 : 5)
            drivers.append(
                TimeLedgerEntry(
                    date: snapshot.date,
                    title: "\(exercise) exercise minutes",
                    deltaMinutes: delta,
                    source: "healthkit",
                    confidenceRaw: Confidence.high.rawValue,
                    driverType: "exercise"
                )
            )
            totalDelta += delta
        }

        // Sleep
        if let hours = snapshot.sleepHours {
            let entry = sleepDriver(hours: hours, goal: profile.sleepGoalHours, date: snapshot.date)
            drivers.append(entry)
            totalDelta += entry.deltaMinutes
        }

        // Habits
        if let habits {
            if habits.alcoholLevel.lowercased() == "heavy" {
                let delta = -25
                drivers.append(
                    TimeLedgerEntry(
                        date: snapshot.date,
                        title: "Heavy alcohol logged",
                        deltaMinutes: delta,
                        source: "manual",
                        confidenceRaw: Confidence.medium.rawValue,
                        driverType: "alcohol"
                    )
                )
                totalDelta += delta
            }
            if habits.smokingVaping {
                let delta = -30
                drivers.append(
                    TimeLedgerEntry(
                        date: snapshot.date,
                        title: "Smoking/vaping logged",
                        deltaMinutes: delta,
                        source: "manual",
                        confidenceRaw: Confidence.medium.rawValue,
                        driverType: "smoking"
                    )
                )
                totalDelta += delta
            }
            if habits.strengthTraining {
                let delta = 30
                drivers.append(
                    TimeLedgerEntry(
                        date: snapshot.date,
                        title: "Strength training completed",
                        deltaMinutes: delta,
                        source: "manual",
                        confidenceRaw: Confidence.high.rawValue,
                        driverType: "strength"
                    )
                )
                totalDelta += delta
            }
        }

        let confidence = ConfidenceModel.assign(snapshot: snapshot)
        return DailyDeltaResult(deltaMinutes: totalDelta, drivers: drivers, confidence: confidence)
    }

    private func movementDriver(steps: Int, date: Date) -> TimeLedgerEntry {
        let delta: Int
        let title: String
        if steps >= 10_000 {
            delta = 25
            title = "\(steps) steps"
        } else if steps >= 7_500 {
            delta = 15
            title = "\(steps) steps"
        } else if steps >= 5_000 {
            delta = 8
            title = "\(steps) steps"
        } else if steps >= 2_500 {
            delta = -5
            title = "\(steps) steps — light day"
        } else {
            delta = -12
            title = "\(steps) steps — sedentary day"
        }
        return TimeLedgerEntry(
            date: date,
            title: title,
            deltaMinutes: delta,
            source: "healthkit",
            confidenceRaw: Confidence.high.rawValue,
            driverType: "movement"
        )
    }

    private func sleepDriver(hours: Double, goal: Double, date: Date) -> TimeLedgerEntry {
        let lower = goal - 1.0
        let upper = goal + 1.5
        let delta: Int
        let title: String
        if hours >= lower, hours <= upper {
            delta = 18
            title = String(format: "%.1fh sleep", hours)
        } else if hours < 5.0 {
            delta = -15
            title = String(format: "%.1fh sleep — too short", hours)
        } else {
            delta = 5
            title = String(format: "%.1fh sleep", hours)
        }
        return TimeLedgerEntry(
            date: date,
            title: title,
            deltaMinutes: delta,
            source: "healthkit",
            confidenceRaw: Confidence.high.rawValue,
            driverType: "sleep"
        )
    }

    // MARK: - Weekly trend

    func calculateWeeklyTrend(
        snapshots: [DailyHealthSnapshot],
        habits: [HabitLog],
        profile: UserProfile
    ) -> WeeklyReport {
        guard !snapshots.isEmpty else {
            let now = clock.now()
            let report = WeeklyReport(weekStart: now, weekEnd: now)
            report.confidenceRaw = Confidence.low.rawValue
            return report
        }

        let sorted = snapshots.sorted { $0.date < $1.date }
        let weekStart = sorted.first!.date
        let weekEnd = sorted.last!.date

        let habitsByDay = Dictionary(grouping: habits, by: { $0.date })

        var net = 0
        var driverTotals: [String: Int] = [:]

        for snapshot in sorted {
            let habitForDay = habitsByDay[snapshot.date]?.first
            let result = calculateDailyDelta(snapshot: snapshot, habits: habitForDay, profile: profile)
            net += result.deltaMinutes
            for driver in result.drivers {
                driverTotals[driver.driverType, default: 0] += driver.deltaMinutes
            }
        }

        let topPositive = driverTotals.filter { $0.value > 0 }.max { $0.value < $1.value }?.key ?? "—"
        let topNegative = driverTotals.filter { $0.value < 0 }.min { $0.value < $1.value }?.key ?? "—"
        let nextLever = nextBestLever(driverTotals: driverTotals)

        let report = WeeklyReport(weekStart: weekStart, weekEnd: weekEnd)
        report.netTimeDeltaMinutes = net
        report.topPositiveDriver = topPositive
        report.topNegativeDriver = topNegative
        report.nextBestLever = nextLever
        let avgCompleteness = sorted.map(\.sourceCompleteness).reduce(0, +) / Double(sorted.count)
        report.confidenceRaw = avgCompleteness >= 0.7
            ? Confidence.high.rawValue
            : (avgCompleteness >= 0.4 ? Confidence.medium.rawValue : Confidence.low.rawValue)
        return report
    }

    private func nextBestLever(driverTotals: [String: Int]) -> String {
        // Suggest the smallest absolute-impact lever we haven't seen positively.
        let positiveDrivers = Set(driverTotals.filter { $0.value > 0 }.keys)
        let candidates = ["movement", "sleep", "strength", "exercise"]
        for candidate in candidates where !positiveDrivers.contains(candidate) {
            return candidate
        }
        return positiveDrivers.first ?? "consistency"
    }
}
