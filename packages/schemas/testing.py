from dataclasses import asdict, dataclass
from enum import Enum


class TestLane(str, Enum):
    PYTHON = "python"
    IOS = "ios"
    NONE = "none"


class NoTestReasonCode(str, Enum):
    DOCS_ONLY = "docs_only"
    COMMENTS_ONLY = "comments_only"
    GENERATED_FILES = "generated_files"
    VISUAL_ONLY_NON_LOGIC = "visual_only_non_logic"
    CONFIG_NO_BEHAVIOR_CHANGE = "config_no_behavior_change"
    APPROVED_FOLLOWUP_TEST_TASK = "approved_followup_test_task"


class ValidationFailureCode(str, Enum):
    MISSING_TESTS_FOR_LOGIC_CHANGE = "missing_tests_for_logic_change"
    MISSING_TESTING_METADATA = "missing_testing_metadata"
    INVALID_NO_TEST_REASON_CODE = "invalid_no_test_reason_code"
    INVALID_FOLLOWUP_TEST_TASK_REFERENCE = "invalid_followup_test_task_reference"


@dataclass(frozen=True)
class TestingPolicyResult:
    tests_required: bool
    test_lane: TestLane
    relevant_tests_changed: bool
    no_test_reason_code: NoTestReasonCode | None = None
    followup_task_id: str | None = None
    failure_code: ValidationFailureCode | None = None
    details: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["test_lane"] = self.test_lane.value
        payload["no_test_reason_code"] = (
            self.no_test_reason_code.value if self.no_test_reason_code else None
        )
        payload["failure_code"] = self.failure_code.value if self.failure_code else None
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "TestingPolicyResult":
        no_test_reason_code = payload.get("no_test_reason_code")
        failure_code = payload.get("failure_code")
        return cls(
            tests_required=bool(payload.get("tests_required", False)),
            test_lane=TestLane(str(payload.get("test_lane", TestLane.NONE.value))),
            relevant_tests_changed=bool(payload.get("relevant_tests_changed", False)),
            no_test_reason_code=(
                NoTestReasonCode(str(no_test_reason_code)) if no_test_reason_code else None
            ),
            followup_task_id=str(payload["followup_task_id"])
            if payload.get("followup_task_id")
            else None,
            failure_code=ValidationFailureCode(str(failure_code)) if failure_code else None,
            details=str(payload.get("details", "")),
        )
