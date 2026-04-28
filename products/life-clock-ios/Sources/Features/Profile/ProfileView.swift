import SwiftUI

struct ProfileView: View {
    @Environment(LifeClockStore.self) private var store

    var body: some View {
        NavigationStack {
            Form {
                Section("Tone") {
                    Picker("Tone mode", selection: Binding(
                        get: { store.toneMode },
                        set: { store.setToneMode($0) }
                    )) {
                        ForEach(ToneMode.allCases) { mode in
                            Text(mode.displayName).tag(mode)
                        }
                    }
                    Text(store.toneMode.description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section("Connected data") {
                    dataRow(name: "Apple Health — steps", status: "Not configured")
                    dataRow(name: "Apple Health — sleep", status: "Not configured")
                    dataRow(name: "Apple Health — heart rate", status: "Not configured")
                    Text("Live Apple Health reads land in a follow-up update. The current build uses sample data.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section("Privacy") {
                    Button("Export data") { /* placeholder */ }
                    Button("Delete data") { /* placeholder */ }
                    Button("Restore purchases") { /* placeholder */ }
                }

                Section("About") {
                    DisclaimerBanner()
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                    Text("\(LifeClockConfiguration.appName) · Version 0.1.0")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section {
                    Button("Reset onboarding (dev)") {
                        store.resetForOnboarding()
                    }
                    .foregroundStyle(.red)
                }
            }
            .navigationTitle("Profile")
        }
    }

    private func dataRow(name: String, status: String) -> some View {
        HStack {
            Text(name).font(.callout)
            Spacer()
            Text(status).font(.caption).foregroundStyle(.secondary)
        }
    }
}
