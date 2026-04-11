import XCTest
@testable import Catchbook

final class LocaleDecimalParserTests: XCTestCase {
    func testEnUSParsesDotSeparator() {
        let locale = Locale(identifier: "en_US")
        XCTAssertEqual(LocaleDecimalParser.parse("1.5", locale: locale), 1.5)
        XCTAssertEqual(LocaleDecimalParser.parse("42", locale: locale), 42)
        XCTAssertEqual(LocaleDecimalParser.parse("0.25", locale: locale), 0.25)
    }

    func testDeDEParsesCommaSeparator() {
        let locale = Locale(identifier: "de_DE")
        XCTAssertEqual(LocaleDecimalParser.parse("1,5", locale: locale), 1.5)
        XCTAssertEqual(LocaleDecimalParser.parse("42", locale: locale), 42)
        XCTAssertEqual(LocaleDecimalParser.parse("0,25", locale: locale), 0.25)
    }

    func testFrFRParsesCommaSeparator() {
        let locale = Locale(identifier: "fr_FR")
        XCTAssertEqual(LocaleDecimalParser.parse("1,5", locale: locale), 1.5)
        XCTAssertEqual(LocaleDecimalParser.parse("3,14", locale: locale), 3.14)
    }

    func testCrossLocaleFallbackAcceptsPosixDot() {
        let locale = Locale(identifier: "de_DE")
        // User typed "1.5" on a hardware keyboard even though their locale
        // expects "1,5" — fallback should still parse it.
        XCTAssertEqual(LocaleDecimalParser.parse("1.5", locale: locale), 1.5)
    }

    func testEmptyAndWhitespaceReturnNil() {
        XCTAssertNil(LocaleDecimalParser.parse(""))
        XCTAssertNil(LocaleDecimalParser.parse("   "))
    }

    func testGarbageInputReturnsNil() {
        XCTAssertNil(LocaleDecimalParser.parse("abc"))
        XCTAssertNil(LocaleDecimalParser.parse("1..5"))
    }
}
