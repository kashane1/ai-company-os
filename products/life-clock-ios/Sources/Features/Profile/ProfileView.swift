import SwiftUI

struct ProfileView: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(SubscriptionStore.self) private var subscriptions
    @State private var requestingAuth: Bool = false
    @State private var restoring: Bool = false
    @State private var paywallPresented: Bool = false
    @State private var safetyNetPresented: Bool = false
    @State private var bodyUnitSystem: BodyMeasurementSystem = .standard

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
                    // .menu keeps the selection on its own line as a
                    // dropdown trigger instead of letting the in-row
                    // trailing text truncate ("Defaul...erage" caught
                    // 2026-05-06 axxl recon).
                    .pickerStyle(.menu)
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

                completionBadgesSection

                bodyMetricsSection

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
                        // DatePicker handles 12/24-hour locales automatically.
                        // Store-side clamp (8…22) is the source of truth for the
                        // valid range — the picker UI lets the user select any
                        // hour, but `setDailyReminder` rounds into the window.
                        DatePicker(
                            "Time",
                            selection: Binding(
                                get: {
                                    let hour = store.profile?.dailyReminderHour ?? 20
                                    return store.clock.calendar.date(
                                        bySettingHour: hour, minute: 0, second: 0,
                                        of: store.clock.now()
                                    ) ?? store.clock.now()
                                },
                                set: { newDate in
                                    let hour = store.clock.calendar.component(.hour, from: newDate)
                                    Task {
                                        await store.setDailyReminder(enabled: true, hour: hour)
                                    }
                                }
                            ),
                            displayedComponents: .hourAndMinute
                        )
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
                        let signal = store.hasTodaySignal ? "Data available today" : "No data today"
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
                        .accessibilityIdentifier("profile.upgrade")
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
                    .accessibilityIdentifier("profile.restore")
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

    @ViewBuilder
    private var bodyMetricsSection: some View {
        Section("Height & weight") {
            Toggle("Include height & weight", isOn: Binding(
                get: { store.profile?.heightCm != nil && store.profile?.weightKg != nil },
                set: { enabled in
                    if enabled {
                        store.setBodyMetrics(
                            heightCm: store.profile?.heightCm ?? 170,
                            weightKg: store.profile?.weightKg ?? 70
                        )
                    } else {
                        store.setBodyMetrics(heightCm: nil, weightKg: nil)
                    }
                }
            ))

            if store.profile?.heightCm != nil && store.profile?.weightKg != nil {
                Picker("Unit system", selection: $bodyUnitSystem) {
                    ForEach(BodyMeasurementSystem.allCases) { system in
                        Text(system.displayName).tag(system)
                    }
                }
                .pickerStyle(.segmented)

                switch bodyUnitSystem {
                case .standard:
                    Stepper(
                        "Height: \(profileFeet) ft \(profileInches) in",
                        value: profileFeetBinding,
                        in: 3...7
                    )
                    Stepper("Inches: \(profileInches)", value: profileInchesBinding, in: 0...11)
                    Stepper("Weight: \(profilePounds) lb", value: profilePoundsBinding, in: 66...440)
                case .metric:
                    Stepper("Height: \(Int(profileHeightCm.rounded())) cm", value: profileHeightCmBinding, in: 120...220)
                    Stepper("Weight: \(Int(profileWeightKg.rounded())) kg", value: profileWeightKgBinding, in: 30...200)
                }
            }
        }
    }

    private var profileHeightCm: Double {
        store.profile?.heightCm ?? 170
    }

    private var profileWeightKg: Double {
        store.profile?.weightKg ?? 70
    }

    private var profileFeet: Int {
        max(3, min(7, Int((profileHeightCm / 2.54).rounded()) / 12))
    }

    private var profileInches: Int {
        max(0, min(11, Int((profileHeightCm / 2.54).rounded()) % 12))
    }

    private var profilePounds: Int {
        Int((profileWeightKg * 2.20462).rounded())
    }

    private var profileHeightCmBinding: Binding<Double> {
        Binding(
            get: { profileHeightCm },
            set: { store.setBodyMetrics(heightCm: $0, weightKg: profileWeightKg) }
        )
    }

    private var profileWeightKgBinding: Binding<Double> {
        Binding(
            get: { profileWeightKg },
            set: { store.setBodyMetrics(heightCm: profileHeightCm, weightKg: $0) }
        )
    }

    private var profileFeetBinding: Binding<Int> {
        Binding(
            get: { profileFeet },
            set: { newFeet in
                let nextHeight = Double(newFeet * 12 + profileInches) * 2.54
                store.setBodyMetrics(heightCm: nextHeight, weightKg: profileWeightKg)
            }
        )
    }

    private var profileInchesBinding: Binding<Int> {
        Binding(
            get: { profileInches },
            set: { newInches in
                let nextHeight = Double(profileFeet * 12 + newInches) * 2.54
                store.setBodyMetrics(heightCm: nextHeight, weightKg: profileWeightKg)
            }
        )
    }

    private var profilePoundsBinding: Binding<Int> {
        Binding(
            get: { profilePounds },
            set: { store.setBodyMetrics(heightCm: profileHeightCm, weightKg: Double($0) / 2.20462) }
        )
    }

    @ViewBuilder
    private var completionBadgesSection: some View {
        Section("Completion badges") {
            let badges = store.completionBadges()
            let earned = badges.filter { $0.isUnlocked }
            let locked = badges.filter { !$0.isUnlocked }

            HStack {
                Label("\(earned.count)", systemImage: "seal.fill")
                    .foregroundStyle(.tint)
                Text("earned")
                    .foregroundStyle(.secondary)
                Spacer()
                Text("\(badges.count) possible")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .accessibilityIdentifier("profile.badges.summary")

            if earned.isEmpty {
                Text("No badges earned yet.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(earned) { badge in
                    badgeRow(badge)
                }
            }

            DisclosureGroup("Locked") {
                ForEach(locked) { badge in
                    badgeRow(badge)
                }
            }
        }
    }

    private func badgeRow(_ badge: CompletionBadge) -> some View {
        HStack(alignment: .top, spacing: DesignTokens.Spacing.sm) {
            Image(systemName: badge.systemImage)
                .font(.title3)
                .foregroundStyle(badge.isUnlocked ? tierTint(for: badge.tier) : .secondary)
                .frame(width: 28)

            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                HStack(alignment: .firstTextBaseline) {
                    Text(badge.title)
                        .font(.callout.bold())
                    Spacer()
                    Text(badge.category.displayName)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Text(badge.detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                if badge.isUnlocked {
                    Label("Earned", systemImage: "checkmark.seal.fill")
                        .font(.caption)
                        .foregroundStyle(tierTint(for: badge.tier))
                } else {
                    ProgressView(value: badge.progressFraction) {
                        Text(badge.progressText)
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .accessibilityIdentifier("profile.badge.\(badge.id)")
    }

    private func tierTint(for tier: CompletionBadge.Tier) -> Color {
        switch tier {
        case .starter:
            return .blue
        case .bronze:
            return .brown
        case .silver:
            return .gray
        case .gold:
            return .yellow
        case .platinum:
            return .purple
        }
    }

    private var reminderFooterText: String {
        if store.notificationAuthorizationStatus == .denied,
           store.profile?.dailyReminderEnabled == true {
            return "Notifications are disabled in iOS Settings → Life Clock. Re-enable there to receive reminders."
        }
        return "We'll remind you to log if you haven't already by this time. One per day. Reminder time runs between 8 AM and 10 PM."
    }

    private func connectAppleHealth() {
        requestingAuth = true
        Task {
            await store.requestHealthAuthorization()
            requestingAuth = false
        }
    }
}
