import XCTest
import SwiftData
@testable import LifeClock

@MainActor
final class DailyReflectionStoreTests: XCTestCase {
    private let fixedDate = Date(timeIntervalSince1970: 1_800_000_000)

    /// IMPORTANT: retain the container alongside the store. On iOS 26.4
    /// simulator, `ModelContext` does not retain its `ModelContainer`,
    /// so a helper that returns only the store would let the container
    /// deallocate and subsequent SwiftData ops would trap. The store's
    /// `init` now holds `modelContext.container` defensively, but tests
    /// that build the container locally should still keep it alive
    /// explicitly for clarity.
    private func makeStore(at date: Date) throws -> (ModelContainer, LifeClockStore) {
        let container = try LifeClockContainer.make(inMemory: true)
        let store = LifeClockStore(
            healthService: MockHealthKitService(seed: 42),
            modelContext: container.mainContext,
            engineClock: .fixed(date)
        )
        return (container, store)
    }

    // MARK: - Smoke

    func testDailyReflectionInsertsAndFetchesViaContainer() throws {
        let container = try LifeClockContainer.make(inMemory: true)
        let ctx = container.mainContext
        let r = DailyReflection(dayKey: 20260501, prompt: "P", response: "R")
        ctx.insert(r)
        try ctx.save()
        let all = try ctx.fetch(FetchDescriptor<DailyReflection>())
        XCTAssertEqual(all.count, 1)
        XCTAssertEqual(all.first?.dayKey, 20260501)
    }

    // MARK: - Upsert behavior

    func testSaveReflectionInsertsForFirstSaveOfTheDay() throws {
        let (container, store) = try makeStore(at: fixedDate)
        _ = container
        XCTAssertNil(store.todayReflection, "no reflection should exist before first save")

        store.saveReflection(prompt: "What stood out today?", response: "Walked at lunch.")

        let saved = try XCTUnwrap(store.todayReflection)
        XCTAssertEqual(saved.prompt, "What stood out today?")
        XCTAssertEqual(saved.response, "Walked at lunch.")
        XCTAssertEqual(saved.dayKey, DayKey.from(date: fixedDate, calendar: .current))
    }

    func testRepeatedSaveOnSameDayUpsertsRatherThanDuplicating() throws {
        let (container, store) = try makeStore(at: fixedDate)
        store.saveReflection(prompt: "Prompt A", response: "First take.")
        store.saveReflection(prompt: "Prompt A", response: "Edited take.")

        let current = try XCTUnwrap(store.todayReflection)
        XCTAssertEqual(current.response, "Edited take.")

        // Direct fetch via the same container — proves only one row exists.
        let all = (try? container.mainContext.fetch(FetchDescriptor<DailyReflection>())) ?? []
        XCTAssertEqual(all.count, 1, "upsert must not create a duplicate row for the same day")
    }

    func testSaveReflectionReStampsPromptOnEdit() throws {
        let (container, store) = try makeStore(at: fixedDate)
        _ = container
        store.saveReflection(prompt: "Original prompt", response: "Response.")
        store.saveReflection(prompt: "Rotated prompt", response: "Response.")

        let saved = try XCTUnwrap(store.todayReflection)
        XCTAssertEqual(saved.prompt, "Rotated prompt", "prompt must be re-stamped on edit")
    }

    // MARK: - Cross-day lookup

    func testReflectionForArbitraryDayReturnsTheRightRow() throws {
        let day1 = fixedDate
        let day2 = fixedDate.addingTimeInterval(86_400 * 2)

        let (container, store) = try makeStore(at: day2)
        _ = container
        store.saveReflection(prompt: "P2", response: "R2")

        let day2Row = try XCTUnwrap(store.reflection(for: day2))
        XCTAssertEqual(day2Row.response, "R2")
        XCTAssertNil(store.reflection(for: day1))
    }

    // MARK: - Prompt rotation determinism

    func testPromptForSameDayIsStableAcrossCalls() {
        let p1 = ReflectionPrompts.prompt(for: fixedDate, calendar: .current)
        let p2 = ReflectionPrompts.prompt(for: fixedDate, calendar: .current)
        XCTAssertEqual(p1, p2, "same day must return the same prompt")
    }

    func testPromptDiffersAcrossDaysWhenIndicesDiffer() {
        let p1 = ReflectionPrompts.prompt(for: fixedDate, calendar: .current)
        let p2 = ReflectionPrompts.prompt(for: fixedDate.addingTimeInterval(86_400), calendar: .current)
        XCTAssertNotEqual(p1, p2, "consecutive days must rotate to different prompts")
    }

    func testPromptPoolIsLargerThanTen() {
        XCTAssertGreaterThanOrEqual(
            ReflectionPrompts.pool.count, 10,
            "pool must be large enough to avoid same-prompt-every-N-days fatigue"
        )
    }

    // MARK: - DayKey

    func testDayKeyIsTimezoneStableForSameLocalDay() {
        let calendar = Calendar(identifier: .gregorian)
        let t1 = Date(timeIntervalSince1970: 1_800_000_000)
        let t2 = t1.addingTimeInterval(7200) // +2h; same local calendar day in UTC
        XCTAssertEqual(
            DayKey.from(date: t1, calendar: calendar),
            DayKey.from(date: t2, calendar: calendar),
            "two timestamps within the same local day must map to the same dayKey"
        )
    }
}
