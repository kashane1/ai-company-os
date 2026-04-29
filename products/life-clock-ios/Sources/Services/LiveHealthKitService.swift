import Foundation
import HealthKit

/// Production HealthKit service. Talks to `HKHealthStore` for real per-day
/// aggregates of steps, exercise minutes, active energy, sleep, resting HR,
/// and weight. Uses `HKStatisticsCollectionQuery` for cumulative quantities
/// and `HKSampleQuery` for sleep (a category type with no statistics support).
///
/// Authorization is silent on read denials (Apple privacy design). We persist
/// "have we asked" via UserDefaults so the Profile screen can show
/// "Not configured" → "Available" / "No data" honestly, never "Connected" /
/// "Denied".
@MainActor
final class LiveHealthKitService: HealthKitServiceProtocol {
    private let store = HKHealthStore()
    private let calendar: Calendar
    private let userDefaults: UserDefaults

    private static let askedKey = "lc.hk.requestedCore"

    private let coreReadTypes: Set<HKObjectType> = {
        var types: Set<HKObjectType> = []
        if let stepCount = HKQuantityType.quantityType(forIdentifier: .stepCount) {
            types.insert(stepCount)
        }
        if let exerciseTime = HKQuantityType.quantityType(forIdentifier: .appleExerciseTime) {
            types.insert(exerciseTime)
        }
        if let activeEnergy = HKQuantityType.quantityType(forIdentifier: .activeEnergyBurned) {
            types.insert(activeEnergy)
        }
        if let restingHR = HKQuantityType.quantityType(forIdentifier: .restingHeartRate) {
            types.insert(restingHR)
        }
        if let bodyMass = HKQuantityType.quantityType(forIdentifier: .bodyMass) {
            types.insert(bodyMass)
        }
        if let sleep = HKCategoryType.categoryType(forIdentifier: .sleepAnalysis) {
            types.insert(sleep)
        }
        return types
    }()

    init(calendar: Calendar = .current, userDefaults: UserDefaults = .standard) {
        self.calendar = calendar
        self.userDefaults = userDefaults
    }

    // MARK: - Availability + Authorization

    var isHealthDataAvailable: Bool {
        HKHealthStore.isHealthDataAvailable()
    }

    /// Real authorization. Throws on `.unavailable` *and* on store-level
    /// errors (entitlement misconfiguration, missing usage description) so
    /// they surface in TestFlight logs instead of looking like silent denials.
    func requestAuthorization() async throws {
        guard isHealthDataAvailable else { throw HealthKitError.unavailable }
        try await store.requestAuthorization(toShare: [], read: coreReadTypes)
        userDefaults.set(true, forKey: Self.askedKey)
    }

    var authorizationKnown: Bool {
        userDefaults.bool(forKey: Self.askedKey)
    }

    // MARK: - Snapshot reads

    /// Always queries when HealthKit is available — does not gate on
    /// `authorizationKnown`. HealthKit returns empty for unauthorized reads
    /// (silent by privacy design); empty maps to nil snapshot which the UI
    /// renders as "missing data". Gating here would mean a user who granted
    /// permission outside the app (or whose UserDefaults flag was lost) saw
    /// permanent ghost-empty state.
    func dailySnapshot(for date: Date) async -> DailyHealthSnapshot? {
        guard isHealthDataAvailable else { return nil }
        let dayStart = calendar.startOfDay(for: date)
        guard let dayEnd = calendar.date(byAdding: .day, value: 1, to: dayStart) else { return nil }

        async let steps = sumQuantity(.stepCount, unit: .count(), start: dayStart, end: dayEnd)
        async let exercise = sumQuantity(.appleExerciseTime, unit: .minute(), start: dayStart, end: dayEnd)
        async let activeEnergy = sumQuantity(.activeEnergyBurned, unit: .kilocalorie(), start: dayStart, end: dayEnd)
        async let restingHR = averageQuantity(.restingHeartRate, unit: HKUnit(from: "count/min"), start: dayStart, end: dayEnd)
        async let weight = mostRecentQuantity(.bodyMass, unit: .gramUnit(with: .kilo), start: dayStart, end: dayEnd)
        async let sleep = sleepHours(start: dayStart, end: dayEnd)

        let stepCount = await steps
        let exerciseMinutes = await exercise
        let energy = await activeEnergy
        let resting = await restingHR
        let weightKg = await weight
        let sleepHrs = await sleep

        // A fully-empty day is nil (missing data), not synthetic zeros.
        if stepCount == nil, exerciseMinutes == nil, energy == nil, resting == nil, weightKg == nil, sleepHrs == nil {
            return nil
        }
        return HealthKitAggregator.aggregate(
            date: dayStart,
            stepCount: stepCount,
            exerciseMinutes: exerciseMinutes,
            activeEnergyKcal: energy,
            sleepHours: sleepHrs,
            restingHeartRate: resting,
            weightKg: weightKg
        )
    }

    func recentSnapshots(endingAt endDate: Date, count: Int) async -> [DailyHealthSnapshot] {
        var results: [DailyHealthSnapshot] = []
        for offset in stride(from: count - 1, through: 0, by: -1) {
            guard let day = calendar.date(byAdding: .day, value: -offset, to: endDate) else { continue }
            if let snap = await dailySnapshot(for: day) {
                results.append(snap)
            }
        }
        return results
    }

    // MARK: - Query helpers

    private func sumQuantity(
        _ identifier: HKQuantityTypeIdentifier,
        unit: HKUnit,
        start: Date,
        end: Date
    ) async -> Double? {
        guard let type = HKQuantityType.quantityType(forIdentifier: identifier) else { return nil }
        return await statisticsValue(type: type, options: .cumulativeSum, unit: unit, start: start, end: end) {
            $0.sumQuantity()
        }
    }

    private func averageQuantity(
        _ identifier: HKQuantityTypeIdentifier,
        unit: HKUnit,
        start: Date,
        end: Date
    ) async -> Double? {
        guard let type = HKQuantityType.quantityType(forIdentifier: identifier) else { return nil }
        return await statisticsValue(type: type, options: .discreteAverage, unit: unit, start: start, end: end) {
            $0.averageQuantity()
        }
    }

    private func mostRecentQuantity(
        _ identifier: HKQuantityTypeIdentifier,
        unit: HKUnit,
        start: Date,
        end: Date
    ) async -> Double? {
        guard let type = HKQuantityType.quantityType(forIdentifier: identifier) else { return nil }
        return await statisticsValue(type: type, options: .mostRecent, unit: unit, start: start, end: end) {
            $0.mostRecentQuantity()
        }
    }

    private func statisticsValue(
        type: HKQuantityType,
        options: HKStatisticsOptions,
        unit: HKUnit,
        start: Date,
        end: Date,
        selector: @escaping (HKStatistics) -> HKQuantity?
    ) async -> Double? {
        await withCheckedContinuation { continuation in
            let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)
            let query = HKStatisticsQuery(quantityType: type, quantitySamplePredicate: predicate, options: options) { _, statistics, _ in
                guard let statistics, let quantity = selector(statistics) else {
                    continuation.resume(returning: nil)
                    return
                }
                continuation.resume(returning: quantity.doubleValue(for: unit))
            }
            store.execute(query)
        }
    }

    private func sleepHours(start: Date, end: Date) async -> Double? {
        guard let type = HKCategoryType.categoryType(forIdentifier: .sleepAnalysis) else { return nil }
        // Wake-day attribution: a sleep block ending in [start, end) counts
        // toward this day even if it began the previous evening.
        let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictEndDate)
        return await withCheckedContinuation { continuation in
            let query = HKSampleQuery(sampleType: type, predicate: predicate, limit: HKObjectQueryNoLimit, sortDescriptors: nil) { _, samples, _ in
                guard let samples = samples as? [HKCategorySample] else {
                    continuation.resume(returning: nil)
                    return
                }
                let asleep: Set<Int> = [
                    HKCategoryValueSleepAnalysis.asleepCore.rawValue,
                    HKCategoryValueSleepAnalysis.asleepDeep.rawValue,
                    HKCategoryValueSleepAnalysis.asleepREM.rawValue,
                    HKCategoryValueSleepAnalysis.asleepUnspecified.rawValue,
                ]
                let totalSeconds = samples
                    .filter { asleep.contains($0.value) }
                    .reduce(0.0) { $0 + $1.endDate.timeIntervalSince($1.startDate) }
                continuation.resume(returning: totalSeconds > 0 ? totalSeconds / 3600 : nil)
            }
            store.execute(query)
        }
    }
}
