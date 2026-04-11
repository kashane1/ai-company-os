import XCTest
@testable import Catchbook

final class PersistenceFailureHandlingTests: XCTestCase {
    func testPerformRunsSuccessCallbackWhenCommitSucceeds() {
        var didCommit = false
        var didSucceed = false
        var failureMessage: String?

        PersistenceWriteCoordinator.perform(
            commit: {
                didCommit = true
            },
            onSuccess: {
                didSucceed = true
            },
            onFailure: { message in
                failureMessage = message
            }
        )

        XCTAssertTrue(didCommit)
        XCTAssertTrue(didSucceed)
        XCTAssertNil(failureMessage)
    }

    func testPerformDoesNotRunSuccessCallbackAndRunsRollbackWhenCommitFails() {
        enum StubError: Error {
            case failed
        }

        var didRollback = false
        var didSucceed = false
        var failureMessage: String?

        PersistenceWriteCoordinator.perform(
            userMessage: "Custom failure",
            commit: {
                throw StubError.failed
            },
            rollback: {
                didRollback = true
            },
            onSuccess: {
                didSucceed = true
            },
            onFailure: { message in
                failureMessage = message
            }
        )

        XCTAssertTrue(didRollback)
        XCTAssertFalse(didSucceed)
        XCTAssertEqual(failureMessage, "Custom failure")
    }

    func testPerformUsesDefaultFailureMessage() {
        enum StubError: Error {
            case failed
        }

        var failureMessage: String?

        PersistenceWriteCoordinator.perform(
            commit: {
                throw StubError.failed
            },
            onSuccess: {
                XCTFail("Success callback should not run when commit fails")
            },
            onFailure: { message in
                failureMessage = message
            }
        )

        XCTAssertEqual(failureMessage, PersistenceWriteCoordinator.defaultUserMessage)
    }
}
