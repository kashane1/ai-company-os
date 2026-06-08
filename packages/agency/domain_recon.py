"""Domain readiness recon — read a client's public DNS + registration state.

The first preemptive capability for bring-your-own-domain onboarding (see
``docs/plans/2026-06-07-feat-agency-domain-onboarding-automation-plan.md``). Given
only a domain *name* — before any client access — this reads **public** state over
HTTPS and produces a readiness report:

* **RDAP** (``rdap.org`` redirector) → registrar + nameservers + DNSSEC/transfer
  signals. Many ccTLDs (``.io``, ``.co``) lack RDAP — we degrade to DNS-only and
  label the registrar unknown rather than failing.
* **DNS-over-HTTPS** (Google primary, Cloudflare cross-check) → A/AAAA/MX/TXT/NS,
  from which we classify the **DNS provider** (→ does the apex support an
  ALIAS/flattened-CNAME, or only an A record?) and the **email host** (the records
  that MUST survive a cutover — the single biggest hazard).

Security posture: the domain is **untrusted input** (it can come from a public
form), so :func:`validate_domain` runs first — hostname-shape validation + IDNA
normalization — and every value is URL-encoded into the request, never raw-concat.
This module only ever READS; it performs no writes and needs no credentials. The
``httpx.Client`` is injectable so the whole thing is unit-testable with
``httpx.MockTransport`` — no network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import quote

import httpx

# Public DoH resolvers. Both speak the same JSON schema (Cloudflare copied
# Google's), so one parser handles both; we cross-check to defend against
# propagation lag / a single-resolver blip.
GOOGLE_DOH = "https://dns.google/resolve"
CLOUDFLARE_DOH = "https://cloudflare-dns.com/dns-query"
RDAP_BOOTSTRAP = "https://rdap.org/domain"

# DNS record type numbers (DoH returns/accepts the numeric type).
_RTYPE = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "MX": 15, "TXT": 16, "AAAA": 28}

# Current Netlify external-DNS targets (confirmed 2026-06-07 — see plan Research
# Insights). The apex CANNOT be a plain CNAME; use ALIAS/ANAME where supported,
# else the single A-record fallback. No AAAA (breaks Netlify cert provisioning).
NETLIFY_APEX_ALIAS = "apex-loadbalancer.netlify.com"
NETLIFY_APEX_A = "75.2.60.5"

# NS suffix → (provider label, apex-can-point-at-a-hostname?). The capability flag
# is the one variable that matters: a no-ALIAS registrar (GoDaddy/Namecheap)
# forces the A-record fallback for the apex.
_NS_PROVIDERS: tuple[tuple[str, str, bool], ...] = (
    ("cloudflare.com", "Cloudflare", True),
    ("awsdns", "AWS Route 53", True),
    ("domaincontrol.com", "GoDaddy", False),
    ("registrar-servers.com", "Namecheap", False),
    ("nsone.net", "NS1", True),
    ("netlifydns.com", "Netlify DNS", True),
    ("netlify.com", "Netlify DNS", True),
    ("googledomains.com", "Google Domains", False),
    ("google.com", "Google Cloud DNS", False),
    ("dnsmadeeasy.com", "DNS Made Easy", True),
    ("azure-dns", "Azure DNS", True),
    ("vercel-dns.com", "Vercel", True),
    ("digitalocean.com", "DigitalOcean", False),
)

# MX target suffix → email host. If MX exists and points somewhere, those records
# (plus SPF/DKIM/DMARC) are "never-delete" during any cutover.
_MX_HOSTS: tuple[tuple[str, str], ...] = (
    ("mail.protection.outlook.com", "Microsoft 365"),
    ("mx.microsoft", "Microsoft 365"),  # new format for domains added >= 2026-07-01
    ("google.com", "Google Workspace"),
    ("googlemail.com", "Google Workspace"),
    ("pphosted.com", "Proofpoint"),
    ("mimecast.com", "Mimecast"),
    ("zoho.com", "Zoho Mail"),
    ("zoho.eu", "Zoho Mail"),
    ("secureserver.net", "GoDaddy email"),
    ("improvmx.com", "ImprovMX (forwarding)"),
    ("forwardemail.net", "Forward Email (forwarding)"),
    ("mailgun.org", "Mailgun"),
    ("yandex.net", "Yandex"),
)

# Hostname label: letters/digits/hyphen, not starting/ending with hyphen, 1-63 chars.
_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")


class DomainValidationError(ValueError):
    """Raised when an untrusted domain string fails hostname-shape validation."""


class DomainReconError(RuntimeError):
    """Raised when a recon HTTP call fails irrecoverably."""


def validate_domain(raw: str) -> str:
    """Normalize + validate an untrusted domain string to a punycode A-label host.

    Rejects anything carrying a scheme, path, port, ``@``, whitespace, CR/LF, or
    query characters — i.e. anything that isn't a bare registrable hostname — so it
    can't pivot the RDAP/DoH request. IDN is normalized to its ASCII A-label
    (IDNA2008-ish via the stdlib ``idna`` codec). The result is safe to URL-encode
    into a request path/query.
    """
    if raw is None:
        raise DomainValidationError("domain is required")
    s = raw.strip().lower().rstrip(".")
    if not s:
        raise DomainValidationError("domain is empty")
    # Reject obvious URL/injection shapes before anything else.
    if any(c in s for c in ("/", "\\", "@", ":", "?", "#", "&", "=", " ", "\t", "\n", "\r")):
        raise DomainValidationError(f"not a bare hostname: {raw!r}")
    # Normalize IDN to punycode; rejects mixed-script garbage the codec can't encode.
    try:
        s = s.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise DomainValidationError(f"invalid internationalized domain: {raw!r}") from exc
    labels = s.split(".")
    if len(labels) < 2:
        raise DomainValidationError(f"need a registrable domain (got {raw!r})")
    for label in labels:
        if not _LABEL.match(label):
            raise DomainValidationError(f"invalid label {label!r} in {raw!r}")
    return s


@dataclass(frozen=True)
class DomainReport:
    """Machine-readable recon result (rendered to a human report by callers)."""

    domain: str
    registrar: str = ""  # "" when RDAP unavailable for the TLD
    rdap_available: bool = False
    nameservers: list[str] = field(default_factory=list)
    dns_provider: str = ""
    apex_alias_supported: bool = False
    dnssec: bool = False
    a_records: list[str] = field(default_factory=list)
    has_aaaa: bool = False
    www_target: str = ""
    mx_records: list[str] = field(default_factory=list)  # "<pri> <host>"
    email_host: str = ""
    has_spf: bool = False
    has_dkim: bool = False
    dmarc_policy: str = ""  # "", "none", "quarantine", "reject"
    recommended_strategy: str = "external"  # "external" | "managed"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "domain": self.domain,
            "registrar": self.registrar,
            "rdap_available": self.rdap_available,
            "nameservers": list(self.nameservers),
            "dns_provider": self.dns_provider,
            "apex_alias_supported": self.apex_alias_supported,
            "dnssec": self.dnssec,
            "a_records": list(self.a_records),
            "has_aaaa": self.has_aaaa,
            "www_target": self.www_target,
            "mx_records": list(self.mx_records),
            "email_host": self.email_host,
            "has_spf": self.has_spf,
            "has_dkim": self.has_dkim,
            "dmarc_policy": self.dmarc_policy,
            "recommended_strategy": self.recommended_strategy,
            "notes": list(self.notes),
        }


class DomainRecon:
    """Reads public RDAP + DoH state for a domain. Injectable client for tests."""

    def __init__(self, *, client: httpx.Client | None = None, timeout: float = 10.0) -> None:
        # follow_redirects: rdap.org is a 302 redirector to the registry RDAP host.
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)

    # ── low-level queries ────────────────────────────────────────────────
    def _doh(self, name: str, rtype: str) -> list[dict]:
        """Query DoH for ``name``/``rtype``; Google primary, Cloudflare fallback.

        Returns the ``Answer`` array (empty for NODATA/NXDOMAIN). ``name`` is
        URL-encoded — never raw-concatenated.
        """
        qname = quote(name, safe="")
        qtype = _RTYPE[rtype]
        # Google first.
        try:
            resp = self._client.get(
                f"{GOOGLE_DOH}?name={qname}&type={qtype}",
                headers={"accept": "application/dns-json"},
            )
            if resp.status_code < 300:
                return list(resp.json().get("Answer", []) or [])
        except httpx.HTTPError:
            pass
        # Cloudflare cross-check / fallback.
        try:
            resp = self._client.get(
                f"{CLOUDFLARE_DOH}?name={qname}&type={qtype}",
                headers={"accept": "application/dns-json"},
            )
            if resp.status_code < 300:
                return list(resp.json().get("Answer", []) or [])
        except httpx.HTTPError as exc:
            raise DomainReconError(f"DoH query failed for {name} {rtype}: {exc}") from exc
        return []

    def _rdap(self, domain: str) -> dict | None:
        """Fetch RDAP JSON, or ``None`` if the TLD has no RDAP / lookup fails."""
        try:
            resp = self._client.get(f"{RDAP_BOOTSTRAP}/{quote(domain, safe='')}")
        except httpx.HTTPError:
            return None
        # A 404 with NO redirect history = rdap.org had no RDAP service for the TLD
        # (the ccTLD gap). A 404 after a redirect = registry says "available".
        if resp.status_code >= 300:
            return None
        try:
            return resp.json()
        except ValueError:
            return None

    # ── public API ───────────────────────────────────────────────────────
    def recon(self, raw_domain: str) -> DomainReport:
        domain = validate_domain(raw_domain)
        notes: list[str] = []

        rdap = self._rdap(domain)
        registrar, rdap_ns, dnssec = _parse_rdap(rdap)
        rdap_available = rdap is not None
        if not rdap_available:
            notes.append(
                "No RDAP for this TLD (common for .io/.co/ccTLDs) — registrar "
                "unknown; derived from DNS only."
            )

        ns = [_clean(a["data"]) for a in self._doh(domain, "NS") if a.get("data")]
        nameservers = sorted({n for n in ns if n}) or rdap_ns
        provider, apex_alias = _classify_provider(nameservers)

        a_records = [_clean(a["data"]) for a in self._doh(domain, "A") if a.get("data")]
        has_aaaa = bool(self._doh(domain, "AAAA"))
        www = self._doh(f"www.{domain}", "CNAME") or self._doh(f"www.{domain}", "A")
        www_target = _clean(www[0]["data"]) if www and www[0].get("data") else ""

        mx_answers = [a["data"] for a in self._doh(domain, "MX") if a.get("data")]
        mx_records = sorted(_clean(m) for m in mx_answers)
        email_host = _classify_email(mx_records)
        if email_host:
            notes.append(
                f"Email runs through {email_host} — its MX + SPF/DKIM/DMARC records "
                "MUST be preserved on any DNS change or inbound mail breaks."
            )

        txt = [_txt(a.get("data", "")) for a in self._doh(domain, "TXT")]
        has_spf = any(t.lower().startswith("v=spf1") for t in txt)
        dmarc_txt = [_txt(a.get("data", "")) for a in self._doh(f"_dmarc.{domain}", "TXT")]
        dmarc_policy = _dmarc_policy(dmarc_txt)
        has_dkim = bool(self._doh(f"google._domainkey.{domain}", "TXT")) or bool(
            self._doh(f"selector1._domainkey.{domain}", "CNAME")
        )

        if dnssec:
            notes.append(
                "DNSSEC is enabled — a nameserver move needs the DS record at the "
                "registrar disabled before cutover, re-enabled after, or resolution breaks."
            )
        if not apex_alias and nameservers:
            notes.append(
                f"{provider or 'this DNS provider'} has no apex ALIAS — point the apex "
                f"at the A-record fallback {NETLIFY_APEX_A} (or move DNS to a flattening provider)."
            )

        # Recommend managed DNS only when the apex can't be aliased where it is AND
        # there's no email to risk; otherwise the lighter external path is safer.
        strategy = "managed" if (not apex_alias and not email_host) else "external"

        return DomainReport(
            domain=domain,
            registrar=registrar,
            rdap_available=rdap_available,
            nameservers=nameservers,
            dns_provider=provider,
            apex_alias_supported=apex_alias,
            dnssec=dnssec,
            a_records=sorted(a_records),
            has_aaaa=has_aaaa,
            www_target=www_target,
            mx_records=mx_records,
            email_host=email_host,
            has_spf=has_spf,
            has_dkim=has_dkim,
            dmarc_policy=dmarc_policy,
            recommended_strategy=strategy,
            notes=notes,
        )


# ── parsing helpers ──────────────────────────────────────────────────────
def _clean(value: str) -> str:
    """Lowercase + strip the trailing dot DoH puts on names."""
    return str(value).strip().rstrip(".").lower()


def _txt(value: str) -> str:
    """Unquote/concatenate a DoH TXT ``data`` field (segments come quoted)."""
    return re.sub(r'"\s*"', "", str(value).strip().strip('"'))


def _parse_rdap(rdap: dict | None) -> tuple[str, list[str], bool]:
    if not rdap:
        return "", [], False
    registrar = ""
    for entity in rdap.get("entities", []) or []:
        roles = entity.get("roles", []) or []
        if "registrar" in roles:
            registrar = _vcard_fn(entity) or registrar
    nameservers = sorted(
        _clean(ns.get("ldhName", ""))
        for ns in rdap.get("nameservers", []) or []
        if ns.get("ldhName")
    )
    dnssec = bool((rdap.get("secureDNS") or {}).get("delegationSigned"))
    return registrar, nameservers, dnssec


def _vcard_fn(entity: dict) -> str:
    """Pull the formatted-name (fn) out of an RDAP jCard (array-of-arrays)."""
    try:
        for item in entity["vcardArray"][1]:
            if item and item[0] == "fn":
                return str(item[3])
    except (KeyError, IndexError, TypeError):
        pass
    return ""


def _classify_provider(nameservers: list[str]) -> tuple[str, bool]:
    for ns in nameservers:
        for suffix, label, alias in _NS_PROVIDERS:
            if suffix in ns:
                return label, alias
    return ("", False) if not nameservers else ("custom/unknown", False)


def _classify_email(mx_records: list[str]) -> str:
    for record in mx_records:
        target = record.split()[-1] if record.split() else ""
        for suffix, label in _MX_HOSTS:
            if target.endswith(suffix) or suffix in target:
                return label
    return ""


def _dmarc_policy(txts: list[str]) -> str:
    for t in txts:
        if t.lower().startswith("v=dmarc1"):
            m = re.search(r"\bp\s*=\s*(none|quarantine|reject)", t, re.IGNORECASE)
            return m.group(1).lower() if m else "none"
    return ""


# ── instruction generation (the external-DNS path's final form) ──────────
def netlify_external_dns_instructions(report: DomainReport, netlify_site: str) -> str:
    """Render copy-paste DNS records to point this domain at a Netlify site.

    Constant Netlify targets + the client's own email records carried over
    untouched. ``netlify_site`` is the ``<name>.netlify.app`` host (the www CNAME
    target). The apex line adapts to whether the provider supports ALIAS.
    """
    apex = (
        f"| `@` (apex) | ALIAS/ANAME | `{NETLIFY_APEX_ALIAS}` |"
        if report.apex_alias_supported
        else f"| `@` (apex) | A | `{NETLIFY_APEX_A}` |  ← no ALIAS at "
        f"{report.dns_provider or 'provider'}"
    )
    lines = [
        f"## DNS records — point {report.domain} at Netlify",
        "",
        f"DNS provider: **{report.dns_provider or 'unknown'}** · registrar: "
        f"**{report.registrar or 'unknown'}**",
        "",
        "| Host | Type | Value |",
        "|---|---|---|",
        apex,
        f"| `www` | CNAME | `{netlify_site}` |",
        "",
        "- Set **one** apex record only; do **not** add an AAAA/IPv6 record "
        "(it breaks Netlify's cert).",
    ]
    if report.email_host:
        lines += [
            "",
            f"> ⚠️ **Do not touch the email records.** This domain receives mail via "
            f"**{report.email_host}**. Leave the MX"
            + (" + SPF" if report.has_spf else "")
            + (" + DKIM" if report.has_dkim else "")
            + (f" + DMARC (p={report.dmarc_policy})" if report.dmarc_policy else "")
            + " records exactly as they are.",
        ]
    return "\n".join(lines) + "\n"


def render_report(report: DomainReport) -> str:
    """Human-readable readiness report (the Phase-1 transient artifact)."""
    r = report
    apex = (
        "ALIAS/flattened CNAME supported" if r.apex_alias_supported else "A-record only (no ALIAS)"
    )
    lines = [
        f"# Domain readiness — {r.domain}",
        "",
        f"- **Registrar:** {r.registrar or '_unknown (no RDAP for this TLD)_'}",
        f"- **Nameservers:** {', '.join(r.nameservers) or '_none resolved_'}",
        f"- **DNS provider:** {r.dns_provider or '_unknown_'} ({apex})",
        f"- **DNSSEC:** {'enabled' if r.dnssec else 'off'}",
        f"- **Current A:** {', '.join(r.a_records) or '_none_'}"
        + (" + AAAA present" if r.has_aaaa else ""),
        f"- **www →** {r.www_target or '_none_'}",
        f"- **Email host:** {r.email_host or '_no MX / none detected_'}",
        f"- **MX:** {', '.join(r.mx_records) or '_none_'}",
        f"- **SPF / DKIM / DMARC:** "
        f"{'SPF' if r.has_spf else '–'} / {'DKIM' if r.has_dkim else '–'} / "
        f"{('DMARC p=' + r.dmarc_policy) if r.dmarc_policy else '–'}",
        f"- **Recommended strategy:** {r.recommended_strategy}",
        "",
        "## Notes",
    ]
    lines += [f"- {n}" for n in r.notes] or ["- _none_"]
    return "\n".join(lines) + "\n"
