import SwiftUI

struct ActivityView: View {
    @EnvironmentObject private var store: AfterPlansStore

    var body: some View {
        List {
            Section {
                Text("Activity is for live and recent after-plans. It is not a chat inbox.")
                    .foregroundStyle(.secondary)
            }

            Section("Live now") {
                if store.livePlans.isEmpty {
                    Text("Nothing live yet.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(store.livePlans) { plan in
                        NavigationLink {
                            PlanDetailView(planID: plan.id)
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(plan.title)
                                Text("\(plan.lifecycle.title) · \(plan.contextTitle)")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }

            Section("Recent") {
                if store.historyPlans.isEmpty {
                    Text("Closed plans will appear here once the loop is running.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(store.historyPlans) { plan in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(plan.title)
                            Text("\(plan.contextTitle) · \(plan.venueLabel)")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
        .navigationTitle("Activity")
    }
}
