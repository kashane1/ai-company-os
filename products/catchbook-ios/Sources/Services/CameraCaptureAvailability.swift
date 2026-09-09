import UIKit

struct CameraCaptureAvailability {
    let isAvailable: Bool

    init(
        nativeAvailability: Bool = UIImagePickerController.isSourceTypeAvailable(.camera),
        availabilityOverride: Bool? = CatchbookLaunchConfiguration.cameraAvailabilityOverride
    ) {
        isAvailable = availabilityOverride ?? nativeAvailability
    }
}
