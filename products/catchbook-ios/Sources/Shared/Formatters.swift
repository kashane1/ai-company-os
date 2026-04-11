import Foundation

/// Shared app formatters. Uses a mutable `NSObject` singleton so a locale
/// change observer can rebuild cached `DateFormatter` instances when the user
/// switches regions mid-session (without this, formatters captured the old
/// locale and kept formatting against it until process relaunch).
///
/// Touch `AppFormatters.shared` from `CatchbookApp.init()` to install the
/// observer early in app startup.
final class AppFormattersBox: NSObject {
    static let shared = AppFormattersBox()

    private(set) var tripDate: DateFormatter = AppFormattersBox.makeTripDate()
    private(set) var shortTime: DateFormatter = AppFormattersBox.makeShortTime()
    private(set) var duration: DateComponentsFormatter = AppFormattersBox.makeDuration()

    override init() {
        super.init()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(localeDidChange),
            name: NSLocale.currentLocaleDidChangeNotification,
            object: nil
        )
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }

    @objc private func localeDidChange() {
        tripDate = AppFormattersBox.makeTripDate()
        shortTime = AppFormattersBox.makeShortTime()
        duration = AppFormattersBox.makeDuration()
    }

    private static func makeTripDate() -> DateFormatter {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter
    }

    private static func makeShortTime() -> DateFormatter {
        let formatter = DateFormatter()
        formatter.dateStyle = .none
        formatter.timeStyle = .short
        return formatter
    }

    private static func makeDuration() -> DateComponentsFormatter {
        let formatter = DateComponentsFormatter()
        formatter.allowedUnits = [.hour, .minute]
        formatter.unitsStyle = .abbreviated
        return formatter
    }
}

/// Static accessor facade preserved for call-site compatibility. These route
/// through the singleton so locale-change rebuilds are picked up automatically.
enum AppFormatters {
    static var shared: AppFormattersBox { AppFormattersBox.shared }
    static var tripDate: DateFormatter { AppFormattersBox.shared.tripDate }
    static var shortTime: DateFormatter { AppFormattersBox.shared.shortTime }
    static var duration: DateComponentsFormatter { AppFormattersBox.shared.duration }
}
