import XCTest

/// Throwaway recon driver for `simulator-driven-polish` freeform-polish
/// runs on the v2 onboarding flow. Walks cold-open → first reveal +
/// captures per-screen screenshots and AX-tree dumps to /tmp/lifeclock-polish/.
///
/// Not part of CI. Intended to be deleted at session end.
final class OnboardingRhythmRecon: XCTestCase {
    private var app: XCUIApplication!
    private let outDir = "/tmp/lifeclock-polish"

    override func setUpWithError() throws {
        continueAfterFailure = true
        try? FileManager.default.removeItem(atPath: outDir)
        try? FileManager.default.createDirectory(
            atPath: outDir, withIntermediateDirectories: true
        )
    }

    func testWalkAndCapture() throws {
        app = XCUIApplication()
        app.launchEnvironment["LIFECLOCK_UI_TEST"] = "1"
        app.launchEnvironment["LIFECLOCK_UI_TEST_SCENARIO"] = "onboarding"
        app.launchEnvironment["LIFECLOCK_USE_MOCK_HEALTH"] = "1"
        app.launch()

        // 01 coldOpen — auto-advances ~2s. Capture-best-effort then let
        // welcome arrive on its own.
        capture("01-coldOpen")

        // 02 welcome — scaffolds resolve as buttons (single tap target).
        wait("onboarding.welcome", file: "02-welcome", timeout: 10)
        tapContinue()

        // 03 meetYourClock
        wait("onboarding.meetYourClock", file: "03-meetYourClock")
        tapContinue()

        // 04 reactiveSlider
        wait("onboarding.reactiveSlider", file: "04-reactiveSlider")
        tapContinue()

        // 05 personalizeIntro removed 2026-05-05 — coordinator now goes
        // reactiveSlider -> goalPick directly. Skip the wait.

        // 06 goalPick
        wait("onboarding.goalPick", file: "06-goalPick")
        tapByLabelContains("Just curious")
        capture("06b-goalPick-selected")
        tapContinue()

        // 07 baselineDOB
        wait("onboarding.baselineDOB", file: "07-baselineDOB")
        tapContinue()

        // 08 baselineSex
        wait("onboarding.baselineSex", file: "08-baselineSex")
        tapByLabelContains("Prefer not to say")
        tapContinue()

        // 09 bodyComp
        wait("onboarding.bodyComp", file: "09-bodyComp")
        tapContinue()

        // 10 smoking — pick NEGATIVE so the per-answer reaction has
        // signal worth showing. Capture both pre-tap (mascot at baseline)
        // and post-tap (mascot reacting) to measure the delta.
        wait("onboarding.smoking", file: "10-smoking")
        tapByLabelContains("Daily")
        usleep(900_000) // 80ms debounce + spring + reaction window
        capture("10b-smoking-after-daily")
        tapContinue()

        // 11 alcohol — POSITIVE: "Rarely or never" is baseline-positive
        // relative to a "Daily smoker" anchor; pick "Most days" first to
        // probe the strong-negative reaction stacking.
        wait("onboarding.alcohol", file: "11-alcohol")
        tapByLabelContains("Most days")
        usleep(900_000)
        capture("11b-alcohol-after-most-days")
        tapContinue()

        // 12 strength — bump stepper a few times to verify live-draft
        // commits fire during input (the +/- taps should each move the
        // mascot before Continue is even tapped).
        wait("onboarding.strength", file: "12-strength")
        let stepUp = app.buttons["Increment"].firstMatch
        if stepUp.waitForExistence(timeout: 2) {
            for _ in 0..<5 { stepUp.tap() }
        }
        usleep(900_000)
        capture("12b-strength-after-5-stepups")
        tapContinue()

        // 13 cardio
        wait("onboarding.cardio", file: "13-cardio")
        tapContinue()

        // 14 sleep
        wait("onboarding.sleep", file: "14-sleep")
        tapContinue()

        // 15 diet — strong negative for one more reaction sample.
        wait("onboarding.diet", file: "15-diet")
        tapByLabelContains("Rough")
        usleep(900_000)
        capture("15b-diet-after-rough")
        tapContinue()

        // 16 sensitiveConsent — take the skip path
        wait("onboarding.sensitiveConsent", file: "16-sensitiveConsent")
        if !tapByLabelContains("Skip", required: false) {
            tapContinue()
        }

        // 17 tone
        wait("onboarding.tone", file: "17-tone")
        if app.buttons["onboarding.tone.coach"].exists {
            app.buttons["onboarding.tone.coach"].tap()
        } else {
            tapByLabelContains("Default")
        }
        tapContinue()

        // 18 priorAttempts
        wait("onboarding.priorAttempts", file: "18-priorAttempts")
        if app.buttons["onboarding.priorAttempts.firstTime"].exists {
            app.buttons["onboarding.priorAttempts.firstTime"].tap()
        } else {
            tapByLabelContains("First time")
        }
        tapContinue()

        // 19 analyzing — auto-advances ~4.5s
        wait("onboarding.analyzing", file: "19-analyzing")

        // 20 archetypeReveal
        wait("onboarding.archetypeReveal", file: "20-archetypeReveal", timeout: 10)
        tapContinue()

        // 21 lifeGridRemaining (justCurious skips bigNumberPenalty)
        wait("onboarding.lifeGridRemaining", file: "21-lifeGridRemaining")
        tapContinue()

        // 22 engineRevealAndDial — the FIRST LIFE CLOCK REVEAL
        wait("onboarding.engineRevealAndDial", file: "22-engineRevealAndDial")
        // Brief settle so the on-appear animations finish before the
        // golden capture.
        sleep(1)
        capture("22b-engineRevealAndDial-settled")
    }

    // MARK: - Helpers

    private func wait(_ id: String, file: String, timeout: TimeInterval = 6) {
        // Scaffolds resolve as buttons (single-tap target inside ZStack);
        // data-collection screens with multiple controls register as
        // otherElements. Match either to keep the driver flexible.
        let any = app.descendants(matching: .any).matching(identifier: id).firstMatch
        let exists = any.waitForExistence(timeout: timeout)
        XCTAssertTrue(exists, "did not reach \(id)")
        capture(file)
    }

    /// Tap whichever button advances the current screen. On scaffold
    /// screens with EmptyView() content the AX collapses the screen body
    /// into a single button identified by the screen id; on screens with
    /// inputs the scaffold's Continue button keeps its own identifier.
    private func tapContinue() {
        if app.buttons["onboarding.continue"].exists {
            app.buttons["onboarding.continue"].tap()
            return
        }
        // Fallback: tap the only enabled button that isn't Back/header.
        let candidates = app.buttons.allElementsBoundByIndex
        for b in candidates where b.identifier.hasPrefix("onboarding.") &&
            b.identifier != "onboarding.header" &&
            b.identifier != "onboarding.header.back" &&
            b.isHittable {
            b.tap()
            return
        }
        XCTFail("no advance-button found; ids=\(candidates.map { $0.identifier })")
    }

    @discardableResult
    private func tapByLabel(_ label: String, required: Bool = true) -> Bool {
        let pred = NSPredicate(format: "label ==[c] %@", label)
        let el = app.buttons.matching(pred).firstMatch
        if el.waitForExistence(timeout: 2) {
            el.tap()
            return true
        }
        if required { XCTFail("button labeled '\(label)' not found") }
        return false
    }

    @discardableResult
    private func tapByLabelContains(_ substring: String, required: Bool = true) -> Bool {
        let pred = NSPredicate(format: "label CONTAINS[c] %@", substring)
        let el = app.buttons.matching(pred).firstMatch
        if el.waitForExistence(timeout: 2) {
            el.tap()
            return true
        }
        if required { XCTFail("button containing '\(substring)' not found") }
        return false
    }

    private func capture(_ name: String) {
        let png = XCUIScreen.main.screenshot().pngRepresentation
        try? png.write(to: URL(fileURLWithPath: "\(outDir)/\(name).png"))
        let ax = app.debugDescription
        try? ax.write(
            toFile: "\(outDir)/\(name).ax.txt",
            atomically: true, encoding: .utf8
        )
    }
}
