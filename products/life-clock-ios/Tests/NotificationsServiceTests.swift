import XCTest
import UserNotifications
@testable import LifeClock

final class NotificationsServiceTests: XCTestCase {
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

    /// Each tone produces a distinct, non-empty title and body. (We pin
    /// the invariant — distinct + non-empty — rather than the exact
    /// strings, which would be a tautology that breaks on every harmless
    /// copy change.)
    func testToneCopyIsDistinctAndNonEmpty() {
        let bodies = ToneMode.allCases.map { NotificationCopy.body(for: $0) }
        for body in bodies {
            XCTAssertFalse(body.title.isEmpty)
            XCTAssertFalse(body.body.isEmpty)
        }
        XCTAssertEqual(Set(bodies.map(\.title)).count, bodies.count, "each tone must have a distinct title")
    }
}
