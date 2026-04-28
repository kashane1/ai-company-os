import SwiftUI

@main
struct LifeClockApp: App {
    @State private var store = LifeClockStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .task { await store.bootstrap() }
        }
    }
}

struct RootView: View {
    @Environment(LifeClockStore.self) private var store

    var body: some View {
        if store.hasCompletedOnboarding {
            MainTabView()
        } else {
            OnboardingView()
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
