import Foundation

/// Typed product IDs. Must match the IDs configured in `Products.storekit`
/// (local testing) and the App Store Connect listing (production).
enum PaywallProductID: String, CaseIterable {
    case monthly = "com.life-clock.pro.monthly"
    case annual = "com.life-clock.pro.annual"
    case lifetime = "com.life-clock.pro.lifetime"

    static var all: [String] { allCases.map(\.rawValue) }
}
