import XCTest
import StoreKit
import StoreKitTest
@testable import LifeClock

@MainActor
final class SubscriptionStoreTests: XCTestCase {
    var session: SKTestSession!

    override func setUp() async throws {
        session = try SKTestSession(configurationFileNamed: "Products")
        session.resetToDefaultState()
        session.disableDialogs = true
        session.clearTransactions()
    }

    /// iOS 26.3+ simulator: SKTestSession's internal config save fails with
    /// `SKInternalErrorDomain Code=3`, so `session.buyProduct(identifier:)`
    /// falls through to "off-device buy mode" and throws
    /// `StoreKitError.notEntitled`. The .storekit configuration is correctly
    /// attached to the test action; the failure is in the simulator's StoreKit
    /// subsystem, not in our wiring (see flutter/flutter#184678 for an
    /// independent repro). Re-enable once Apple ships a fix.
    private func skipIfStoreKitTestSessionBroken() throws {
        let os = ProcessInfo.processInfo.operatingSystemVersion
        if os.majorVersion >= 26 {
            throw XCTSkip("SKTestSession.buyProduct broken on iOS \(os.majorVersion).\(os.minorVersion) simulator — Apple bug, tracked in flutter/flutter#184678")
        }
    }

    override func tearDown() async throws {
        session = nil
    }

    func testLoadProductsReturnsAllThreeTiers() async {
        let store = SubscriptionStore()
        await store.loadProducts()
        let ids = Set(store.products.map(\.id))
        XCTAssertTrue(ids.contains(PaywallProductID.monthly.rawValue))
        XCTAssertTrue(ids.contains(PaywallProductID.annual.rawValue))
        XCTAssertTrue(ids.contains(PaywallProductID.lifetime.rawValue))
    }

    func testProductsSortedAnnualFirstThenMonthlyThenLifetime() async {
        let store = SubscriptionStore()
        await store.loadProducts()
        let ordered = store.products.map(\.id)
        XCTAssertEqual(ordered.first, PaywallProductID.annual.rawValue)
        XCTAssertEqual(ordered.last, PaywallProductID.lifetime.rawValue)
    }

    func testPurchaseGrantsProEntitlement() async throws {
        try skipIfStoreKitTestSessionBroken()
        let store = SubscriptionStore()
        await store.loadProducts()
        XCTAssertFalse(store.isPro)

        _ = try await session.buyProduct(identifier: PaywallProductID.annual.rawValue)
        // Allow Transaction.updates to deliver.
        try await Task.sleep(for: .milliseconds(500))
        await store.refreshEntitlements()

        XCTAssertTrue(store.isPro)
        XCTAssertTrue(store.entitledProductIDs.contains(PaywallProductID.annual.rawValue))
    }

    func testRestoreRefreshesEntitlements() async throws {
        try skipIfStoreKitTestSessionBroken()
        _ = try await session.buyProduct(identifier: PaywallProductID.lifetime.rawValue)
        try await Task.sleep(for: .milliseconds(200))

        // Fresh store reads entitlements at construction time.
        let store = SubscriptionStore()
        await store.loadProducts()
        await store.refreshEntitlements()
        XCTAssertTrue(store.isPro)
    }

    func testRevocationViaRefundClearsEntitlement() async throws {
        try skipIfStoreKitTestSessionBroken()
        let store = SubscriptionStore()
        await store.loadProducts()

        let transaction = try await session.buyProduct(identifier: PaywallProductID.monthly.rawValue)
        try await Task.sleep(for: .milliseconds(200))
        await store.refreshEntitlements()
        XCTAssertTrue(store.isPro)

        try session.refundTransaction(identifier: UInt(transaction.id))
        try await Task.sleep(for: .milliseconds(300))
        await store.refreshEntitlements()
        XCTAssertFalse(store.isPro, "Refunded transactions must not grant entitlement")
    }
}
