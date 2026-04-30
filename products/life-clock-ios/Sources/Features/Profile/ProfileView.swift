import SwiftUI

struct ProfileView: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(SubscriptionStore.self) private var subscriptions
    @State private var requestingAuth: Bool = false
    @State private var restoring: Bool = false
    @State private var paywallPresented: Bool = false
    @State private var safetyNetPresented: Bool = false

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

                Section("Appearance") {
                    Picker("Color palette", selection: Binding(
                        get: { store.palette },
                        set: { store.setPalette($0) }
                    )) {
                        ForEach(LifeClockPalette.allCases) { palette in
                            HStack {
                                Circle()
                                    .fill(palette.accent)
                                    .frame(width: 16, height: 16)
                                Text(palette.displayName)
                            }
                            .tag(palette)
                        }
                    }
                }

                Section {
                    Toggle("Daily reminder", isOn: Binding(
                        get: { store.profile?.dailyReminderEnabled ?? false },
                        set: { newValue in
                            Task {
                                await store.setDailyReminder(
                                    enabled: newValue,
                                    hour: store.profile?.dailyReminderHour ?? 20
                                )
                            }
                        }
                    ))

                    if store.profile?.dailyReminderEnabled == true {
                        Picker("Time", selection: Binding(
                            get: { store.profile?.dailyReminderHour ?? 20 },
                            set: { newHour in
                                Task {
                                    await store.setDailyReminder(enabled: true, hour: newHour)
                                }
                            }
                        )) {
                            ForEach(8...22, id: \.self) { hour in
                                Text(reminderHourLabel(hour)).tag(hour)
                            }
                        }
                    }
                } header: {
                    Text("Daily reminder")
                } footer: {
                    Text(reminderFooterText)
                        .font(.caption)
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
                        Text(LifeClockConfiguration.healthKitRationale)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    } else {
                        let signal = store.hasTodaySignal ? "Available" : "No data today"
                        dataRow(name: "Apple Health (steps, sleep, exercise, resting HR)", status: signal)
                        Text("If \"No data\" persists, open iOS Settings → Health → Data Access & Devices → Life Clock to review what's shared.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    if let error = store.lastHealthAuthError {
                        Text(error)
                            .font(.caption)
                            .foregroundStyle(.red)
                    }
                }

                Section("Subscription") {
                    if subscriptions.isPro {
                        HStack {
                            Image(systemName: "checkmark.seal.fill").foregroundStyle(.tint)
                            Text(LifeClockConfiguration.proName)
                            Spacer()
                            Text("Active").foregroundStyle(.secondary).font(.caption)
                        }
                    } else {
                        Button("Upgrade to Pro") {
                            paywallPresented = true
                        }
                    }
                    Button {
                        restorePurchases()
                    } label: {
                        HStack {
                            Text("Restore purchases")
                            if restoring { ProgressView() }
                        }
                    }
                    .disabled(restoring)
                }

                Section("Privacy") {
                    Button("Export data") { /* placeholder — separate plan */ }
                    Button("Delete all data", role: .destructive) {
                        store.resetForOnboarding()
                    }
                }

                Section {
                    Button {
                        safetyNetPresented = true
                    } label: {
                        HStack {
                            Image(systemName: "heart.text.square")
                            Text("If this app is making you anxious")
                        }
                    }
                } footer: {
                    Text("Switch to Gentle tone, hide the clock, or get crisis-resource phone numbers. Always available — no questions asked.")
                        .font(.caption)
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
            .sheet(isPresented: $paywallPresented) {
                PaywallSheet()
            }
            .sheet(isPresented: $safetyNetPresented) {
                SafetyNetView()
            }
        }
    }

    private func restorePurchases() {
        restoring = true
        Task {
            await subscriptions.restore()
            restoring = false
        }
    }

    private func dataRow(name: String, status: String) -> some View {
        HStack {
            Text(name).font(.callout)
            Spacer()
            Text(status).font(.caption).foregroundStyle(.secondary)
        }
    }

    private var reminderFooterText: String {
        if store.notificationAuthorizationStatus == .denied,
           store.profile?.dailyReminderEnabled == true {
            return "Notifications are disabled in iOS Settings → Life Clock. Re-enable there to receive reminders."
        }
        return "We'll remind you to log if you haven't already by this time. One per day. Reminder time runs between 8 AM and 10 PM."
    }

    private func reminderHourLabel(_ hour: Int) -> String {
        switch hour {
        case 0: return "12 AM"
        case 12: return "12 PM"
        case 1...11: return "\(hour) AM"
        default: return "\(hour - 12) PM"
        }
    }

    private func connectAppleHealth() {
        requestingAuth = true
        Task {
            await store.requestHealthAuthorization()
            requestingAuth = false
        }
    }
}
