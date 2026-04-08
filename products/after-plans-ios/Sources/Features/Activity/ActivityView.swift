import SwiftUI

struct ActivityView: View {
    @EnvironmentObject private var store: AfterPlansStore

    var body: some View {
        List {
            Section("Live now") {
                if store.livePlans.isEmpty {
                    Label("Nothing live right now.", systemImage: "moon")
                        .foregroundStyle(.secondary)
                        .font(.subheadline)
                } else {
                    ForEach(store.livePlans) { plan in
                        NavigationLink {
                            PlanDetailView(planID: plan.id)
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(plan.title)
                                        .font(.headline)
                                    Text(plan.contextTitle)
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                LifecycleBadgeView(lifecycle: plan.lifecycle)
                            }
                            .padding(.vertical, 2)
                        }
                    }
                }
            }

            Section("Recent") {
                if store.historyPlans.isEmpty {
                    Label("Closed plans will appear here.", systemImage: "clock.arrow.circlepath")
                        .foregroundStyle(.secondary)
                        .font(.subheadline)
                } else {
                    ForEach(store.historyPlans) { plan in
                        NavigationLink {
                            PlanDetailView(planID: plan.id)
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(plan.title)
                                        .font(.headline)
                                    Text("\(plan.contextTitle) · \(plan.venueLabel)")
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                LifecycleBadgeView(lifecycle: plan.lifecycle)
                            }
                            .padding(.vertical, 2)
                        }
                    }
                }
            }
        }
        .navigationTitle("Activity")
    }
}
