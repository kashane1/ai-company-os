import XCTest
@testable import Catchbook

final class CatchPhotoMigrationServiceTests: XCTestCase {
    func testDraftsPreferCatchPhotoRecordsOverLegacyPhotoData() {
        let catchRecord = CatchRecord(species: "Bass", trip: nil, photoData: Data([0x01]))
        let extraPhoto = CatchPhoto(
            catchRecord: catchRecord,
            sortOrder: 0,
            photoContentType: "image/jpeg",
            photoData: Data([0x02, 0x03])
        )
        catchRecord.photos = [extraPhoto]

        let drafts = CatchPhotoMigrationService.drafts(for: catchRecord)

        XCTAssertEqual(drafts.count, 1)
        XCTAssertEqual(drafts.first?.data, Data([0x02, 0x03]))
    }

    func testSyncWritesPhotosAndLegacyHeroFields() throws {
        let store = try ModelTestSupport.makeStore()
        let catchRecord = CatchRecord(species: "Bass", trip: nil)
        store.context.insert(catchRecord)

        CatchPhotoMigrationService.sync(
            record: catchRecord,
            drafts: [
                CatchPhotoDraft(data: Data([0x01]), contentType: "image/jpeg"),
                CatchPhotoDraft(data: Data([0x02]), contentType: "image/jpeg"),
            ],
            in: store.context
        )

        XCTAssertEqual(catchRecord.photos.count, 2)
        XCTAssertEqual(catchRecord.primaryPhotoData, Data([0x01]))
        XCTAssertEqual(catchRecord.photoCount, 2)
        XCTAssertEqual(catchRecord.photoData, Data([0x01]))
    }
}
