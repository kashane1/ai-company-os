import Foundation

enum HomeToolbarAction: String, CaseIterable {
    case exportLogbookBackup

    var label: String {
        switch self {
        case .exportLogbookBackup:
            return "Export Logbook Backup"
        }
    }

    var accessibilityIdentifier: String {
        switch self {
        case .exportLogbookBackup:
            return "home.exportLogbookBackupButton"
        }
    }
}
