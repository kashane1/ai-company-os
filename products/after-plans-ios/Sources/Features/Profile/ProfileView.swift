import SwiftUI

struct ProfileView: View {
    @EnvironmentObject private var store: AfterPlansStore

    var body: some View {
        List {
            Section("Profile") {
                VStack(alignment: .leading, spacing: Spacing.sm) {
                    Text(store.currentUser.firstName)
                        .font(.title2.weight(.bold))
                    Text(store.currentUser.descriptor)
                        .foregroundStyle(.secondary)
                    AppBadge(text: store.currentUser.trustHeadline, tone: .appSafe)
                }
                .padding(.vertical, 6)
            }

            Section("Trust defaults") {
                Label(store.currentUser.visibilityDefault.title, systemImage: "eye")
                Text("Known people, same-context visibility, and block controls should stay visible before launch.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Section("Recent plan partners") {
                if store.recentPartners.isEmpty {
                    Text("Past partners will show up here as the seed build is exercised.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(store.recentPartners, id: \.self) { partner in
                        Text(partner)
                    }
                }
            }

            Section("Safety") {
                NavigationLink("Open safety center") {
                    SafetyCenterView(focusedPlanID: nil)
                }

                if store.blockedUserNames.isEmpty {
                    Text("No blocked users yet.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(store.blockedUserNames, id: \.self) { name in
                        Label(name, systemImage: "hand.raised")
                    }
                }
            }

            Section("Intentionally deferred") {
                Label("Ranking logic", systemImage: "chart.line.uptrend.xyaxis")
                Label("Messaging and handoff tooling", systemImage: "message")
                Label("Organizer and premium layers", systemImage: "crown")
                Label("Payments and analytics pipelines", systemImage: "creditcard")
            }
            .foregroundStyle(.secondary)
        }
        .navigationTitle("Profile")
    }
}
