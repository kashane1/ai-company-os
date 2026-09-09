import UIKit
import XCTest
@testable import Catchbook

final class CameraCaptureAvailabilityTests: XCTestCase {
    func testUsesNativeAvailabilityWithoutOverride() {
        let nativeAvailability = UIImagePickerController.isSourceTypeAvailable(.camera)
        let availability = CameraCaptureAvailability(availabilityOverride: nil)

        print("Native camera availability: \(nativeAvailability)")
        XCTAssertEqual(
            availability.isAvailable,
            nativeAvailability
        )
    }

    func testOverrideCanRepresentUnavailableCamera() {
        let availability = CameraCaptureAvailability(
            nativeAvailability: true,
            availabilityOverride: false
        )

        XCTAssertFalse(availability.isAvailable)
    }
}
