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


def set_client_netlify_site_id(
    product_id: str,
    site_id: str,
    *,
    registry_path: Path | None = None,
) -> dict[str, object]:
    """Stamp the client's own Netlify site id onto the nested ``client`` block.

    Recorded at launch so the lead-health drain can target the client's
    ``inbound-leads`` Blobs store on their own site.
    """
    record = get_registry_record(product_id, registry_path=registry_path)
    client = {**(record.get("client") or {}), "netlify_site_id": site_id}
    return update_registry_record(product_id, {"client": client}, registry_path=registry_path)


def lead_drain_targets(*, registry_path: Path | None = None) -> list[dict[str, str]]:
    """Client sites whose contact-form lead store should be drained + monitored.

    Lead monitoring only matters for sites that actually capture leads, so a target
    is a ``client-site`` that bought the ``contact_forms`` service (the explicit
    lead-capture signal) AND has a recorded ``netlify_site_id`` (so we can reach
    their store). Form-less businesses are skipped entirely — no false "no leads"
    nags. Returns ``[{"product_id", "site_id"}]``. This is the canonical filter;
    the Node drain (``scripts/web/pull-leads.mjs``) mirrors it.
    """
    targets: list[dict[str, str]] = []
    for record in load_registry(registry_path):
        if record.get("type") != "client-site":
            continue
        client = record.get("client") or {}
        if not isinstance(client, dict):
            continue
        site_id = str(client.get("netlify_site_id", "")).strip()
        services = [str(s) for s in list(client.get("services", []))]
        if site_id and "contact_forms" in services:
            targets.append({"product_id": str(record["id"]), "site_id": site_id})
    return targets
