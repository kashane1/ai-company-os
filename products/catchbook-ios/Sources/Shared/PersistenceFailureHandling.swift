import SwiftUI

enum PersistenceWriteCoordinator {
    static let defaultUserMessage = "We couldn't save your changes right now."

    static func perform(
        userMessage: String = defaultUserMessage,
        commit: () throws -> Void,
        rollback: () -> Void = {},
        onSuccess: () -> Void,
        onFailure: (String) -> Void
    ) {
        do {
            try commit()
            onSuccess()
        } catch {
            rollback()
            onFailure(userMessage)
        }
    }
}

extension View {
    func persistenceFailureAlert(
        title: String = "Save failed",
        message: Binding<String?>
    ) -> some View {
        alert(title, isPresented: Binding(
            get: { message.wrappedValue != nil },
            set: { isPresented in
                if !isPresented {
                    message.wrappedValue = nil
                }
            }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(message.wrappedValue ?? PersistenceWriteCoordinator.defaultUserMessage)
        }
    }
}
