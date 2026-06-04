"""Product registry helpers for client-site engagements (Agency layer)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.schemas.product import ProductPhase


class RegistryError(ValueError):
    """Raised when a registry lookup or update fails."""


def default_registry_path(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).repo_root / "infra" / "products.json"


def load_registry(path: Path | None = None) -> list[dict[str, object]]:
    path = path or default_registry_path()
    if not path.exists():
        return []
    return list(json.loads(path.read_text(encoding="utf-8")))


def write_registry(path: Path, registry: list[dict[str, object]]) -> None:
    # Atomic write ([X-ATOM]): the registry holds entitlement state, so a crash
    # mid-write must never truncate it. Temp file in the same dir, then replace.
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(registry, indent=2) + "\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def get_registry_record(product_id: str, *, registry_path: Path | None = None) -> dict[str, object]:
    path = registry_path or default_registry_path()
    for record in load_registry(path):
        if record.get("id") == product_id:
            return record
    raise RegistryError(f"no product registry record for {product_id!r}")


def find_client_by_prospect(place_id: str, *, registry_path: Path | None = None) -> dict[str, object] | None:
    for record in load_registry(registry_path):
        if record.get("type") != "client-site":
            continue
        client = record.get("client") or {}
        if isinstance(client, dict) and client.get("from_prospect") == place_id:
            return record
    return None


def update_registry_record(
    product_id: str,
    patch: dict[str, object],
    *,
    registry_path: Path | None = None,
) -> dict[str, object]:
    """Merge ``patch`` into the top-level registry record for ``product_id``."""
    path = registry_path or default_registry_path()
    registry = load_registry(path)
    for i, record in enumerate(registry):
        if record.get("id") != product_id:
            continue
        merged = {**record, **patch}
        registry[i] = merged
        write_registry(path, registry)
        return merged
    raise RegistryError(f"no product registry record for {product_id!r}")


def set_client_phase(
    product_id: str,
    phase: ProductPhase,
    *,
    registry_path: Path | None = None,
) -> dict[str, object]:
    return update_registry_record(product_id, {"phase": phase.value}, registry_path=registry_path)
