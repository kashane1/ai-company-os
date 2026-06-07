"""Prospect → client promotion (Agency layer, Phase 3).

The one-way, approval-gated transition that connects the two existing halves:
the prospecting warehouse (verified local SMBs with no owned website) and the web
lane (which can build + ship a site). Promotion does **not** send outreach; it is
an operator-initiated, approval-gated registry transition.

Steps:

1. ``assert_promotion_allowed`` — refuse unless the prospect is human-verified
   **and** a founder approval is granted.
2. validate the bundle against the service catalog;
3. write a ``type: client-site`` record into the product registry
   (``infra/products.json``), backlinking ``client.from_prospect``;
4. scaffold the client docs workspace from the Phase 3 template stubs.

Idempotent: re-running for an already-promoted prospect returns the existing
record without duplicating it.
"""

from __future__ import annotations

from pathlib import Path

from packages.agency.catalog import ServiceCatalog, default_catalog
from packages.agency.client_lifecycle import mark_prospect_onboarded
from packages.agency.registry import load_registry, write_registry
from packages.agency.templates import scaffold_client_workspace, slugify
from packages.config.settings import load_runtime_paths
from packages.policies.agency_gates import assert_promotion_allowed
from packages.prospecting.storage import ProspectRepository
from packages.schemas.offer import CatalogError
from packages.schemas.prospect import HumanVerified, ProspectRecord


class PromotionError(ValueError):
    """Raised for non-policy promotion failures (e.g. unknown bundle)."""


def promote_prospect_to_client(
    prospect: ProspectRecord,
    bundle: str,
    *,
    approval_granted: bool,
    catalog: ServiceCatalog | None = None,
    registry_path: Path | None = None,
    docs_root_parent: Path | None = None,
    repo_root: Path | None = None,
    prospect_repo: ProspectRepository | None = None,
    mark_onboarded: bool = True,
) -> dict[str, object]:
    """Promote ``prospect`` into a ``client-site`` registry record.

    Returns the registry record dict (existing one if already promoted).
    """
    catalog = catalog or default_catalog()
    paths = load_runtime_paths(repo_root)
    registry_path = registry_path or (paths.repo_root / "infra" / "products.json")
    docs_root_parent = docs_root_parent or (paths.repo_root / "docs" / "products")

    # 1. Policy gate — human-verified + approved.
    assert_promotion_allowed(
        human_verified=prospect.human_verified is HumanVerified.TRUE,
        approval_granted=approval_granted,
    )

    # 2. Validate the bundle against the catalog.
    try:
        quote = catalog.quote_bundle(bundle)
    except CatalogError as exc:
        raise PromotionError(str(exc)) from exc

    slug = slugify(prospect.display_name)
    product_id = f"{slug}-site"

    registry = load_registry(registry_path)
    existing = next((r for r in registry if r.get("id") == product_id), None)
    if existing is not None:
        # Already promoted. Re-running with a *different* bundle would silently
        # diverge the signed OFFER.md from the registry record — refuse it.
        existing_bundle = (existing.get("client") or {}).get("bundle")
        if existing_bundle != bundle:
            raise PromotionError(
                f"{product_id!r} is already promoted with bundle {existing_bundle!r}; "
                f"refusing to silently change it to {bundle!r}. Change the bundle explicitly."
            )
        # Same bundle: idempotent re-scaffold from the *stored* bundle is safe.
        scaffold_client_workspace(
            docs_root_parent / product_id,
            client_name=prospect.display_name,
            bundle_id=existing_bundle,
            catalog=catalog,
            from_prospect=prospect.place_id,
        )
        if mark_onboarded:
            mark_prospect_onboarded(prospect, repo=prospect_repo)
        return existing

    record = {
        "id": product_id,
        "name": prospect.display_name,
        "slug": slug,
        "type": "client-site",
        "platform": "web",
        "source_path": f"products/{product_id}",
        "docs_root": f"docs/products/{product_id}",
        "phase": "discovery",
        "client": {
            "ownership": "client-owned",
            "bundle": bundle,
            "services": [s.service_id for s in quote.services],
            "from_prospect": prospect.place_id,
            "billing_status": "trial",
        },
    }

    registry.append(record)
    write_registry(registry_path, registry)

    scaffold_client_workspace(
        docs_root_parent / product_id,
        client_name=prospect.display_name,
        bundle_id=bundle,
        catalog=catalog,
        from_prospect=prospect.place_id,
    )
    if mark_onboarded:
        mark_prospect_onboarded(prospect, repo=prospect_repo)
    return record


def promote_order_to_client(
    *,
    product_id: str,
    business_name: str,
    service_ids: list[str],
    bundle: str = "custom",
    catalog: ServiceCatalog | None = None,
    registry_path: Path | None = None,
    docs_root_parent: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Promote a self-serve buy-now order into a ``client-site`` registry record.

    Unlike :func:`promote_prospect_to_client`, there is no prospect and no founder
    approval gate — the public buy button *is* the approval. The ``product_id``
    MUST be the one the Netlify function minted (it rides in the Stripe metadata),
    so the billing reconciler finds a registry record and activates instead of
    dead-lettering. Idempotent on ``product_id``.
    """
    catalog = catalog or default_catalog()
    paths = load_runtime_paths(repo_root)
    registry_path = registry_path or (paths.repo_root / "infra" / "products.json")
    docs_root_parent = docs_root_parent or (paths.repo_root / "docs" / "products")

    if not product_id:
        raise PromotionError("promote_order_to_client: product_id is required")

    # Validate the purchased services against the catalog (unknown id → error).
    try:
        catalog.quote_services(service_ids)
    except CatalogError as exc:
        raise PromotionError(str(exc)) from exc

    # A preset order scaffolds from its bundle (curated promo); a custom cart
    # scaffolds from the raw service set.
    is_preset = bundle in catalog.bundles
    scaffold_kwargs: dict[str, object] = (
        {"bundle_id": bundle} if is_preset else {"service_ids": list(service_ids)}
    )

    registry = load_registry(registry_path)
    existing = next((r for r in registry if r.get("id") == product_id), None)
    if existing is not None:
        existing_services = set((existing.get("client") or {}).get("services") or [])
        if existing_services != set(service_ids):
            raise PromotionError(
                f"{product_id!r} already exists with a different service set; "
                "refusing to silently change it."
            )
        scaffold_client_workspace(
            docs_root_parent / product_id,
            client_name=business_name,
            catalog=catalog,
            **scaffold_kwargs,
        )
        return existing

    record = {
        "id": product_id,
        "name": business_name,
        "slug": slugify(business_name),
        "type": "client-site",
        "platform": "web",
        "source_path": f"products/{product_id}",
        "docs_root": f"docs/products/{product_id}",
        "phase": "discovery",
        "client": {
            "ownership": "client-owned",
            "bundle": bundle,
            "services": list(service_ids),
            "from_order": product_id,
            "billing_status": "trial",
        },
    }
    registry.append(record)
    write_registry(registry_path, registry)

    scaffold_client_workspace(
        docs_root_parent / product_id,
        client_name=business_name,
        catalog=catalog,
        **scaffold_kwargs,
    )
    return record
