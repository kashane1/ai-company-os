import XCTest
@testable import Catchbook

final class HomeToolbarActionTests: XCTestCase {
    func testHomeExposesExactlyOneBackupExportEntryPoint() {
        XCTAssertEqual(HomeToolbarAction.allCases, [.exportLogbookBackup])
        XCTAssertEqual(HomeToolbarAction.exportLogbookBackup.label, "Export Logbook Backup")
        XCTAssertEqual(
            HomeToolbarAction.exportLogbookBackup.accessibilityIdentifier,
            "home.exportLogbookBackupButton"
        )
    }
}
