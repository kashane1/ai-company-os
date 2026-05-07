import Foundation
import Observation
import StoreKit

/// StoreKit 2 entitlement state. Single source of truth for "is this user
/// Pro?" — no UserDefaults cache, no off-store flag. Always answers from
/// `Transaction.currentEntitlements`.
///
/// `Transaction.updates` listener starts in `init` so transactions delivered
/// at launch (e.g. after reinstall) aren't lost.
@MainActor
@Observable
final class SubscriptionStore: EntitlementProviding {
    private(set) var products: [Product] = []
    private(set) var entitledProductIDs: Set<String> = []
    private(set) var purchaseInFlight: Bool = false
    private(set) var lastError: String?

    @ObservationIgnored private var updatesTask: Task<Void, Never>?

    var isPro: Bool { !entitledProductIDs.isEmpty }

    init() {
        updatesTask = Task.detached { [weak self] in
            for await result in Transaction.updates {
                await self?.handle(result)
            }
        }
    }

    deinit { updatesTask?.cancel() }

    // MARK: - Product loading

    func loadProducts() async {
        do {
            let loaded = try await Product.products(for: PaywallProductID.all)
            // Stable display order: annual first (recommended), monthly,
            // lifetime last.
            products = loaded.sorted { lhs, rhs in
                rank(lhs.id) < rank(rhs.id)
            }
            lastError = nil
        } catch {
            lastError = "Couldn't load subscription options: \(error.localizedDescription)"
        }
    }

    private func rank(_ id: String) -> Int {
        switch id {
        case PaywallProductID.annual.rawValue: return 0
        case PaywallProductID.monthly.rawValue: return 1
        case PaywallProductID.lifetime.rawValue: return 2
        default: return 99
        }
    }

    // MARK: - Purchase / restore

    func purchase(_ product: Product) async {
        purchaseInFlight = true
        defer { purchaseInFlight = false }
        do {
            let result = try await product.purchase()
            switch result {
            case .success(let verification):
                await handle(verification)
            case .userCancelled, .pending:
                break
            @unknown default:
                break
            }
        } catch {
            lastError = "Purchase failed: \(error.localizedDescription)"
        }
    }

    func restore() async {
        do {
            try await AppStore.sync()
            await refreshEntitlements()
        } catch {
            lastError = "Restore failed: \(error.localizedDescription)"
        }
    }

    // MARK: - Entitlement state

    func refreshEntitlements() async {
        #if targetEnvironment(simulator) && DEBUG
        // Dev-experience hatch: auto-grant Pro on simulator + Debug
        // builds so a manually-installed `.app` (no Xcode-attached
        // StoreKit configuration) doesn't pop the Apple-ID sign-in
        // sheet. The `.storekit` configuration only attaches when the
        // app is launched via Xcode's Run; standalone `simctl launch`
        // falls through to the production sandbox path. Set
        // `LIFECLOCK_SIMULATOR_PRO_DISABLED=1` in the environment to
        // exercise the real paywall flow on the simulator.
        let env = ProcessInfo.processInfo.environment
        if env["LIFECLOCK_SIMULATOR_PRO_DISABLED"] == nil {
            entitledProductIDs = [PaywallProductID.lifetime.rawValue]
            return
        }
        // Pro is explicitly disabled. Under XCUITest we want a deterministic
        // empty-entitlements state without iterating Transaction.current-
        // Entitlements, which has been seen to stall in test mode (the
        // sandbox StoreKit framework is configured per-scheme but hasn't
        // always finished warming up by the time .task fires). For human
        // simulator runs we still fall through to the real StoreKit path
        // so a manual purchase exercises the production code.
        if env["LIFECLOCK_UI_TEST"] == "1" {
            entitledProductIDs = []
            return
        }
        #endif
        var ids: Set<String> = []
        for await result in Transaction.currentEntitlements {
            if case .verified(let tx) = result, tx.revocationDate == nil {
                ids.insert(tx.productID)
            }
        }
        entitledProductIDs = ids
    }

    private func handle(_ result: VerificationResult<Transaction>) async {
        // Unverified transactions never grant entitlement — security.
        guard case .verified(let tx) = result else { return }
        await refreshEntitlements()
        // Required: unfinished transactions replay on every launch.
        await tx.finish()
    }
}
