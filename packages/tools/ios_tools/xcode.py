def build_command(scheme: str, destination: str) -> str:
    return f"xcodebuild -scheme {scheme} -destination '{destination}' build"
