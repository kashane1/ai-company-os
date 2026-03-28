import json
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.schemas.repo import RepoConfig


def load_repo_configs(config_path: Path | None = None) -> dict[str, RepoConfig]:
    paths = load_runtime_paths()
    registry_path = config_path or (paths.repo_root / "infra" / "repos.json")
    with registry_path.open() as handle:
        raw_configs = json.load(handle)

    configs: dict[str, RepoConfig] = {}
    for item in raw_configs:
        source_path = Path(item["source_path"])
        if not source_path.is_absolute():
            source_path = (paths.repo_root / source_path).resolve()

        configs[item["id"]] = RepoConfig(
            id=item["id"],
            name=item["name"],
            source_path=str(source_path),
            managed_repo_name=item.get("managed_repo_name", item["id"]),
            default_branch=item.get("default_branch", "main"),
        )

    return configs
