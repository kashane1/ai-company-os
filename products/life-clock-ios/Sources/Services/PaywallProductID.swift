import Foundation

/// Typed product IDs. Must match the IDs configured in `Products.storekit`
/// (local testing) and the App Store Connect listing (production).
enum PaywallProductID: String, CaseIterable {
    case monthly = "com.lifeclock.pro.monthly"
    case annual = "com.lifeclock.pro.annual"
    case lifetime = "com.lifeclock.pro.lifetime"

    static var all: [String] { allCases.map(\.rawValue) }
}
