import XCTest
@testable import Catchbook

final class DeterministicInsightCardTests: XCTestCase {
    func testIdReturnsKindRawValue() {
        let card = DeterministicInsightCard(
            kind: .lastTrips,
            title: "Recent Activity",
            body: "You've been fishing regularly",
            supportingSampleCount: 5,
            systemImage: "calendar"
        )

        XCTAssertEqual(card.id, "lastTrips")
    }

    func testIdReturnsCorrectRawValueForRecencyKind() {
        let card = DeterministicInsightCard(
            kind: .recency,
            title: "Recency",
            body: "Your last trip was recent",
            supportingSampleCount: 1,
            systemImage: "clock"
        )

        XCTAssertEqual(card.id, "recency")
    }

    func testIdReturnsCorrectRawValueForProductivityKind() {
        let card = DeterministicInsightCard(
            kind: .productivity,
            title: "Productivity Trend",
            body: "Catches per trip improving",
            supportingSampleCount: 10,
            systemImage: "chart.bar"
        )

        XCTAssertEqual(card.id, "productivity")
    }

    func testAllKindCasesHaveUniqueRawValues() {
        let kinds: [DeterministicInsightCard.Kind] = [
            .lastTrips,
            .recency,
            .productivity,
            .species,
            .conditions,
            .lure,
            .bestTimeWindow,
            .mostEffectiveLure,
            .seasonality,
            .similarConditions
        ]

        let rawValues = kinds.map { $0.rawValue }
        let uniqueRawValues = Set(rawValues)

        XCTAssertEqual(rawValues.count, uniqueRawValues.count, "All Kind cases should have unique rawValues")
    }

    func testCardStoresAllProperties() {
        let title = "Time Window Analysis"
        let body = "Best fishing between 6-9 AM"
        let sampleCount = 7
        let image = "sun.max"

        let card = DeterministicInsightCard(
            kind: .bestTimeWindow,
            title: title,
            body: body,
            supportingSampleCount: sampleCount,
            systemImage: image
        )

        XCTAssertEqual(card.kind, .bestTimeWindow)
        XCTAssertEqual(card.title, title)
        XCTAssertEqual(card.body, body)
        XCTAssertEqual(card.supportingSampleCount, sampleCount)
        XCTAssertEqual(card.systemImage, image)
    }

    func testCardWithSpeciesKindStoresProperties() {
        let card = DeterministicInsightCard(
            kind: .species,
            title: "Most Caught Species",
            body: "Bass is your most frequent catch",
            supportingSampleCount: 12,
            systemImage: "fish.fill"
        )

        XCTAssertEqual(card.kind, .species)
        XCTAssertEqual(card.id, "species")
        XCTAssertEqual(card.supportingSampleCount, 12)
    }

    func testCardWithConditionsKindStoresProperties() {
        let card = DeterministicInsightCard(
            kind: .conditions,
            title: "Condition Patterns",
            body: "Overcast days show higher success",
            supportingSampleCount: 8,
            systemImage: "cloud.fill"
        )

        XCTAssertEqual(card.kind, .conditions)
        XCTAssertEqual(card.id, "conditions")
    }

    func testCardWithLureKindStoresProperties() {
        let card = DeterministicInsightCard(
            kind: .lure,
            title: "Lure Preference",
            body: "Spinner outperforms other lures",
            supportingSampleCount: 6,
            systemImage: "hook"
        )

        XCTAssertEqual(card.kind, .lure)
        XCTAssertEqual(card.id, "lure")
    }

    func testCardIdentifiableConformance() {
        let card = DeterministicInsightCard(
            kind: .mostEffectiveLure,
            title: "Top Lure",
            body: "Crankbait is most effective",
            supportingSampleCount: 9,
            systemImage: "sparkles"
        )

        // Verify Identifiable conformance by accessing id
        let id = card.id
        XCTAssertNotNil(id)
        XCTAssertEqual(id, "mostEffectiveLure")
    }

    func testCardWithSeasonalityKind() {
        let card = DeterministicInsightCard(
            kind: .seasonality,
            title: "Seasonal Trends",
            body: "Spring shows your best catches",
            supportingSampleCount: 15,
            systemImage: "leaf.fill"
        )

        XCTAssertEqual(card.kind, .seasonality)
        XCTAssertEqual(card.id, "seasonality")
    }

    func testCardWithSimilarConditionsKind() {
        let card = DeterministicInsightCard(
            kind: .similarConditions,
            title: "Matching Conditions",
            body: "Similar weather brought success before",
            supportingSampleCount: 4,
            systemImage: "checkmark.circle"
        )

        XCTAssertEqual(card.kind, .similarConditions)
        XCTAssertEqual(card.id, "similarConditions")
    }
}
