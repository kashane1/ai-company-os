import XCTest
@testable import AfterPlans

@MainActor
final class OnboardingStateTests: XCTestCase {
    private func makeDefaults() -> UserDefaults {
        let suite = "afterplans.tests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)
        return defaults
    }

    func testFreshStateBeginsAtIntro() {
        let state = OnboardingState(defaults: makeDefaults())
        XCTAssertEqual(state.step, .intro)
        XCTAssertEqual(state.draft, OnboardingDraft())
    }

    func testAdvanceFollowsExpectedTransitions() {
        let state = OnboardingState(defaults: makeDefaults())
        let expected: [OnboardingStep] = [.name, .privacy, .activityVenue, .inviteCode, .complete]
        for step in expected {
            state.advance()
            XCTAssertEqual(state.step, step)
        }
    }

    func testGoBackUnwindsTransitions() {
        let state = OnboardingState(defaults: makeDefaults())
        state.advance()
        state.advance()
        XCTAssertEqual(state.step, .privacy)
        state.goBack()
        XCTAssertEqual(state.step, .name)
        state.goBack()
        XCTAssertEqual(state.step, .intro)
        state.goBack()
        XCTAssertEqual(state.step, .intro, "goBack from .intro is a no-op")
    }

    func testTerminalStepHasNoNext() {
        let state = OnboardingState(defaults: makeDefaults())
        state.skipToEnd()
        XCTAssertEqual(state.step, .complete)
        state.advance()
        XCTAssertEqual(state.step, .complete, "advance from .complete is a no-op")
    }

    func testDraftMutationsPersistAcrossInstances() {
        let defaults = makeDefaults()
        let first = OnboardingState(defaults: defaults)
        first.updateDraft { $0.firstName = "Sam" }
        first.advance()
        XCTAssertEqual(first.step, .name)

        let second = OnboardingState(defaults: defaults)
        XCTAssertEqual(second.step, .name, "step should resume from persisted state")
        XCTAssertEqual(second.draft.firstName, "Sam", "draft should resume from persisted state")
    }

    func testResetClearsPersistence() {
        let defaults = makeDefaults()
        let state = OnboardingState(defaults: defaults)
        state.updateDraft { $0.firstName = "Sam"; $0.privacyMode = .strict }
        state.advance()
        state.reset()
        XCTAssertEqual(state.step, .intro)
        XCTAssertEqual(state.draft, OnboardingDraft())
        XCTAssertNil(defaults.data(forKey: OnboardingState.persistenceKey))
    }

    func testHasMinimumNameRespectsTrim() {
        var draft = OnboardingDraft()
        draft.firstName = "   "
        XCTAssertFalse(draft.hasMinimumName)
        draft.firstName = "  Sam  "
        XCTAssertTrue(draft.hasMinimumName)
    }
}
