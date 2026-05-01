import Foundation
import SwiftData

/// Builds the app's `ModelContainer`. CloudKit is **explicitly** disabled
/// because HealthKit-derived data must not iCloud-sync (App Review policy
/// + privacy posture in `docs/products/life-clock/PRIVACY_COMPLIANCE.md`).
enum LifeClockContainer {
    static func make(inMemory: Bool = false) throws -> ModelContainer {
        let schema = Schema(versionedSchema: LifeClockSchemaV1.self)
        let config = ModelConfiguration(
            "LifeClock",
            schema: schema,
            isStoredInMemoryOnly: inMemory,
            allowsSave: true,
            cloudKitDatabase: .none
        )
        let container = try ModelContainer(
            for: schema,
            migrationPlan: LifeClockMigrationPlan.self,
            configurations: [config]
        )
        #if DEBUG
        // Defensive: structural invariant — this container is built with
        // exactly one configuration explicitly carrying `cloudKitDatabase:
        // .none`. If a future refactor adds a second configuration, this
        // assertion fires loudly so a CloudKit-enabled config never sneaks
        // in unnoticed (HealthKit-derived data must not iCloud-sync per
        // `docs/products/life-clock/PRIVACY_COMPLIANCE.md`).
        assert(
            container.configurations.count == 1,
            "LifeClockContainer must be configured with exactly one ModelConfiguration (with cloudKitDatabase: .none)"
        )
        #endif
        return container
    }
}
