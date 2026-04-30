import UserNotifications
import Foundation

/// Local-only daily-reminder notification service. No Push, no APNs,
/// no backend — `UNUserNotificationCenter` handles delivery on-device.
///
/// Suppression model: when the user logs habits, the store calls
/// `cancelTodayUntilTomorrowMorning` to drop the pending repeating
/// request; the next `reconcileNotifications()` invocation re-installs
/// it, by which point today's hour is past and only tomorrow's fires.
protocol NotificationsServiceProtocol: Sendable {
    func requestAuthorization() async -> Bool
    func currentAuthorizationStatus() async -> UNAuthorizationStatus
    func installForegroundDelegate()
    func setSchedule(enabled: Bool, hour: Int, tone: ToneMode) async
    func cancelTodayUntilTomorrowMorning() async
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

    func setSchedule(enabled: Bool, hour: Int, tone: ToneMode) async {
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

        var components = DateComponents()
        components.hour = hour
        components.minute = 0

        let trigger = UNCalendarNotificationTrigger(
            dateMatching: components,
            repeats: true
        )
        let request = UNNotificationRequest(
            identifier: identifier,
            content: content,
            trigger: trigger
        )
        try? await center.add(request)
    }

    func cancelTodayUntilTomorrowMorning() async {
        center.removePendingNotificationRequests(withIdentifiers: [identifier])
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
        case .mementoMori:
            // Neutral by design — see plan §"Tone-aware copy".
            // Mortality framing in-app where the user picked the tone is
            // fine; mortality framing on a Lock Screen notification is a
            // 1.4.1 rejection waiting to happen.
            Body(title: "Today's log",
                 body: "A minute to capture today, when you can.")
        }
    }
}
