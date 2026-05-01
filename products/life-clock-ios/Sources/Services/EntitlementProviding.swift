import Foundation

/// Application-layer entitlement source. Decouples `LifeClockStore` from
/// `SubscriptionStore` so the override gate can be unit-tested with a
/// trivial mock conformance and the store doesn't carry a SubscriptionStore
/// reference for what is policy, not state.
///
/// `SubscriptionStore` conforms in production. Tests pass a mock that
/// returns whatever isPro the case under test needs.
protocol EntitlementProviding: AnyObject {
    var isPro: Bool { get }
}

extension EntitlementProviding where Self == NeverEntitled {
    static var never: NeverEntitled { NeverEntitled() }
}

/// Trivial conformance returning `false`. Useful as a safe default in
/// codepaths that haven't been wired to the live SubscriptionStore yet.
final class NeverEntitled: EntitlementProviding {
    var isPro: Bool { false }
}
