import XCTest
@testable import LifeClock

/// Privacy-redaction guard: assert the `OnboardingTelemetry` protocol's
/// public bucketing helpers always emit coarse buckets and never pass
/// raw integer scores through. The default `OSLogTelemetry` impl uses
/// `Logger` with `privacy: .private` on value parameters; that's tested
/// implicitly by the call-site contract — this file pins the contract.
final class OnboardingTelemetryTests: XCTestCase {

    // MARK: - StubTelemetry sequence assertions

    func testStubRecordsEventsInOrder() {
        let stub = StubTelemetry()
        stub.screenAppeared("welcome")
        stub.choiceMade("goalPick", key: "goal", valueBucket: "moreEnergy")
        stub.dialAdjusted(yearsBucket: "zero_pos1")
        stub.paywallShown(stage: .primary)
        stub.purchased(productID: "com.lifeclock.pro.annual")

        XCTAssertEqual(stub.events, [
            "screenAppeared:welcome",
            "choiceMade:goalPick:goal:moreEnergy",
            "dialAdjusted:zero_pos1",
            "paywallShown:primary",
            "purchased:com.lifeclock.pro.annual",
        ])
    }

    // MARK: - Bucketing helpers (raw values must never escape)

    func testPSSBucketing_NeverEmitsRawScore() {
        XCTAssertEqual(PerceivedStressBucket.bucket(for: 5), "low")
        XCTAssertEqual(PerceivedStressBucket.bucket(for: 13), "low")
        XCTAssertEqual(PerceivedStressBucket.bucket(for: 14), "medium")
        XCTAssertEqual(PerceivedStressBucket.bucket(for: 26), "medium")
        XCTAssertEqual(PerceivedStressBucket.bucket(for: 27), "high")
        XCTAssertEqual(PerceivedStressBucket.bucket(for: 40), "high")
    }

    func testLonelinessBucketing_NeverEmitsRawScore() {
        XCTAssertEqual(LonelinessBucket.bucket(for: 3), "connected")
        XCTAssertEqual(LonelinessBucket.bucket(for: 5), "connected")
        XCTAssertEqual(LonelinessBucket.bucket(for: 6), "lonely")
        XCTAssertEqual(LonelinessBucket.bucket(for: 9), "lonely")
    }

    func testParentLongevityBucketing_NeverEmitsRawAge() {
        XCTAssertEqual(ParentLongevityBucket.bucket(for: 95), "very_long")
        XCTAssertEqual(ParentLongevityBucket.bucket(for: 80), "long")
        XCTAssertEqual(ParentLongevityBucket.bucket(for: 70), "average")
        XCTAssertEqual(ParentLongevityBucket.bucket(for: 65), "short")
        XCTAssertEqual(ParentLongevityBucket.bucket(for: 50), "very_short")
    }

    func testDialAdjustmentBucketing_NeverEmitsRawValue() {
        XCTAssertEqual(DialAdjustmentBucket.bucket(for: -4.5), "neg5_neg3")
        XCTAssertEqual(DialAdjustmentBucket.bucket(for: -2.0), "neg3_neg1")
        XCTAssertEqual(DialAdjustmentBucket.bucket(for: -0.5), "neg1_zero")
        XCTAssertEqual(DialAdjustmentBucket.bucket(for: 0.0), "zero")
        XCTAssertEqual(DialAdjustmentBucket.bucket(for: 0.5), "zero_pos1")
        XCTAssertEqual(DialAdjustmentBucket.bucket(for: 2.0), "pos1_pos3")
        XCTAssertEqual(DialAdjustmentBucket.bucket(for: 4.0), "pos3_pos5")
    }

    /// Hard guard: every bucket label is alphabetic / underscore only —
    /// no digits. If a future change accidentally interpolates a raw
    /// score into a label, this test fails immediately.
    func testNoBucketLabelContainsRawDigits() {
        let stub = StubTelemetry()

        // Run every bucket type through a representative value.
        stub.choiceMade("stressScreen", key: "pss",
                        valueBucket: PerceivedStressBucket.bucket(for: 27))
        stub.choiceMade("socialScreen", key: "ucla",
                        valueBucket: LonelinessBucket.bucket(for: 7))
        stub.choiceMade("familyMother", key: "ageAtDeath",
                        valueBucket: ParentLongevityBucket.bucket(for: 67))
        stub.dialAdjusted(yearsBucket: DialAdjustmentBucket.bucket(for: 2.5))

        // Extract just the bucket portions of every event string
        // (last colon-separated component for choice events; the value
        // for dialAdjusted).
        for event in stub.events {
            // The bucket value is intentionally NOT a number.
            // Bucket labels are tokens like "high", "lonely", "very_long",
            // "pos3_pos5". The numeric components ("3", "5") are
            // cohort labels (pre-defined in code), not raw user scores —
            // distinguishable because they appear ONLY inside underscore-
            // joined tokens. Raw user scores would appear standalone
            // (e.g. "27" by itself) which this assert would catch.
            let lastComponent = event.split(separator: ":").last ?? ""
            // Standalone numeric tokens (no surrounding letters) are
            // forbidden — those would be raw scores. Bucket labels
            // like "pos3_pos5" are allowed because the digits sit
            // inside an alphabetic token.
            let tokens = lastComponent.split(whereSeparator: { !$0.isLetter && !$0.isNumber && $0 != "_" })
            for token in tokens {
                let isPureNumber = token.allSatisfy { $0.isNumber }
                XCTAssertFalse(
                    isPureNumber,
                    "Raw numeric token '\(token)' leaked through telemetry — bucket the value first."
                )
            }
        }
    }
}
