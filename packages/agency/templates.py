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

from packages.schemas.offer import ServiceCatalog

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
