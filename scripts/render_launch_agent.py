#!/usr/bin/env python3
"""Render the LaunchAgent locally; installation is a separate operator action."""

import argparse
import plistlib
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "infra/launchd/com.ai-company-os.runtime-supervisor.plist"


def render(repo_root: Path, output: Path) -> None:
    root = repo_root.resolve()
    payload = plistlib.loads(TEMPLATE.read_bytes())

    def substitute(value):
        if isinstance(value, str):
            return value.replace("__REPO_ROOT__", str(root))
        if isinstance(value, list):
            return [substitute(item) for item in value]
        if isinstance(value, dict):
            return {key: substitute(item) for key, item in value.items()}
        return value

    payload = substitute(payload)
    for key in ("StandardOutPath", "StandardErrorPath"):
        Path(payload[key]).parent.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(plistlib.dumps(payload, sort_keys=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.repo_root, args.output)
