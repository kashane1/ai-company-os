import SwiftUI
import SwiftData

@main
@MainActor
struct LifeClockApp: App {
    let container: ModelContainer
    let launchConfiguration: LifeClockLaunchConfiguration
    @State private var store: LifeClockStore
    @State private var subscriptions = SubscriptionStore()
    @State private var hasBootstrapped: Bool = false
    @Environment(\.scenePhase) private var scenePhase

    init() {
        let launchConfiguration = LifeClockLaunchConfiguration.current
        self.launchConfiguration = launchConfiguration
        let container: ModelContainer
        do {
            container = try LifeClockContainer.make(inMemory: launchConfiguration.useInMemoryStore)
        } catch {
            fatalError("ModelContainer init failed: \(error)")
        }
        self.container = container
        launchConfiguration.seedInitialStateIfNeeded(in: container.mainContext)
        let notificationsService = NotificationsService()
        // Foreground delegate must be set BEFORE any notification could
        // arrive — otherwise iOS silently suppresses foreground banners.
        notificationsService.installForegroundDelegate()
        let store = LifeClockStore(
            healthService: launchConfiguration.makeHealthService(),
            modelContext: container.mainContext,
            engineClock: launchConfiguration.clock,
            notificationsService: notificationsService
        )
        _store = State(wrappedValue: store)
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .environment(subscriptions)
                .tint(store.palette.accent)
                .task {
                    await store.bootstrap()
                    hasBootstrapped = true
                    await subscriptions.loadProducts()
                    await subscriptions.refreshEntitlements()
                }
                .onChange(of: scenePhase) { _, newPhase in
                    // Catch permission flips made in iOS Settings without
                    // requiring a relaunch. Skip the first .active
                    // transition — bootstrap() already refreshed and
                    // reconciled.
                    guard newPhase == .active, hasBootstrapped else { return }
                    Task { await store.refreshNotificationAuthorization() }
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
