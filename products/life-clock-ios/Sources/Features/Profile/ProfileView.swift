import SwiftUI

struct ProfileView: View {
    @Environment(LifeClockStore.self) private var store
    @State private var requestingAuth: Bool = false

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

                Section("Apple Health") {
                    if !store.healthDataAvailable {
                        Text("Apple Health is not available on this device.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    } else if !store.healthAuthorizationKnown {
                        Button {
                            connectAppleHealth()
                        } label: {
                            HStack {
                                Text("Connect Apple Health")
                                if requestingAuth { ProgressView() }
                            }
                        }
                        .disabled(requestingAuth)
                        Text("Life Clock asks for steps, sleep, exercise minutes, and resting heart rate. You control which data types are shared.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    } else {
                        dataRow(name: "Steps", status: status(for: store.todayDrivers.contains { $0.driverType == "movement" }))
                        dataRow(name: "Sleep", status: status(for: store.todayDrivers.contains { $0.driverType == "sleep" }))
                        dataRow(name: "Exercise minutes", status: status(for: store.todayDrivers.contains { $0.driverType == "exercise" }))
                        Text("If a row reads \"No data\", open iOS Settings → Health → Data Access & Devices → Life Clock to review what's shared.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Section("Privacy") {
                    Button("Export data") { /* placeholder — lands with persistence plan */ }
                    Button("Delete data") { /* placeholder — lands with persistence plan */ }
                    Button("Restore purchases") { /* placeholder — lands with paywall plan */ }
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

    private func status(for hasData: Bool) -> String {
        // Honest: we don't know "denied" vs "no data" for read scopes.
        hasData ? "Available" : "No data"
    }

    private func connectAppleHealth() {
        requestingAuth = true
        Task {
            await store.requestHealthAuthorization()
            requestingAuth = false
        }
    }
}
