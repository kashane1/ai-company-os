import SwiftUI

struct SafetyCenterView: View {
    @EnvironmentObject private var store: AfterPlansStore
    let focusedPlanID: UUID?

    var body: some View {
        List {
            Section {
                Text("Safety stays visible in the shell because After Plans should feel bounded and human from the start, not anonymous or random.")
                    .foregroundStyle(.secondary)
            }

            if let focusedPlanID, let plan = store.plan(with: focusedPlanID) {
                Section("Current plan") {
                    Text(plan.title)
                    Button("Report this plan") {
                        store.reportPlan(plan)
                    }
                    Button("Report host: \(plan.hostName)") {
                        store.reportUser(named: plan.hostName)
                    }
                    Button("Block host: \(plan.hostName)", role: .destructive) {
                        store.blockUser(named: plan.hostName)
                    }
                }
            }

            Section("Report reasons") {
                ForEach(store.reportReasons) { reason in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(reason.title)
                        Text(reason.explanation)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Section("Moderation posture") {
                Text(store.moderationNote)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if !store.reportLog.isEmpty {
                Section("Recent safety actions") {
                    ForEach(store.reportLog.reversed(), id: \.self) { item in
                        Text(item)
                    }
                }
            }
        }
        .navigationTitle("Safety Center")
    }
}
