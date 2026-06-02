import json
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.schemas.product import (
    ClientConfig,
    ProductConfig,
    ProductPhase,
    ProductPlatform,
    ProductType,
)


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

        # Agency layer (Phase 2) — ``type`` is additive/optional and defaults to
        # ``product``. Client sites carry a ``client {}`` block and may omit
        # ``repo_id`` (they have no source repo of their own in the iOS sense),
        # so it is read with a default rather than required.
        try:
            product_type = ProductType(str(item.get("type", ProductType.PRODUCT.value)))
        except ValueError:
            product_type = ProductType.PRODUCT

        client_raw = item.get("client")
        client = ClientConfig.from_dict(client_raw) if isinstance(client_raw, dict) else None

        # ``platform`` is required for owned products; client sites default to web.
        if "platform" in item:
            platform = ProductPlatform(str(item["platform"]))
        elif product_type is ProductType.CLIENT_SITE:
            platform = ProductPlatform.WEB
        else:
            platform = ProductPlatform(str(item["platform"]))  # raise KeyError as before

        configs[item["id"]] = ProductConfig(
            id=item["id"],
            name=item["name"],
            slug=item["slug"],
            platform=platform,
            repo_id=str(item.get("repo_id", "")),
            source_path=str(source_path),
            docs_root=str(docs_root),
            phase=phase,
            type=product_type,
            client=client,
        )

    return configs


# Backwards-compat alias — some older call sites import ``load_products``.
load_products = load_product_configs
