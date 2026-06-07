"""Client delivery orchestration — Phases 3–5 (Agency layer).

Wires promotion, intake, product scaffold, and launch gating into one callable
surface for operator CLIs and skills.

Typical flow::

    promote  →  client_intake  →  build (Astro)  →  launch_checklist  →  live
"""

from __future__ import annotations

import json
from pathlib import Path

from packages.agency.catalog import ServiceCatalog, default_catalog
from packages.agency.intake import ClientIntake, render_brief, write_intake
from packages.agency.launch import LaunchChecklistReport, run_launch_checklist
from packages.agency.prospect_site import intake_from_record
from packages.agency.registry import (
    RegistryError,
    default_registry_path,
    get_registry_record,
    set_client_phase,
)
from packages.agency.templates import scaffold_client_workspace, slugify
from packages.config.settings import load_runtime_paths
from packages.prospecting.storage import ProspectRepository
from packages.schemas.product import ProductPhase
from packages.schemas.prospect import EngagementStatus, ProspectRecord, replace_record
from packages.web.scaffold import scaffold_site, unfilled_tokens


class LaunchNotReadyError(RuntimeError):
    """Launch checklist did not pass — site must not be marked live."""


def intake_from_prospect(prospect: ProspectRecord) -> ClientIntake:
    """Map a warehouse prospect into a :class:`ClientIntake` (genre defaults)."""
    return intake_from_record(prospect.to_dict())


def apply_client_intake(
    docs_root: Path,
    intake: ClientIntake,
    *,
    bundle_id: str,
    catalog: ServiceCatalog | None = None,
    from_prospect: str = "",
) -> list[Path]:
    """Write ``CLIENT_BRIEF.md`` and refresh workspace stubs from intake."""
    intake.validate()
    catalog = catalog or default_catalog()
    docs_root.mkdir(parents=True, exist_ok=True)
    (docs_root / "reports").mkdir(exist_ok=True)

    from packages.agency.templates import render_offer

    paths = scaffold_client_workspace(
        docs_root,
        client_name=intake.business_name,
        bundle_id=bundle_id,
        catalog=catalog,
        from_prospect=from_prospect,
    )
    brief_path = docs_root / "CLIENT_BRIEF.md"
    brief_path.write_text(render_brief(intake), encoding="utf-8")

    copy_path = docs_root / "COPY.md"
    copy_path.write_text(_copy_from_intake(intake), encoding="utf-8")

    site_map_path = docs_root / "SITE_MAP.md"
    site_map_path.write_text(_site_map_from_intake(intake), encoding="utf-8")

    local_seo_path = docs_root / "LOCAL_SEO.md"
    local_seo_path.write_text(_local_seo_from_intake(intake), encoding="utf-8")

    # Machine-readable twin so retainer draft executors can reload the intake.
    intake_path = write_intake(docs_root, intake)

    overwritten = {brief_path, copy_path, site_map_path, local_seo_path, intake_path}
    return [
        brief_path,
        copy_path,
        site_map_path,
        local_seo_path,
        intake_path,
        *[p for p in paths if p not in overwritten],
    ]


def scaffold_client_product(
    product_id: str,
    intake: ClientIntake,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Materialize ``products/<product_id>/`` from the web scaffold + intake context."""
    intake.validate()
    paths = load_runtime_paths(repo_root)
    target = paths.repo_root / "products" / product_id
    ctx = intake.to_site_context()
    ctx["PACKAGE_NAME"] = product_id
    written = scaffold_site(target, ctx)
    if not written:
        raise RuntimeError(f"scaffold_site wrote no files under {target}")
    html_paths = [p for p in written if p.suffix in {".astro", ".html"}]
    for path in html_paths:
        leftover = unfilled_tokens(path.read_text(encoding="utf-8"))
        if leftover:
            raise ValueError(f"unfilled tokens in {path}: {leftover}")
    return target


def run_client_launch_checklist(
    dist_dir: Path,
    *,
    gbp_url: str = "",
    analytics_id: str = "",
    deploy_approved: bool = False,
    dns_approved: bool = False,
    pass_threshold: int = 70,
) -> LaunchChecklistReport:
    """Fail-closed pre-launch gate for a paying client site."""
    return run_launch_checklist(
        dist_dir,
        gbp_url=gbp_url,
        analytics_id=analytics_id,
        deploy_approved=deploy_approved,
        dns_approved=dns_approved,
        pass_threshold=pass_threshold,
        first_party=False,
    )


def mark_client_live(
    product_id: str,
    dist_dir: Path,
    *,
    gbp_url: str = "",
    analytics_id: str = "",
    deploy_approved: bool = False,
    dns_approved: bool = False,
    registry_path: Path | None = None,
    pass_threshold: int = 70,
) -> LaunchChecklistReport:
    """Run the launch checklist and set registry ``phase`` to ``live`` when ready."""
    record = get_registry_record(product_id, registry_path=registry_path)
    if record.get("type") != "client-site":
        raise RegistryError(f"{product_id!r} is not a client-site record")

    report = run_client_launch_checklist(
        dist_dir,
        gbp_url=gbp_url,
        analytics_id=analytics_id,
        deploy_approved=deploy_approved,
        dns_approved=dns_approved,
        pass_threshold=pass_threshold,
    )
    if not report.ready:
        failed = ", ".join(i.name for i in report.failures())
        raise LaunchNotReadyError(
            f"launch checklist not ready for {product_id!r}: {failed}"
        )
    set_client_phase(product_id, ProductPhase.LIVE, registry_path=registry_path)
    return report


def mark_prospect_onboarded(
    prospect: ProspectRecord,
    *,
    repo: ProspectRepository | None = None,
) -> ProspectRecord:
    """Set ``engagement_status`` to ``onboarded`` after promotion (operator-set track)."""
    repo = repo or ProspectRepository()
    updated = replace_record(prospect, engagement_status=EngagementStatus.ONBOARDED.value)
    return repo.save(updated)


def client_paths(product_id: str, *, repo_root: Path | None = None) -> tuple[Path, Path]:
    """Return ``(docs_root, source_path)`` for a registry ``product_id``."""
    record = get_registry_record(product_id, registry_path=default_registry_path(repo_root))
    paths = load_runtime_paths(repo_root)
    docs = paths.repo_root / str(record["docs_root"])
    source = paths.repo_root / str(record["source_path"])
    return docs, source


def _copy_from_intake(intake: ClientIntake) -> str:
    services = "\n".join(f"- {s}" for s in intake.services) or "- _TBD_"
    return "\n".join(
        [
            f"# Copy — {intake.business_name}",
            "",
            "> Generated from client intake. Edit before publish.",
            "",
            "## Hero",
            "",
            f"- **H1 direction:** {intake.tagline or f'Trusted {intake.service_category} in {intake.city}'}",
            f"- **Subhead:** Serve {intake.ideal_customer or 'local customers'} in {intake.city}.",
            "",
            "## Services",
            services,
            "",
            "## CTA",
            "",
            f"- Primary: {'Call ' + intake.phone if intake.phone else 'Contact / book'}",
            "",
        ]
    )


def _site_map_from_intake(intake: ClientIntake) -> str:
    return "\n".join(
        [
            f"# Site Map — {intake.business_name}",
            "",
            "> Generated from client intake.",
            "",
            "- `/` — Home (hero, services, social proof, CTA)",
            "- `/`#contact — Contact / hours (footer or section)",
            "",
            f"_Location focus: {intake.city}{(', ' + intake.region) if intake.region else ''}_",
            "",
        ]
    )


def _local_seo_from_intake(intake: ClientIntake) -> str:
    cities = intake.service_area_cities or [intake.city]
    city_rows = "\n".join(
        f"| {service} | {city} | |"
        for service in (intake.services or [intake.service_category])
        for city in cities
    )
    city_yaml = json.dumps(cities)
    service_yaml = json.dumps(intake.services or [intake.service_category])
    radius = "" if intake.travel_radius_miles is None else str(intake.travel_radius_miles)
    return "\n".join(
        [
            f"# Local SEO — {intake.business_name}",
            "",
            "> Generated from client intake. Matrix must be approved before page generation.",
            "",
            "## Primary market",
            "",
            f"- **Primary city:** {intake.city}",
            f"- **State/region:** {intake.region or '_TBD_'}",
            f"- **Travel radius:** {radius or '_TBD_'}",
            f"- **Notes:** {intake.service_area_notes or '_none_'}",
            "",
            "## Service area (SEO pages)",
            "",
            "| Service | City / area | Notes |",
            "|---|---|---|",
            city_rows,
            "",
            "## Matrix YAML (for automation)",
            "",
            "```yaml",
            f'primary_city: "{intake.city}"',
            f'region: "{intake.region}"',
            f"radius_miles: {radius or 'null'}",
            f"service_area_cities: {city_yaml}",
            f"services: {service_yaml}",
            f"notes: \"{intake.service_area_notes}\"",
            f"matrix_approved: {str(intake.matrix_approved).lower()}",
            f'approved_by: "{intake.matrix_approved_by}"',
            f'approved_at: "{intake.matrix_approved_at}"',
            "```",
            "",
        ]
    )
