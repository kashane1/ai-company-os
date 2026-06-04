"""Business email setup (Agency layer, G5 — Package C service).

A repeatable runbook + a typed completion record. The runbook (``BUSINESS_EMAIL.md``)
is the checklist the operator follows in Google Workspace (verify domain, set MX,
create ``info@/support@/sales@`` aliases); :class:`BusinessEmailSetup` records that
the service was delivered so the platform — not just a human's memory — knows.

Low-tech by design (no provisioning API yet); the value is a consistent procedure
and a durable "done" marker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from packages.config.settings import load_runtime_paths
from packages.db.json_store import JsonStore

DEFAULT_ALIASES = ("info", "support", "sales")
_RECORD_ID = "business-email"


def derive_domain(site_url: str) -> str:
    """Best-effort domain from a site URL ('https://www.joe.com/x' -> 'joe.com')."""
    host = urlsplit(site_url).hostname or site_url.strip().strip("/")
    return host[4:] if host.startswith("www.") else host


def render_business_email_runbook(
    business_name: str,
    domain: str,
    *,
    provider: str = "Google Workspace",
    aliases: tuple[str, ...] = DEFAULT_ALIASES,
) -> str:
    addresses = [f"{a}@{domain}" for a in aliases]
    alias_lines = [f"- [ ] Create `{addr}`" for addr in addresses]
    return "\n".join(
        [
            f"# Business Email Setup — {business_name}",
            "",
            f"> Operator runbook. Provider: **{provider}**. Domain: **{domain}**.",
            "",
            "## 1. Account",
            "",
            f"- [ ] Sign the business up for {provider}",
            "- [ ] Set the primary mailbox (owner)",
            "",
            "## 2. Verify the domain",
            "",
            f"- [ ] Add the {provider} verification **TXT** record to {domain}'s DNS",
            "- [ ] Confirm verification in the admin console",
            "",
            "## 3. Mail routing (MX)",
            "",
            f"- [ ] Replace existing MX records on {domain} with {provider}'s MX records",
            "- [ ] Wait for propagation; send a test message in and out",
            "",
            "## 4. Aliases",
            "",
            *alias_lines,
            "",
            "## 5. Wire it in",
            "",
            "- [ ] Use the new address on the website contact section and forms",
            "- [ ] Add it to the Google Business Profile",
            "",
            "> Mark done with `setup_business_email.py --mark-complete` once mail flows.",
            "",
        ]
    )


def emit_business_email_runbook(
    business_name: str,
    docs_root: Path,
    *,
    domain: str,
    provider: str = "Google Workspace",
    aliases: tuple[str, ...] = DEFAULT_ALIASES,
) -> Path:
    docs_root.mkdir(parents=True, exist_ok=True)
    path = docs_root / "BUSINESS_EMAIL.md"
    path.write_text(
        render_business_email_runbook(
            business_name, domain, provider=provider, aliases=aliases
        ),
        encoding="utf-8",
    )
    return path


@dataclass(frozen=True)
class BusinessEmailSetup:
    product_id: str
    domain: str
    provider: str = "Google Workspace"
    aliases: list[str] = field(default_factory=lambda: list(DEFAULT_ALIASES))
    mx_configured: bool = False
    verified: bool = False
    completed_at: str = ""

    def validate(self) -> None:
        if not self.product_id.strip():
            raise ValueError("business email: product_id is required")
        if not self.domain.strip():
            raise ValueError("business email: domain is required")

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "domain": self.domain,
            "provider": self.provider,
            "aliases": list(self.aliases),
            "mx_configured": self.mx_configured,
            "verified": self.verified,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "BusinessEmailSetup":
        return cls(
            product_id=str(payload["product_id"]),
            domain=str(payload["domain"]),
            provider=str(payload.get("provider", "Google Workspace")),
            aliases=[str(a) for a in list(payload.get("aliases", DEFAULT_ALIASES))],
            mx_configured=bool(payload.get("mx_configured", False)),
            verified=bool(payload.get("verified", False)),
            completed_at=str(payload.get("completed_at", "")),
        )


def _client_services_store(product_id: str, root: Path | None = None) -> JsonStore:
    base = root or (load_runtime_paths().state_root / "clients" / product_id / "services")
    return JsonStore(base)


def save_business_email_setup(record: BusinessEmailSetup, *, root: Path | None = None) -> Path:
    record.validate()
    return _client_services_store(record.product_id, root).save(_RECORD_ID, record.to_dict())


def load_business_email_setup(
    product_id: str, *, root: Path | None = None
) -> BusinessEmailSetup | None:
    store = _client_services_store(product_id, root)
    if not store.path_for(_RECORD_ID).exists():
        return None
    return BusinessEmailSetup.from_dict(store.load(_RECORD_ID))
