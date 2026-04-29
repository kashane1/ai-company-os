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
        return try ModelContainer(
            for: schema,
            migrationPlan: LifeClockMigrationPlan.self,
            configurations: [config]
        )
    }
}
