import XCTest
@testable import Catchbook

final class CatchLoggingPreferencesTests: XCTestCase {
    func testCatchOptionalFieldsFallbackToDefaultsWhenStorageIsEmpty() {
        XCTAssertEqual(
            CatchOptionalField.fields(from: ""),
            CatchOptionalField.defaultFields
        )
    }

    func testCatchOptionalFieldsRoundTripThroughStoredValue() {
        let fields: Set<CatchOptionalField> = [.gear, .note, .photo]
        let stored = CatchOptionalField.storedValue(for: fields)

        XCTAssertEqual(CatchOptionalField.fields(from: stored), fields)
    }
}
