import XCTest
import UserNotifications
@testable import LifeClock

final class NotificationsServiceTests: XCTestCase {
    // MARK: - Tone-aware copy

    func testCopyForGentleTone() {
        let body = NotificationCopy.body(for: .gentle)
        XCTAssertEqual(body.title, "Two minutes for yourself?")
        XCTAssertEqual(body.body, "A quick log captures today. We'll save your spot.")
    }

    func testCopyForCoachTone() {
        let body = NotificationCopy.body(for: .coach)
        XCTAssertEqual(body.title, "Quick log time")
        XCTAssertEqual(body.body, "Two taps to capture today. Worth it.")
    }

    func testCopyForMementoMoriIsNeutral() {
        let body = NotificationCopy.body(for: .mementoMori)
        XCTAssertEqual(body.title, "Today's log")
        XCTAssertEqual(body.body, "A minute to capture today, when you can.")
    }

    /// Pin the App-Review-sensitive invariant: notification copy never
    /// contains mortality lexicon. Even Memento Mori (where the user
    /// actively chose dramatic in-app framing) gets neutral copy here
    /// because the notification meets the user OUTSIDE the app, on a
    /// Lock Screen or in front of others.
    func testNoMortalityLexiconInAnyToneCopy() {
        let forbidden = ["die", "death", "dying", "lifespan", "year left", "years left", "mortality", "mortal"]
        for tone in ToneMode.allCases {
            let body = NotificationCopy.body(for: tone)
            let combined = (body.title + " " + body.body).lowercased()
            for token in forbidden {
                XCTAssertFalse(
                    combined.contains(token),
                    "Notification copy for tone \(tone.rawValue) contains forbidden token '\(token)': \(combined)"
                )
            }
        }
    }
}
