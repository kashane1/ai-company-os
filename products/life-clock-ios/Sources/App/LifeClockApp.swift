import SwiftUI
import SwiftData

@main
@MainActor
struct LifeClockApp: App {
    let container: ModelContainer
    @State private var store: LifeClockStore
    @State private var subscriptions = SubscriptionStore()

    init() {
        let container: ModelContainer
        do {
            container = try LifeClockContainer.make()
        } catch {
            fatalError("ModelContainer init failed: \(error)")
        }
        self.container = container
        let store = LifeClockStore(
            healthService: HealthKitConfiguration.service(),
            modelContext: container.mainContext
        )
        _store = State(wrappedValue: store)
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .environment(subscriptions)
                .task {
                    await store.bootstrap()
                    await subscriptions.loadProducts()
                    await subscriptions.refreshEntitlements()
                }
        }
        .modelContainer(container)
    }
}

struct RootView: View {
    @Query private var profiles: [UserProfile]

    var body: some View {
        if profiles.isEmpty {
            OnboardingView()
        } else {
            MainTabView()
        }
    }
}

struct MainTabView: View {
    @State private var selection: AppTab = .today

    var body: some View {
        TabView(selection: $selection) {
            TodayView()
                .tabItem { Label(AppTab.today.title, systemImage: AppTab.today.systemImage) }
                .tag(AppTab.today)

            TimeLedgerView()
                .tabItem { Label(AppTab.ledger.title, systemImage: AppTab.ledger.systemImage) }
                .tag(AppTab.ledger)

            QuestsView()
                .tabItem { Label(AppTab.quests.title, systemImage: AppTab.quests.systemImage) }
                .tag(AppTab.quests)

            WeeklyReportView()
                .tabItem { Label(AppTab.weekly.title, systemImage: AppTab.weekly.systemImage) }
                .tag(AppTab.weekly)

            ProfileView()
                .tabItem { Label(AppTab.profile.title, systemImage: AppTab.profile.systemImage) }
                .tag(AppTab.profile)
        }
    }
}
