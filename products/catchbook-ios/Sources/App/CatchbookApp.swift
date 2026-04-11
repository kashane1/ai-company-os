import SwiftData
import SwiftUI

@main
struct CatchbookApp: App {
    @State private var selectedTab: AppTab = .home
    @State private var selectedTripID: UUID?

    init() {
        // Instantiate the shared formatters singleton eagerly so its locale
        // change observer is registered before any view reads a formatter.
        _ = AppFormatters.shared
    }

    var body: some Scene {
        WindowGroup {
            TabView(selection: $selectedTab) {
                HomeView(selectedTab: $selectedTab)
                    .tabItem {
                        Label("Home", systemImage: "house")
                    }
                    .tag(AppTab.home)

                TripsView(selectedTripID: $selectedTripID)
                    .tabItem {
                        Label("Trips", systemImage: "clock.arrow.circlepath")
                    }
                    .tag(AppTab.trips)

                LogView { trip in
                    selectedTripID = trip.id
                    selectedTab = .trips
                }
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
            .tint(.catchbookOcean)
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
