import SwiftData
import SwiftUI

@main
struct FishingLogbookApp: App {
    @State private var selectedTab: AppTab = .home

    var body: some Scene {
        WindowGroup {
            TabView(selection: $selectedTab) {
                HomeView(selectedTab: $selectedTab)
                    .tabItem {
                        Label("Home", systemImage: "house")
                    }
                    .tag(AppTab.home)

                TripsView()
                    .tabItem {
                        Label("Trips", systemImage: "clock.arrow.circlepath")
                    }
                    .tag(AppTab.trips)

                LogView()
                    .tabItem {
                        Label("Log", systemImage: "plus.circle.fill")
                    }
                    .tag(AppTab.log)

                SpotsView()
                    .tabItem {
                        Label("Spots", systemImage: "mappin.and.ellipse")
                    }
                    .tag(AppTab.spots)
            }
            .tint(.teal)
        }
        .modelContainer(for: [
            Waterbody.self,
            Spot.self,
            Trip.self,
            CatchRecord.self,
            ConditionSnapshot.self,
            PersonalBest.self,
        ])
    }
}
