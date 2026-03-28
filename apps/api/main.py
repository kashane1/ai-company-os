from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.platform import demo_platform_flow
from packages.config.settings import ensure_runtime_directories, load_runtime_paths


def health() -> dict[str, str]:
    paths = ensure_runtime_directories()
    return {
        "status": "ok",
        "repo_root": str(paths.repo_root),
        "state_root": str(paths.state_root),
    }


if __name__ == "__main__":
    print({"health": health(), "engineering_demo": demo_platform_flow()})
