import SwiftUI

/// A reusable keyboard toolbar that adds a "Done" button to dismiss the
/// keyboard. Needed because `.keyboardType(.decimalPad)` and multi-line
/// `TextField(axis: .vertical)` fields have no return key to resolve typing,
/// leaving users with no visible dismissal affordance.
///
/// Usage — the caller passes its own closure that clears focus, so the helper
/// stays agnostic of the caller's `@FocusState` enum type:
///
/// ```swift
/// .toolbar { KeyboardDoneToolbar { focusedField = nil } }
/// ```
struct KeyboardDoneToolbar: ToolbarContent {
    let onDone: () -> Void

    var body: some ToolbarContent {
        ToolbarItemGroup(placement: .keyboard) {
            Spacer()
            Button("Done", action: onDone)
        }
    }
}
