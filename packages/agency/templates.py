"""Client docs-workspace templates (Agency layer).

Phase 3 owns *minimal stubs* so the promotion step has something to scaffold;
Phase 4 (client intake) fleshes out their content. Each client engagement gets a
workspace under ``docs/products/<slug>-site/`` mirroring the product-artifact
convention.

``OFFER.md`` renders from the service catalog + the signed bundle so the terms
can never silently drift from ``packages/agency/catalog.yaml``.
"""

from __future__ import annotations

import re
from pathlib import Path

from packages.schemas.offer import BillType, ServiceCatalog, ServiceTier

# Files seeded for every client workspace. Phase 4 expands these.
WORKSPACE_FILES = (
    "CLIENT_BRIEF.md",
    "OFFER.md",
    "SITE_MAP.md",
    "COPY.md",
    "LOCAL_SEO.md",
    "MAINTENANCE_PLAN.md",
    "LAUNCH_CHECKLIST.md",
)


def slugify(name: str) -> str:
    # Drop apostrophes/quotes so "Joe's Plumbing" -> "joes-plumbing" (not
    # "joe-s-plumbing"), then collapse any other run of non-alphanumerics.
    cleaned = re.sub(r"['’\"]", "", name.strip().lower())
    slug = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    return slug or "client"


def render_offer(catalog: ServiceCatalog, bundle_id: str, *, client_name: str) -> str:
    quote = catalog.quote_bundle(bundle_id)
    bundle = catalog.bundles[bundle_id]
    lines = [
        f"# Offer — {client_name}",
        "",
        "> Rendered from `packages/agency/catalog.yaml`. Do not hand-edit prices;",
        "> override per-client terms explicitly and note the deviation below.",
        "",
        f"**Package:** {bundle.name}",
        "",
        f"**{_money(quote.setup_total)} setup + {_money(quote.monthly_total)}/mo**",
        "",
        "## Included services",
        "",
        "| Service | Setup | Monthly |",
        "|---|---|---|",
    ]
    for service in quote.services:
        setup = _money(service.setup_fee) if service.setup_fee else "—"
        monthly = f"{_money(service.monthly_fee)}/mo" if service.monthly_fee else "—"
        lines.append(f"| {service.name} | {setup} | {monthly} |")
    lines += ["", "## Per-client overrides", "", "_None._", ""]
    return "\n".join(lines) + "\n"


TIER_LABELS = {
    ServiceTier.TIER_1: "Tier 1 — Easy add-ons",
    ServiceTier.TIER_2: "Tier 2 — High value",
    ServiceTier.TIER_3: "Tier 3 — Recurring-revenue goldmine",
    ServiceTier.TIER_4: "Tier 4 — Fractional-CTO bespoke",
}


def render_service_catalog(catalog: ServiceCatalog) -> str:
    """Render the human-readable catalog mirror (``docs/agency/service-catalog.md``).

    Peer of :func:`render_offer` — string-in/string-out, offline. The committed
    mirror must equal this output (drift guard in the test suite), so repricing the
    YAML regenerates the doc instead of silently desyncing it. Run
    ``scripts/agency/render_catalog_md.py`` after editing the catalog.
    """
    lines = [
        "# Agency Service Catalog",
        "",
        "> Generated render of `packages/agency/catalog.yaml` (the typed source of",
        "> truth, validated by `packages/agency/catalog.py`). Do not edit prices here —",
        "> edit the YAML and regenerate. Client `OFFER.md` files render from the same data.",
        "",
        "## Services",
    ]
    for tier in ServiceTier:
        tier_services = [s for s in catalog.services.values() if s.tier is tier]
        if not tier_services:
            continue
        lines += [
            "",
            f"### {TIER_LABELS[tier]}",
            "",
            "| Service | Bill | Setup | Monthly |",
            "|---|---|---|---|",
        ]
        for s in tier_services:
            bill = "one-time" if s.bill_type is BillType.ONE_TIME else "recurring"
            setup = _money(s.setup_fee) if s.setup_fee else "—"
            monthly = f"{_money(s.monthly_fee)}/mo" if s.monthly_fee else "—"
            lines.append(f"| {s.name} (`{s.service_id}`) | {bill} | {setup} | {monthly} |")
    lines += ["", "## Bundles"]
    for bundle in catalog.bundles.values():
        quote = catalog.quote_bundle(bundle.bundle_id)
        included = ", ".join(s.name for s in quote.services)
        lines += [
            "",
            f"### {bundle.name}",
            "",
            bundle.description,
            "",
            f"**{_money(quote.setup_total)} setup + {_money(quote.monthly_total)}/mo.** "
            f"Includes: {included}.",
        ]
    return "\n".join(lines) + "\n"


def scaffold_client_workspace(
    docs_root: Path,
    *,
    client_name: str,
    bundle_id: str,
    catalog: ServiceCatalog,
    from_prospect: str = "",
) -> list[Path]:
    """Write minimal client-workspace stubs under ``docs_root``. Idempotent."""
    docs_root.mkdir(parents=True, exist_ok=True)
    (docs_root / "reports").mkdir(exist_ok=True)
    written: list[Path] = []

    contents = {
        "CLIENT_BRIEF.md": _brief_stub(client_name, from_prospect),
        "OFFER.md": render_offer(catalog, bundle_id, client_name=client_name),
        "SITE_MAP.md": _stub("Site Map", client_name, "Pages and structure."),
        "COPY.md": _stub("Copy", client_name, "Page copy."),
        "LOCAL_SEO.md": _stub(
            "Local SEO", client_name, "GBP, citations, target keywords, service x geo matrix."
        ),
        "MAINTENANCE_PLAN.md": _stub(
            "Maintenance Plan", client_name, "What the retainer covers, edit limits, SLA."
        ),
        "LAUNCH_CHECKLIST.md": _stub(
            "Launch Checklist",
            client_name,
            "domain, DNS, SSL, contact form, mobile test, SEO metadata, GBP link, analytics.",
        ),
    }
    for name in WORKSPACE_FILES:
        path = docs_root / name
        path.write_text(contents[name])
        written.append(path)
    return written


def _brief_stub(client_name: str, from_prospect: str) -> str:
    return "\n".join(
        [
            f"# Client Brief — {client_name}",
            "",
            "> Stub created at promotion (Phase 3). Filled in by `client-intake` (Phase 4).",
            "",
            f"- **From prospect:** `{from_prospect or 'n/a'}`",
            "- **Business type:** _TBD_",
            "- **Services:** _TBD_",
            "- **Location:** _TBD_",
            "- **Ideal customer:** _TBD_",
            "- **Hours:** _TBD_",
            "",
        ]
    )


def _stub(title: str, client_name: str, hint: str) -> str:
    return f"# {title} — {client_name}\n\n> Stub (Phase 3). {hint}\n"


def _money(value: float) -> str:
    return f"${value:,.0f}"
