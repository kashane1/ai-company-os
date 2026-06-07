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

from packages.config.settings import load_runtime_paths
from packages.schemas.offer import (
    BillType,
    BundleQuote,
    ServiceCatalog,
    ServiceTier,
    to_cents,
)

_COMPLIANCE_TEMPLATES = (
    load_runtime_paths().repo_root / "docs" / "agency" / "compliance"
)

# Files seeded for every client workspace. Phase 4 expands these.
WORKSPACE_FILES = (
    "CLIENT_BRIEF.md",
    "OFFER.md",
    "SITE_MAP.md",
    "COPY.md",
    "LOCAL_SEO.md",
    "BOOKING.md",
    "REVIEWS.md",
    "MAINTENANCE_PLAN.md",
    "LAUNCH_CHECKLIST.md",
)


def slugify(name: str) -> str:
    # Drop apostrophes/quotes so "Joe's Plumbing" -> "joes-plumbing" (not
    # "joe-s-plumbing"), then collapse any other run of non-alphanumerics.
    cleaned = re.sub(r"['’\"]", "", name.strip().lower())
    slug = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    return slug or "client"


def render_offer(
    catalog: ServiceCatalog,
    bundle_id: str | None = None,
    *,
    client_name: str,
    service_ids: list[str] | None = None,
    payment_link: str = "",
    payment_expires_at: str = "",
) -> str:
    """Render OFFER.md for a named bundle OR an arbitrary custom service set.

    Pass ``bundle_id`` for a package (curated promo) or ``service_ids`` for a
    build-your-own cart (tier discount). Exactly one must be given.
    """
    if bundle_id is not None:
        quote = catalog.quote_bundle(bundle_id)
        package_name = catalog.bundles[bundle_id].name
    elif service_ids is not None:
        quote = catalog.quote_services(service_ids)
        package_name = "Custom bundle"
    else:
        raise ValueError("render_offer: pass either bundle_id or service_ids")
    lines = [
        f"# Offer — {client_name}",
        "",
        "> Rendered from `packages/agency/catalog.yaml`. Do not hand-edit prices;",
        "> override per-client terms explicitly and note the deviation below.",
        "",
        f"**Package:** {package_name}",
        "",
        _headline_price(quote),
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
    if payment_link:
        # Paying the link = accepting the offer (G3). Stripe Checkout links
        # expire (≤24h), so the expiry is stamped — regenerate when stale.
        expiry = f" _(link expires {payment_expires_at})_" if payment_expires_at else ""
        lines += [
            "",
            "## Pay & start",
            "",
            f"[Pay setup + first month →]({payment_link}){expiry}",
        ]
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
            f"{_headline_price(quote)} "
            f"Includes: {included}.",
        ]
    return "\n".join(lines) + "\n"


def _num(value: float) -> float | int:
    """Whole dollars render as ints (699, not 699.0); keep cents otherwise."""
    return int(value) if float(value).is_integer() else round(value, 2)


def _headline_price(quote: BundleQuote) -> str:
    """The bold setup+monthly line, showing the bundle discount when present."""
    setup = _money(quote.setup_after_discount)
    monthly = _money(quote.monthly_total)
    if quote.savings_cents > 0:
        gross = _money(quote.setup_gross)
        save = _money(quote.savings)
        return f"**{setup} setup ({gross} − {save} bundle discount) + {monthly}/mo.**"
    return f"**{setup} setup + {monthly}/mo.**"


def render_catalog_json(catalog: ServiceCatalog) -> dict[str, object]:
    """Catalog → JSON-able dict for the BBW Astro build.

    Single trusted pricing artifact, emitted to ``src/data/packages.json`` and
    consumed by both the landing-page cards, the Build-Your-Own-Bundle island,
    and the ``create-checkout`` Netlify function. Money is **integer cents**
    (``*_cents``); legacy whole-dollar ``setup``/``monthly`` keys are kept for the
    existing Packages cards. Regenerated by ``scripts/agency/render_catalog_json.py``
    with a drift guard in the test suite.
    """
    bundles = []
    for bundle in catalog.bundles.values():
        quote = catalog.quote_bundle(bundle.bundle_id)
        bundles.append(
            {
                "id": bundle.bundle_id,
                "name": bundle.name,
                "description": bundle.description,
                # legacy dollar keys (= price charged, after promo) for the cards
                "setup": _num(quote.setup_after_discount),
                "monthly": _num(quote.monthly_total),
                # authoritative integer cents
                "setup_gross_cents": quote.setup_gross_cents,
                "setup_after_cents": quote.setup_after_cents,
                "monthly_cents": quote.monthly_cents,
                "savings_cents": quote.savings_cents,
                "pricing_mode": quote.pricing_mode,
                "services": [s.name for s in quote.services],
                "service_ids": [s.service_id for s in quote.services],
            }
        )
    services = [
        {
            "id": s.service_id,
            "name": s.name,
            "tier": s.tier.value,
            "bill_type": s.bill_type.value,
            "setup_cents": to_cents(s.setup_fee),
            "monthly_cents": to_cents(s.monthly_fee),
            "blurb": s.includes[0] if s.includes else "",
            "self_serve": s.self_serve,
            "exclusive_group": s.exclusive_group,
            "requires_group": s.requires_group,
        }
        for s in catalog.services.values()
    ]
    discount_tiers = [
        {"min": t.min_services, "max": t.max_services, "pct": t.pct}
        for t in catalog.discount_tiers
    ]
    return {
        "bundles": bundles,
        "services": services,
        "discount_tiers": discount_tiers,
    }


def scaffold_client_workspace(
    docs_root: Path,
    *,
    client_name: str,
    catalog: ServiceCatalog,
    bundle_id: str | None = None,
    service_ids: list[str] | None = None,
    from_prospect: str = "",
) -> list[Path]:
    """Write minimal client-workspace stubs under ``docs_root``. Idempotent.

    Pass ``bundle_id`` for a named package or ``service_ids`` for a custom cart
    (a self-serve build-your-own order has no catalog bundle).
    """
    docs_root.mkdir(parents=True, exist_ok=True)
    (docs_root / "reports").mkdir(exist_ok=True)
    written: list[Path] = []

    contents = {
        "CLIENT_BRIEF.md": _brief_stub(client_name, from_prospect),
        "OFFER.md": render_offer(
            catalog, bundle_id, client_name=client_name, service_ids=service_ids
        ),
        "SITE_MAP.md": _stub("Site Map", client_name, "Pages and structure."),
        "COPY.md": _stub("Copy", client_name, "Page copy."),
        "LOCAL_SEO.md": _local_seo_stub(client_name),
        "BOOKING.md": _stub(
            "Booking",
            client_name,
            "Owner-managed booking URL (Fresha/Booksy/Square/etc.), embed plan, CTA copy.",
        ),
        "REVIEWS.md": _reviews_stub(client_name),
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
    written.extend(_scaffold_compliance(docs_root, client_name))
    return written


def _scaffold_compliance(docs_root: Path, client_name: str) -> list[Path]:
    """Copy agency compliance templates into the client workspace."""
    written: list[Path] = []
    comp_dir = docs_root / "compliance"
    comp_dir.mkdir(exist_ok=True)
    mapping = {
        "COMPLIANCE.md": "COMPLIANCE-template.md",
        "compliance/review-sms-consent-addendum.md": "review-sms-consent-addendum.md",
    }
    for dest_rel, src_name in mapping.items():
        src = _COMPLIANCE_TEMPLATES / src_name
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8").replace("{{CLIENT_NAME}}", client_name)
        dest = docs_root / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        written.append(dest)
    return written


def _local_seo_stub(client_name: str) -> str:
    return "\n".join(
        [
            f"# Local SEO — {client_name}",
            "",
            "> Service × geography matrix for landing pages. Not limited to one metro —",
            "> use the business’s real service area.",
            "",
            "## Primary market",
            "",
            "- **Primary city:** _TBD_ (from intake)",
            "- **State/region:** _TBD_",
            "",
            "## Service area (SEO pages)",
            "",
            "List cities/neighborhoods to generate pages for (one row per cell):",
            "",
            "| Service | City / area | Notes |",
            "|---|---|---|",
            "| _e.g. Drain cleaning_ | _e.g. Tacoma_ | |",
            "",
            "## Matrix YAML (optional, for automation)",
            "",
            "```yaml",
            "primary_city: \"\"",
            "service_area_cities: []  # e.g. [Tacoma, Federal Way, Kent]",
            "services: []",
            "```",
            "",
        ]
    )


def _reviews_stub(client_name: str) -> str:
    return "\n".join(
        [
            f"# Reviews — {client_name}",
            "",
            "> Review requests are **blocked** until `COMPLIANCE.md` is satisfied and",
            "> `compliance/review-sms-consent-addendum.md` is signed.",
            "",
            "- **GBP review link:** _TBD_",
            "- **SMS template (draft):** _TBD — operator approves before send_",
            "- **Cadence:** max 1 per customer / 90 days (default)",
            "",
        ]
    )


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
