import SwiftUI

struct CatchFieldVisibilityEditor: View {
    @Binding var storedVisibleFields: String

    private var visibleFields: Set<CatchOptionalField> {
        CatchOptionalField.fields(from: storedVisibleFields)
    }

    var body: some View {
        DisclosureGroup("Visible Fields") {
            ForEach(CatchOptionalField.allCases) { field in
                Toggle(field.label, isOn: binding(for: field))
            }
        }
    }

    private func binding(for field: CatchOptionalField) -> Binding<Bool> {
        Binding(
            get: { visibleFields.contains(field) },
            set: { isVisible in
                var next = visibleFields
                if isVisible {
                    next.insert(field)
                } else {
                    next.remove(field)
                }
                storedVisibleFields = CatchOptionalField.storedValue(for: next)
            }
        )
    }
}
