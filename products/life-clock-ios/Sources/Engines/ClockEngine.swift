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

        // Healthspan dial atomic gate: the engine treats
        // (personalAdjustmentYears, anchorAdjustedAt) as logically
        // atomic. Until both are set the adjustment is 0; a partial
        // write left over from a killed app cannot double-apply. The
        // dial UI also keys idempotency off `anchorAdjustedAt`. See
        // docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md
        // Phase 5 for the full rationale.
        let dialAdjustment: Double = (profile.anchorAdjustedAt != nil)
            ? (profile.personalAdjustmentYears ?? 0)
            : 0

        let projected = baselineYears + lifestyleAdjustment + dialAdjustment
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

        // Baseline diet quality is a first-class lever alongside smoking,
        // alcohol, and activity. Small, bounded contribution — agency over
        // certainty. Per `CLOCK_MODEL.md`, these are tuning placeholders,
        // not clinical claims.
        switch profile.dietQualityBaseline.lowercased() {
        case "great": adjustment += 1.5
        case "rough": adjustment -= 1.5
        default: break // "okay" / unknown → neutral
        }

        // MARK: - Reveal-onboarding rebuild (additive 2026-05-01)
        //
        // Five additional lifestyle factors collected during the new
        // onboarding flow. All bounded; missing input ⇒ neutral. Coefficients
        // are tuning placeholders per CLOCK_MODEL.md, sourced from
        // epidemiology references but never expressed as medical predictions
        // in user-facing copy.

        // BMI (Global BMI Mortality Collaboration 2016; NHANES). Both
        // height and weight must be present to score; either missing ⇒
        // neutral.
        if let height = profile.heightCm, let weight = profile.weightKg, height > 0 {
            let heightM = height / 100.0
            let bmi = weight / (heightM * heightM)
            switch bmi {
            case ..<18.5: adjustment -= 1.5
            case 18.5..<25: break  // healthy range; neutral
            case 25..<30: adjustment -= 0.5
            case 30..<35: adjustment -= 2.0
            default: adjustment -= 4.0  // 35+
            }
        }

        // Cardio minutes per week (PA Guidelines 2018; Lee et al. 2014).
        // Distinct from `strengthFrequencyPerWeek`. 0 minutes is the
        // worst bucket; 150–300 hits the recommended range.
        switch profile.cardioMinsPerWeek {
        case 0: adjustment -= 1.0
        case 1..<150: adjustment += 0.5
        case 150...300: adjustment += 1.5
        default: adjustment += 2.0  // 301+
        }

        // Parental longevity (Sebastiani et al. 2012; Atzmon et al. 2010).
        // Each parent is independent. "Prefer not to say" ⇒ nil ⇒ neutral.
        // ≥90 ⇒ +1.0 yr; <65 ⇒ −1.0 yr; in-between ⇒ neutral.
        if let mAge = profile.parentMotherAgeAtDeath {
            if mAge >= 90 { adjustment += 1.0 }
            else if mAge < 65 { adjustment -= 1.0 }
        }
        if let fAge = profile.parentFatherAgeAtDeath {
            if fAge >= 90 { adjustment += 1.0 }
            else if fAge < 65 { adjustment -= 1.0 }
        }

        // Perceived stress (Cohen 1988 PSS-10; 0–40 range). Cohen's
        // category cutoffs: 0–13 low, 14–26 moderate, 27+ high.
        if let pss = profile.perceivedStressScore {
            switch pss {
            case 27...: adjustment -= 1.5
            case 14..<27: adjustment -= 0.5
            default: break  // low stress ⇒ neutral (no bonus)
            }
        }

        // Loneliness (UCLA-3; 3–9 range, with ≥6 typically classified as
        // "lonely"). Holt-Lunstad meta-analyses 2010, 2015.
        if let ucla = profile.lonelinessScore, ucla >= 6 {
            adjustment -= 1.5
        }

        return adjustment
    }

    // MARK: - Archetype computation (reveal-onboarding rebuild)

    /// Maps a `UserProfile` to one of four pace-based archetypes plus
    /// two sub-meter values (behavioralRisk, recoveryCapacity) used by
    /// the archetype-reveal screen. Rules-based, deterministic — same
    /// transparency principle as `lifestyleAdjustmentYears`. See
    /// `docs/plans/2026-05-01-feat-life-clock-reveal-onboarding-anchor-dial-plan.md`
    /// Phase 1b for the decision logic.
    struct ArchetypeResult: Equatable {
        let archetype: Archetype
        /// 0.0 = ideal lifestyle, 1.0 = highest behavioral risk.
        let behavioralRisk: Double
        /// 0.0 = poor recovery capacity, 1.0 = strong. Engine treats
        /// current behavior as a proxy for recoverability — high
        /// behavioralRisk ⇒ low recoveryCapacity.
        let recoveryCapacity: Double
    }

    func computeArchetype(profile: UserProfile) -> ArchetypeResult {
        let behavioralRisk = behavioralRiskScore(profile: profile)
        let geneticAnchor = geneticAnchorScore(profile: profile)
        let recoveryCapacity = max(0.0, min(1.0, 1.0 - behavioralRisk))

        let age = ageInYears(birthDate: profile.birthDate)

        let archetype: Archetype
        if behavioralRisk <= 0.3 {
            archetype = .marathoner
        } else if behavioralRisk > 0.6, age < 50 {
            archetype = .sprinter
        } else if geneticAnchor > 0.7, behavioralRisk > 0.4 {
            archetype = .outlier
        } else if behavioralRisk > 0.4, geneticAnchor < 0.5 {
            archetype = .sleeper
        } else {
            archetype = .marathoner
        }

        return ArchetypeResult(
            archetype: archetype,
            behavioralRisk: behavioralRisk,
            recoveryCapacity: recoveryCapacity
        )
    }

    /// Composite 0..1 score where 0 = no behavioral risk, 1 = worst.
    /// Equally weighted across the lifestyle factors that the engine
    /// also reads. Each factor contributes a normalized 0..1 sub-score;
    /// missing inputs are treated as the neutral midpoint (0.5) — they
    /// don't penalize, but they also can't lower the composite.
    private func behavioralRiskScore(profile: UserProfile) -> Double {
        var components: [Double] = []

        components.append(smokingRisk(profile.smokingStatus))
        components.append(alcoholRisk(profile.alcoholFrequency))
        components.append(strengthRisk(perWeek: profile.strengthFrequencyPerWeek))
        components.append(cardioRisk(minsPerWeek: profile.cardioMinsPerWeek))
        components.append(sleepRisk(goalHours: profile.sleepGoalHours))
        components.append(dietRisk(profile.dietQualityBaseline))
        components.append(bmiRisk(heightCm: profile.heightCm, weightKg: profile.weightKg))
        components.append(stressRisk(score: profile.perceivedStressScore))
        components.append(lonelinessRisk(score: profile.lonelinessScore))

        let avg = components.reduce(0, +) / Double(components.count)
        return max(0.0, min(1.0, avg))
    }

    /// Composite 0..1 score where 0 = poor genetic anchor, 1 = excellent.
    /// Both parents unknown ⇒ neutral 0.5 (no signal). Each parent
    /// contributes independently; very long-lived (≥90) parents push
    /// toward 1.0, very early loss (<65) pushes toward 0.0.
    private func geneticAnchorScore(profile: UserProfile) -> Double {
        let mother = parentLongevityScore(
            alive: profile.parentMotherAlive,
            ageAtDeath: profile.parentMotherAgeAtDeath
        )
        let father = parentLongevityScore(
            alive: profile.parentFatherAlive,
            ageAtDeath: profile.parentFatherAgeAtDeath
        )
        return (mother + father) / 2.0
    }

    private func parentLongevityScore(alive: Bool?, ageAtDeath: Int?) -> Double {
        // No data → neutral 0.5. Alive (regardless of current age) → 0.7
        // (positive but bounded — we don't know how long they'll live).
        // Deceased: linear-ish bucket on age at death.
        guard let alive else { return 0.5 }
        if alive { return 0.7 }
        guard let ageAtDeath else { return 0.5 }
        switch ageAtDeath {
        case 90...: return 1.0
        case 80..<90: return 0.85
        case 70..<80: return 0.6
        case 60..<70: return 0.35
        default: return 0.2  // <60
        }
    }

    private func smokingRisk(_ status: String) -> Double {
        switch status.lowercased() {
        case "heavy": return 1.0
        case "light", "occasional": return 0.7
        case "former": return 0.3
        default: return 0.0
        }
    }

    private func alcoholRisk(_ frequency: String) -> Double {
        switch frequency.lowercased() {
        case "heavy", "daily": return 0.8
        case "frequent", "weekly": return 0.4
        default: return 0.1
        }
    }

    private func strengthRisk(perWeek: Int) -> Double {
        switch perWeek {
        case 0: return 0.7
        case 1: return 0.4
        default: return 0.1  // ≥2/week
        }
    }

    private func cardioRisk(minsPerWeek: Int) -> Double {
        switch minsPerWeek {
        case 0: return 0.8
        case 1..<150: return 0.4
        case 150...300: return 0.15
        default: return 0.05  // 300+
        }
    }

    private func sleepRisk(goalHours: Double) -> Double {
        if goalHours >= 7.0, goalHours <= 9.0 { return 0.1 }
        if goalHours < 6.0 || goalHours > 10.0 { return 0.7 }
        return 0.4
    }

    private func dietRisk(_ quality: String) -> Double {
        switch quality.lowercased() {
        case "great": return 0.1
        case "rough": return 0.7
        default: return 0.4  // okay / unknown
        }
    }

    private func bmiRisk(heightCm: Double?, weightKg: Double?) -> Double {
        guard let h = heightCm, let w = weightKg, h > 0 else { return 0.5 }
        let heightM = h / 100.0
        let bmi = w / (heightM * heightM)
        switch bmi {
        case ..<18.5: return 0.5
        case 18.5..<25: return 0.1
        case 25..<30: return 0.4
        case 30..<35: return 0.7
        default: return 0.9  // 35+
        }
    }

    private func stressRisk(score: Int?) -> Double {
        guard let s = score else { return 0.5 }
        switch s {
        case 27...: return 0.85
        case 14..<27: return 0.5
        default: return 0.15
        }
    }

    private func lonelinessRisk(score: Int?) -> Double {
        guard let s = score else { return 0.5 }
        return s >= 6 ? 0.8 : 0.2
    }

    private func ageInYears(birthDate: Date) -> Int {
        let now = clock.now()
        let comps = clock.calendar.dateComponents([.year], from: birthDate, to: now)
        return max(0, comps.year ?? 0)
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

            // Diet quality is a first-class clock lever — small, bounded
            // delta (±12 min) so a single rough day never swings the clock
            // hard. Self-reported, medium confidence. Plain language only;
            // never names individual foods, never moralizes, never claims
            // medical certainty. The daily delta complements the baseline
            // adjustment in `lifestyleAdjustmentYears`.
            if let entry = dietDriver(habits: habits, date: snapshot.date) {
                drivers.append(entry)
                totalDelta += entry.deltaMinutes
            }
        }

        let confidence = ConfidenceModel.assign(snapshot: snapshot)
        return DailyDeltaResult(deltaMinutes: totalDelta, drivers: drivers, confidence: confidence)
    }

    private func dietDriver(habits: HabitLog, date: Date) -> TimeLedgerEntry? {
        // Composite of three self-reported diet signals. Each contributes
        // additively. Conservative coefficients keep the composite range
        // bounded (-15..+15), well inside other drivers' dynamic range.
        // No clamps — quality already sets the dominant sign.
        //
        // Missing-data rule (founder pack): defaults must never penalize.
        // V1.2.0 defaults — dietQuality="okay" (0), dietAmountRhythm="right"
        // (0), wholeFoodMeal="unknown" (0) — all contribute zero, so a row
        // that exists by virtue of being inserted (without a real user
        // signal) produces no ledger noise.
        let qualityDelta: Int
        let qualityTitle: String?
        switch habits.dietQuality.lowercased() {
        case "great":
            qualityDelta = 12
            qualityTitle = "Great diet quality logged"
        case "rough":
            qualityDelta = -10
            qualityTitle = "Rough diet quality logged"
        default:  // "okay" or unknown — neutral, no quality-specific title
            qualityDelta = 0
            qualityTitle = nil
        }

        let rhythmDelta: Int
        switch habits.dietAmountRhythm.lowercased() {
        case "overate":   rhythmDelta = -3
        case "undereate": rhythmDelta = -3
        case "skipbinge": rhythmDelta = -5
        case "irregular": rhythmDelta = -2
        default:          rhythmDelta = 0  // "right" or unknown
        }

        let anchorDelta: Int
        switch habits.wholeFoodMeal.lowercased() {
        case "yes":    anchorDelta = 3
        case "almost": anchorDelta = 1
        default:       anchorDelta = 0  // "no", "unknown", or anything else
        }

        let composite = qualityDelta + rhythmDelta + anchorDelta

        // Drop only when no signal at all. The prior single-axis
        // short-circuit dropped any "okay" entry; under the composite,
        // "okay" + skipBinge legitimately produces -5 and must surface.
        if composite == 0 && rhythmDelta == 0 && anchorDelta == 0 {
            return nil
        }

        // Confidence-by-evidence: when only rhythm/anchor contribute (no
        // quality answer beyond the default), the entry represents weaker
        // self-report. Downgrade from medium → low.
        let confidenceRaw: String = (qualityDelta == 0 && (rhythmDelta != 0 || anchorDelta != 0))
            ? Confidence.low.rawValue
            : Confidence.medium.rawValue

        let title = qualityTitle ?? "Diet check-in logged"

        return TimeLedgerEntry(
            date: date,
            title: title,
            deltaMinutes: composite,
            source: "manual",
            confidenceRaw: confidenceRaw,
            driverType: "diet"
        )
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
        // Suggest the next lever the user hasn't already shown a positive
        // delta on. Iteration order matters for determinism — use a sorted
        // list, never a Set.
        let positiveDrivers = Set(driverTotals.filter { $0.value > 0 }.keys)
        let candidates = ["movement", "sleep", "strength", "exercise"]
        for candidate in candidates where !positiveDrivers.contains(candidate) {
            return candidate
        }
        return positiveDrivers.sorted().first ?? "consistency"
    }
}
