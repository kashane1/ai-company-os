from pathlib import Path

from packages.tools.ios_tools.xcode import build_command, default_build_command, detect_project_reference


def test_detect_project_reference_prefers_project_before_workspace(tmp_path: Path) -> None:
    (tmp_path / "Catchbook.xcodeproj").mkdir()
    (tmp_path / "Catchbook.xcworkspace").mkdir()

    assert detect_project_reference(tmp_path) == "Catchbook.xcodeproj"


def test_build_command_uses_project_flag_when_project_reference_is_project() -> None:
    command = build_command(
        scheme="Catchbook",
        destination="platform=iOS Simulator,name=iPhone 16",
        project_reference="Catchbook.xcodeproj",
    )

    assert command == (
        "xcodebuild -project Catchbook.xcodeproj -scheme Catchbook "
        "-destination 'platform=iOS Simulator,name=iPhone 16' build"
    )


def test_default_build_command_uses_catchbook_defaults() -> None:
    command = default_build_command("Catchbook.xcworkspace")

    assert command == (
        "xcodebuild -workspace Catchbook.xcworkspace -scheme Catchbook "
        "-destination 'platform=iOS Simulator,name=iPhone 16' build"
    )
