import SwiftUI
import UIKit
import UserNotifications

@main
struct AfterPlansApp: App {
    @StateObject private var store = AfterPlansStore.bootstrap()
    @UIApplicationDelegateAdaptor(PushNotificationDelegate.self) private var pushDelegate

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
                .tint(.appAccent)
                .onAppear {
                    pushDelegate.store = store
                    pushDelegate.requestAuthorization()
                }
        }
    }
}

// MARK: - Push notification delegate
// Phase 7: ask for notification permission on first run, register the
// resulting APNs device token with the backend, and unregister on
// signed-out scenarios. Token re-binding (security H3) is handled
// server-side via push_devices upsert on conflict (token).

final class PushNotificationDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    weak var store: AfterPlansStore?
    private var lastRegisteredToken: String?

    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        return true
    }

    func requestAuthorization() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, _ in
            guard granted else { return }
            DispatchQueue.main.async {
                UIApplication.shared.registerForRemoteNotifications()
            }
        }
    }

    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        lastRegisteredToken = token
        Task { [weak store] in
            await store?.registerPushToken(token)
        }
    }

    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        // No retry path in v1; the next cold start will try again.
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification, withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        completionHandler([.banner, .sound, .badge])
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
