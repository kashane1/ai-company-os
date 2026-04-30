import UserNotifications
import Foundation

/// Local-only daily-reminder service — no APNs, no backend.
protocol NotificationsServiceProtocol: Sendable {
    func requestAuthorization() async -> Bool
    func currentAuthorizationStatus() async -> UNAuthorizationStatus
    func installForegroundDelegate()
    /// Install the daily-reminder schedule.
    ///
    /// - Parameter suppressUntil: If non-nil, a moment in the future
    ///   (typically tomorrow's reminder hour) before which the
    ///   notification must not fire. Used to skip today's hour when the
    ///   user has already logged this morning. The repeating trigger is
    ///   replaced by a non-repeating one-shot at `suppressUntil`; the
    ///   next reconcile (next launch, next mutator, scenePhase active)
    ///   restores the repeating shape automatically.
    func setSchedule(enabled: Bool, hour: Int, tone: ToneMode, suppressUntil: Date?, calendar: Calendar) async
    func cancelAll() async
}

private let identifier = "daily-reminder"

actor NotificationsService: NotificationsServiceProtocol {
    private let center = UNUserNotificationCenter.current()

    func requestAuthorization() async -> Bool {
        (try? await center.requestAuthorization(options: [.alert, .sound, .badge])) ?? false
    }

    func currentAuthorizationStatus() async -> UNAuthorizationStatus {
        await center.notificationSettings().authorizationStatus
    }

    nonisolated func installForegroundDelegate() {
        // Delegate lives on a stateless shared instance so the actor doesn't
        // need to own it — UNUserNotificationCenter holds it weakly anyway.
        UNUserNotificationCenter.current().delegate = ForegroundDelegate.shared
    }

    func setSchedule(
        enabled: Bool,
        hour: Int,
        tone: ToneMode,
        suppressUntil: Date?,
        calendar: Calendar
    ) async {
        // Always start clean — idempotent across rapid mutator calls.
        center.removePendingNotificationRequests(withIdentifiers: [identifier])
        guard enabled else { return }

        let copy = NotificationCopy.body(for: tone)
        let content = UNMutableNotificationContent()
        content.title = copy.title
        content.body = copy.body
        content.sound = .default
        // .active (not .timeSensitive) — a habit nudge isn't urgent in
        // Apple's sense; misusing .timeSensitive can trigger reviewer
        // pushback per HIG.
        content.interruptionLevel = .active

        let trigger: UNNotificationTrigger
        if let suppressUntil {
            // Suppression path: install a one-shot at the suppression
            // boundary (typically tomorrow's reminder hour). The next
            // reconcile restores the repeating shape automatically.
            let skipComponents = calendar.dateComponents(
                [.year, .month, .day, .hour, .minute],
                from: suppressUntil
            )
            trigger = UNCalendarNotificationTrigger(
                dateMatching: skipComponents,
                repeats: false
            )
        } else {
            var components = DateComponents()
            components.hour = hour
            components.minute = 0
            trigger = UNCalendarNotificationTrigger(
                dateMatching: components,
                repeats: true
            )
        }

        let request = UNNotificationRequest(
            identifier: identifier,
            content: content,
            trigger: trigger
        )
        try? await center.add(request)
    }

    func cancelAll() async {
        center.removePendingNotificationRequests(withIdentifiers: [identifier])
    }
}

/// Implements foreground-presentation so a notification fired while the
/// app IS in the foreground still surfaces as a banner. Without this,
/// iOS silently suppresses foreground notifications.
private final class ForegroundDelegate: NSObject, UNUserNotificationCenterDelegate {
    static let shared = ForegroundDelegate()

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        completionHandler([.banner, .sound, .list])
    }
}

enum NotificationCopy {
    struct Body: Equatable { let title: String; let body: String }

    static func body(for tone: ToneMode) -> Body {
        switch tone {
        case .gentle:
            Body(title: "Two minutes for yourself?",
                 body: "A quick log captures today. We'll save your spot.")
        case .coach:
            Body(title: "Quick log time",
                 body: "Two taps to capture today. Worth it.")
        }
    }
}
