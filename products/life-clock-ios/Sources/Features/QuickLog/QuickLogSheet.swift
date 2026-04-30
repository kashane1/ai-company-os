import SwiftUI

/// Today-screen quick-log entry. Captures the manual habit signals the
/// founder pack calls out (alcohol, smoking/vaping, diet quality, stress,
/// strength training) and feeds them to the engine via
/// `store.setTodayHabits(_:)`. Coarse on purpose — fast to log.
struct QuickLogSheet: View {
    @Environment(LifeClockStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    @State private var alcoholLevel: String = "none"
    @State private var smokingVaping: Bool = false
    @State private var dietQuality: String = "okay"
    @State private var stressLevel: String = "medium"
    @State private var strengthTraining: Bool = false
    @State private var saving: Bool = false

    var body: some View {
        NavigationStack {
            Form {
                if store.isAdultUser {
                    Section("Alcohol today") {
                        Picker("Alcohol", selection: $alcoholLevel) {
                            Text("None").tag("none")
                            Text("Light").tag("light")
                            Text("Heavy").tag("heavy")
                        }
                        .pickerStyle(.segmented)
                        .accessibilityIdentifier("quickLog.alcoholLevel")
                        .accessibilityValue(alcoholLevel)
                    }
                    Section("Smoking / vaping today") {
                        Toggle("Logged today", isOn: $smokingVaping)
                            .accessibilityIdentifier("quickLog.smokingVaping")
                    }
                }
                Section {
                    Picker("Diet quality today", selection: $dietQuality) {
                        Text("Great").tag("great")
                        Text("Okay").tag("okay")
                        Text("Rough").tag("rough")
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("quickLog.dietQuality")
                    .accessibilityValue(dietQuality)
                    Text("Coarse on purpose. No calorie counting. Diet quality is one of the clearest signals in your daily progress.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } header: {
                    Text("How did food go today?")
                }
                Section("Stress today") {
                    Picker("Stress", selection: $stressLevel) {
                        Text("Low").tag("low")
                        Text("Medium").tag("medium")
                        Text("High").tag("high")
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("quickLog.stressLevel")
                    .accessibilityValue(stressLevel)
                }
                Section("Strength training") {
                    Toggle("Completed today", isOn: $strengthTraining)
                        .accessibilityIdentifier("quickLog.strengthTraining")
                }
                if store.todayHabits != nil {
                    Section {
                        Button(role: .destructive) {
                            clear()
                        } label: {
                            Text("Clear today's log")
                                .frame(maxWidth: .infinity, alignment: .center)
                        }
                        .disabled(saving)
                    } footer: {
                        Text("Removes today's quick-log entry. Use this if you mis-tapped — your engine result will recompute from HealthKit signals only.")
                    }
                }
                Section {
                    DisclaimerBanner()
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                }
            }
            .navigationTitle("Daily check-in")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .accessibilityIdentifier("checkIn.cancel")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        save()
                    } label: {
                        if saving { ProgressView() } else { Text("Save") }
                    }
                    .disabled(saving)
                    .accessibilityIdentifier("checkIn.save")
                }
            }
            .accessibilityIdentifier("checkIn.screen")
        }
        .onAppear { hydrateFromStore() }
    }

    private func hydrateFromStore() {
        guard let existing = store.todayHabits else { return }
        alcoholLevel = existing.alcoholLevel
        smokingVaping = existing.smokingVaping
        dietQuality = existing.dietQuality
        stressLevel = existing.stressLevel
        strengthTraining = existing.strengthTraining
    }

    private func save() {
        saving = true
        Task {
            let habits = HabitLog(date: store.clock.calendar.startOfDay(for: store.clock.now()))
            habits.alcoholLevel = alcoholLevel
            habits.smokingVaping = smokingVaping
            habits.dietQuality = dietQuality
            habits.stressLevel = stressLevel
            habits.strengthTraining = strengthTraining
            await store.setTodayHabits(habits)
            saving = false
            dismiss()
        }
    }

    private func clear() {
        saving = true
        Task {
            await store.clearTodayHabits()
            saving = false
            dismiss()
        }
    }
}
