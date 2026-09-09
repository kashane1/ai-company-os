import XCTest
@testable import Catchbook

final class CatchPhotoLoaderTests: XCTestCase {
    func testResolveTreatsMissingOrEmptyPhotoDataAsUnavailable() {
        XCTAssertEqual(CatchPhotoLoader.resolve(data: nil), .unavailable)
        XCTAssertEqual(CatchPhotoLoader.resolve(data: Data()), .unavailable)
    }

    func testResolvePreservesLoadedPhotoData() {
        let data = Data([0xFF, 0xD8, 0xFF])

        XCTAssertEqual(CatchPhotoLoader.resolve(data: data), .loaded(data))
    }

    func testLoadMapsThrownSourceErrorToUnavailable() async {
        let result = await CatchPhotoLoader.load {
            throw TestError.unavailable
        }

        XCTAssertEqual(result, .unavailable)
    }

    func testLoadPreservesDataFromSource() async {
        let data = Data([0xFF, 0xD8, 0xFF])
        let result = await CatchPhotoLoader.load {
            data
        }

        XCTAssertEqual(result, .loaded(data))
    }

    private enum TestError: Error {
        case unavailable
    }
}
