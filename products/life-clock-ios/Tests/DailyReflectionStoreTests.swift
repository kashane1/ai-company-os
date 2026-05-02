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
        let p1 = ReflectionPrompts.prompt(for: fixedDate, tone: .coach, calendar: .current)
        let p2 = ReflectionPrompts.prompt(for: fixedDate, tone: .coach, calendar: .current)
        XCTAssertEqual(p1, p2, "same day + tone must return the same prompt")
    }

    func testPromptDiffersAcrossDaysWhenIndicesDiffer() {
        let p1 = ReflectionPrompts.prompt(for: fixedDate, tone: .coach, calendar: .current)
        let p2 = ReflectionPrompts.prompt(
            for: fixedDate.addingTimeInterval(86_400),
            tone: .coach,
            calendar: .current
        )
        XCTAssertNotEqual(p1, p2, "consecutive days must rotate to different prompts")
    }

    func testEachTonePoolHasEnoughPromptsToAvoidFatigue() {
        for tone in ToneMode.allCases {
            XCTAssertGreaterThanOrEqual(
                ReflectionPrompts.pool(for: tone).count, 10,
                "\(tone) pool must be large enough to avoid same-prompt-every-N-days fatigue"
            )
        }
    }

    func testTonePoolsAreDisjoint() {
        // Different tones must produce different prompt pools or the
        // tone selection is decorative.
        let g = Set(ReflectionPrompts.gentlePool)
        let c = Set(ReflectionPrompts.coachPool)
        let f = Set(ReflectionPrompts.firmDirectPool)
        XCTAssertTrue(g.isDisjoint(with: c), "gentle and coach pools must not overlap")
        XCTAssertTrue(c.isDisjoint(with: f), "coach and firmDirect pools must not overlap")
        XCTAssertTrue(g.isDisjoint(with: f), "gentle and firmDirect pools must not overlap")
    }

    func testPromptDiffersAcrossTonesOnSameDay() {
        // Pick a day where the index lands in the same row across pools
        // — disjoint pools mean the prompt strings still differ. This is
        // the visible-to-user guarantee.
        let gentle = ReflectionPrompts.prompt(for: fixedDate, tone: .gentle, calendar: .current)
        let coach = ReflectionPrompts.prompt(for: fixedDate, tone: .coach, calendar: .current)
        let firm = ReflectionPrompts.prompt(for: fixedDate, tone: .firmDirect, calendar: .current)
        XCTAssertNotEqual(gentle, coach)
        XCTAssertNotEqual(coach, firm)
        XCTAssertNotEqual(gentle, firm)
    }

    // MARK: - Delete

    func testDeleteTodayReflectionRemovesPersistedRow() throws {
        let (container, store) = try makeStore(at: fixedDate)
        store.saveReflection(prompt: "Prompt", response: "Initial response.")
        XCTAssertNotNil(store.todayReflection)

        store.deleteTodayReflection()
        XCTAssertNil(store.todayReflection, "todayReflection must clear after delete")

        let all = (try? container.mainContext.fetch(FetchDescriptor<DailyReflection>())) ?? []
        XCTAssertTrue(all.isEmpty, "delete must remove the persisted row, not just clear the cache")
    }

    func testDeleteTodayReflectionIsNoOpWhenNoneExists() throws {
        let (container, store) = try makeStore(at: fixedDate)
        _ = container
        // No save before delete.
        store.deleteTodayReflection()
        XCTAssertNil(store.todayReflection)
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
