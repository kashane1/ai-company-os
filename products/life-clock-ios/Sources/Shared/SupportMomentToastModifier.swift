import SwiftUI

/// Attaches the top-anchored `SupportMomentToast` overlay to any view
/// (typically each tab's `ScrollView` or `Form`, inside its
/// `NavigationStack`). Applying the modifier per-tab keeps the toast
/// visually anchored just below THAT tab's navigation bar, matching the
/// "doubles the height of the top bar" placement chosen for Today.
///
/// The store's `supportMoment` is observed inside the modifier so the
/// overlay re-renders on intent emit/dismiss across every tab. The
/// `.task(id:)` inside `SupportMomentToast` handles the 3.5s
/// auto-dismiss and replace-and-reset on new moments.
private struct SupportMomentToastModifier: ViewModifier {
    @Environment(LifeClockStore.self) private var store
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        content
            .overlay(alignment: .top) {
                if let moment = store.supportMoment {
                    SupportMomentToast(
                        moment: moment,
                        dismissAction: store.dismissSupportMoment
                    )
                    // Reduce Motion: no slide-down; cross-fade only.
                    .transition(
                        reduceMotion
                            ? .opacity
                            : .move(edge: .top).combined(with: .opacity)
                    )
                    .zIndex(1)
                }
            }
            .animation(
                reduceMotion
                    ? nil
                    : .spring(response: 0.42, dampingFraction: 0.86),
                value: store.supportMoment
            )
    }
}

extension View {
    /// Attach the top-anchored support-moment toast overlay. Apply on
    /// each top-level tab content (Today/History/Future/Profile) so a
    /// moment fired while ANY tab is active surfaces consistently under
    /// the active nav bar.
    func supportMomentToast() -> some View {
        modifier(SupportMomentToastModifier())
    }
}
