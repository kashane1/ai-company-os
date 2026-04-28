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
                Section("Alcohol today") {
                    Picker("Alcohol", selection: $alcoholLevel) {
                        Text("None").tag("none")
                        Text("Light").tag("light")
                        Text("Heavy").tag("heavy")
                    }
                    .pickerStyle(.segmented)
                }
                Section("Smoking / vaping today") {
                    Toggle("Logged today", isOn: $smokingVaping)
                }
                Section("Diet today") {
                    Picker("Diet", selection: $dietQuality) {
                        Text("Great").tag("great")
                        Text("Okay").tag("okay")
                        Text("Rough").tag("rough")
                    }
                    .pickerStyle(.segmented)
                }
                Section("Stress today") {
                    Picker("Stress", selection: $stressLevel) {
                        Text("Low").tag("low")
                        Text("Medium").tag("medium")
                        Text("High").tag("high")
                    }
                    .pickerStyle(.segmented)
                }
                Section("Strength training") {
                    Toggle("Completed today", isOn: $strengthTraining)
                }
                Section {
                    DisclaimerBanner()
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                }
            }
            .navigationTitle("Quick log")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        save()
                    } label: {
                        if saving { ProgressView() } else { Text("Save") }
                    }
                    .disabled(saving)
                }
            }
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
}
