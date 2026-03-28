from pathlib import Path


def detect_project_reference(root: Path) -> str | None:
    for extension in ("*.xcodeproj", "*.xcworkspace"):
        matches = sorted(root.glob(extension))
        if matches:
            return matches[0].name
    return None


def build_command(scheme: str, destination: str, *, project_reference: str | None = None) -> str:
    project_flag = ""
    if project_reference:
        if project_reference.endswith(".xcworkspace"):
            project_flag = f"-workspace {project_reference} "
        else:
            project_flag = f"-project {project_reference} "
    return f"xcodebuild {project_flag}-scheme {scheme} -destination '{destination}' build"


def default_build_command(project_reference: str) -> str:
    return build_command(
        scheme="FishingLogbook",
        destination="platform=iOS Simulator,name=iPhone 16",
        project_reference=project_reference,
    )
