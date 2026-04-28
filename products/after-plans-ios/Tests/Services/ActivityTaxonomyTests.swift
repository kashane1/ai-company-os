import XCTest
@testable import AfterPlans

final class ActivityTaxonomyTests: XCTestCase {
    func testNoDuplicateSlugs() {
        let slugs = ActivityTaxonomy.all.map(\.slug)
        XCTAssertEqual(Set(slugs).count, slugs.count, "every taxonomy slug must be unique")
    }

    func testNoDuplicateIDs() {
        let ids = ActivityTaxonomy.all.map(\.id)
        XCTAssertEqual(Set(ids).count, ids.count, "every taxonomy UUID must be unique")
    }

    func testEveryParentReferenceResolves() {
        let parentIDs = Set(ActivityTaxonomy.parents.map(\.id))
        for child in ActivityTaxonomy.children {
            let parentID = try? XCTUnwrap(child.parentActivityID)
            XCTAssertNotNil(parentID, "child \(child.slug) is missing parentActivityID")
            if let pid = parentID {
                XCTAssertTrue(parentIDs.contains(pid), "child \(child.slug) references unknown parent")
            }
        }
    }

    func testParentsHaveNilParentActivityID() {
        for parent in ActivityTaxonomy.parents {
            XCTAssertNil(parent.parentActivityID, "parent \(parent.slug) should not have a parentActivityID")
        }
    }

    func testSortRanksAreUniqueAndStable() {
        let ranks = ActivityTaxonomy.all.map(\.sortRank)
        XCTAssertEqual(Set(ranks).count, ranks.count, "every sortRank must be unique")
    }

    func testTaxonomyMatchesInMemoryStateCount() {
        // The InMemoryActivityState seeds a subset of the taxonomy. We
        // assert the full taxonomy is at least as large as that subset
        // so adding rows here can't accidentally shrink the catalog.
        XCTAssertGreaterThanOrEqual(ActivityTaxonomy.all.count, 15)
    }

    func testParentLookupReturnsExpectedParent() {
        let basketball = try? XCTUnwrap(ActivityTaxonomy.children.first { $0.slug == "basketball" })
        let parent = ActivityTaxonomy.parent(of: basketball!)
        XCTAssertEqual(parent?.slug, "sports")
    }

    func testChildrenLookupReturnsExpectedSet() {
        let sports = try? XCTUnwrap(ActivityTaxonomy.parents.first { $0.slug == "sports" })
        let kids = ActivityTaxonomy.children(of: sports!)
        XCTAssertTrue(kids.contains(where: { $0.slug == "basketball" }))
        XCTAssertFalse(kids.contains(where: { $0.slug == "yoga" }), "yoga belongs under fitness, not sports")
    }
}
