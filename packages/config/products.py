import json
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.schemas.product import ProductConfig, ProductPhase, ProductPlatform


def load_product_configs(config_path: Path | None = None) -> dict[str, ProductConfig]:
    paths = load_runtime_paths()
    registry_path = config_path or (paths.repo_root / "infra" / "products.json")
    with registry_path.open() as handle:
        raw_configs = json.load(handle)

    configs: dict[str, ProductConfig] = {}
    for item in raw_configs:
        source_path = Path(item["source_path"])
        if not source_path.is_absolute():
            source_path = (paths.repo_root / source_path).resolve()

        docs_root = Path(item["docs_root"])
        if not docs_root.is_absolute():
            docs_root = (paths.repo_root / docs_root).resolve()

        # Phase 5.3 — phase is additive/optional.
        phase_raw = item.get("phase")
        try:
            phase = ProductPhase(str(phase_raw)) if phase_raw else ProductPhase.DISCOVERY
        except ValueError:
            phase = ProductPhase.DISCOVERY

        configs[item["id"]] = ProductConfig(
            id=item["id"],
            name=item["name"],
            slug=item["slug"],
            platform=ProductPlatform(str(item["platform"])),
            repo_id=item["repo_id"],
            source_path=str(source_path),
            docs_root=str(docs_root),
            phase=phase,
        )

    return configs


# Backwards-compat alias — some older call sites import ``load_products``.
load_products = load_product_configs
