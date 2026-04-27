import SwiftUI

@main
struct AfterPlansApp: App {
    @StateObject private var store = AfterPlansStore.bootstrap()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
                .tint(.appAccent)
        }
    }
}

struct RootView: View {
    @EnvironmentObject private var store: AfterPlansStore

    var body: some View {
        Group {
            if store.hasCompletedOnboarding {
                MainShellView()
            } else {
                OnboardingView()
            }
        }
        .background(Color.appBackground.ignoresSafeArea())
        .onOpenURL { url in
            _ = store.handleIncomingURL(url)
        }
    }
}

struct MainShellView: View {
    @EnvironmentObject private var store: AfterPlansStore

    var body: some View {
        TabView(selection: $store.selectedTab) {
            NavigationStack {
                HomeView()
            }
            .tabItem {
                Label("Home", systemImage: "sparkles.rectangle.stack")
            }
            .tag(AppTab.home)

            NavigationStack {
                ActivityView()
            }
            .tabItem {
                Label("Activity", systemImage: "clock.arrow.trianglehead.counterclockwise.rotate.90")
            }
            .tag(AppTab.activity)

            NavigationStack {
                ProfileView()
            }
            .tabItem {
                Label("Profile", systemImage: "person.crop.circle")
            }
            .tag(AppTab.profile)
        }
    }
}
