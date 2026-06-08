"""Post-cutover domain verification — the safety net for a domain go-live.

After a domain is pointed at Netlify, this confirms the move succeeded **and** —
critically — that it did **not** knock the client's email offline. The plan's
single highest-stakes failure mode is a cutover that silently drops the MX
records; this catches it.

Design (per the plan's "verify independence" guardrail):

* **Multi-resolver, cache-busting.** Every record is read from *both* Google and
  Cloudflare DoH and they must agree — a verify that trusts one cached resolver
  can false-pass right after a change. Disagreement is reported as "still
  propagating," not success.
* **Propagation-aware.** Mismatch ≠ failure: if the resolvers disagree or a record
  isn't there yet, the result is ``propagating`` (re-check later), distinct from
  ``fail`` (resolvers agree it's wrong).
* The HTTPS cert check is an out-of-band liveness probe (the API can't see DNS for
  you). The ``httpx.Client`` is injectable so the whole thing is offline-testable.

This module only READS. It performs no writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import quote

import httpx

from packages.agency.domain_recon import (
    GOOGLE_DOH,
    NETLIFY_APEX_A,
    NETLIFY_APEX_ALIAS,
    _classify_email,
    _clean,
    validate_domain,
)

CLOUDFLARE_DOH = "https://cloudflare-dns.com/dns-query"
_RTYPE = {"A": 1, "CNAME": 5, "MX": 15, "TXT": 16}

# A check is OK (passed), FAIL (resolvers agree it's wrong), or PROPAGATING
# (resolvers disagree / not visible yet — re-check, don't alarm).
OK = "ok"
FAIL = "fail"
PROPAGATING = "propagating"


@dataclass(frozen=True)
class Check:
    name: str
    status: str  # OK | FAIL | PROPAGATING
    detail: str = ""


@dataclass(frozen=True)
class VerifyResult:
    domain: str
    checks: list[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.status == OK for c in self.checks)

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if c.status == FAIL]

    @property
    def propagating(self) -> list[Check]:
        return [c for c in self.checks if c.status == PROPAGATING]

    def to_dict(self) -> dict[str, object]:
        return {
            "domain": self.domain,
            "ok": self.ok,
            "checks": [
                {"name": c.name, "status": c.status, "detail": c.detail} for c in self.checks
            ],
        }


class DomainVerifier:
    """Verifies a domain points at Netlify without breaking email. Injectable client."""

    def __init__(self, *, client: httpx.Client | None = None, timeout: float = 10.0) -> None:
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)

    def _answers(self, base: str, name: str, rtype: str) -> list[str] | None:
        """Return sorted record data from one resolver, or ``None`` on error."""
        try:
            resp = self._client.get(
                f"{base}?name={quote(name, safe='')}&type={_RTYPE[rtype]}",
                headers={"accept": "application/dns-json"},
            )
            if resp.status_code >= 300:
                return None
            answers = resp.json().get("Answer", []) or []
            return sorted(_clean(a["data"]) for a in answers if a.get("data"))
        except httpx.HTTPError:
            return None

    def _consensus(self, name: str, rtype: str) -> tuple[str, list[str]]:
        """Read from both resolvers; return (status, records).

        OK/FAIL only when both resolvers agree; PROPAGATING when they differ or one
        is unreachable.
        """
        g = self._answers(GOOGLE_DOH, name, rtype)
        c = self._answers(CLOUDFLARE_DOH, name, rtype)
        if g is None or c is None:
            return PROPAGATING, (g or c or [])
        if g != c:
            return PROPAGATING, g
        return OK, g

    def verify(
        self,
        raw_domain: str,
        *,
        netlify_site: str,
        expected_email_host: str = "",
        check_https: bool = True,
    ) -> VerifyResult:
        """Verify apex/www → Netlify, cert live, and email records survived.

        ``expected_email_host`` is the email host recon recorded *before* cutover;
        if set, the MX check fails when mail no longer routes there.
        """
        domain = validate_domain(raw_domain)
        site = _clean(netlify_site)
        checks: list[Check] = []

        # 1. Apex → Netlify (ALIAS flattens to the A, or the A fallback itself).
        status, apex = self._consensus(domain, "A")
        apex_ok = NETLIFY_APEX_A in apex or any(NETLIFY_APEX_ALIAS in a for a in apex)
        checks.append(
            Check(
                "apex_points_to_netlify",
                OK if (status == OK and apex_ok) else (FAIL if status == OK else PROPAGATING),
                f"apex A = {apex or 'none'}",
            )
        )

        # 2. www → the netlify.app site.
        status, www = self._consensus(f"www.{domain}", "CNAME")
        www_ok = any(site in w for w in www)
        checks.append(
            Check(
                "www_points_to_netlify",
                OK if (status == OK and www_ok) else (FAIL if status == OK else PROPAGATING),
                f"www → {www or 'none'}",
            )
        )

        # 3. Email survived — the critical safety check.
        if expected_email_host:
            status, mx = self._consensus(domain, "MX")
            still_there = _classify_email(mx) == expected_email_host
            checks.append(
                Check(
                    "email_mx_preserved",
                    OK
                    if (status == OK and still_there)
                    else (FAIL if status == OK else PROPAGATING),
                    f"MX = {mx or 'NONE — mail is broken!'} (expected {expected_email_host})",
                )
            )
            status, spf = self._consensus(domain, "TXT")
            has_spf = any(t.lower().startswith("v=spf1") or "v=spf1" in t.lower() for t in spf)
            checks.append(
                Check(
                    "spf_preserved",
                    OK if (status == OK and has_spf) else (FAIL if status == OK else PROPAGATING),
                    "SPF present" if has_spf else "SPF missing",
                )
            )

        # 4. HTTPS liveness (cert provisioned + serving).
        if check_https:
            checks.append(self._https_check(domain))

        return VerifyResult(domain=domain, checks=checks)

    def _https_check(self, domain: str) -> Check:
        for host in (f"https://www.{domain}", f"https://{domain}"):
            try:
                resp = self._client.get(host)
                if resp.status_code < 500:
                    return Check("https_serving", OK, f"{host} → HTTP {resp.status_code}")
            except httpx.HTTPError:
                continue
        return Check(
            "https_serving", PROPAGATING, "no HTTPS response yet (cert may still be provisioning)"
        )


def render_result(result: VerifyResult) -> str:
    glyph = {OK: "✓", FAIL: "✗", PROPAGATING: "…"}
    lines = [f"# Domain verify — {result.domain}", ""]
    for c in result.checks:
        lines.append(f"- {glyph.get(c.status, '?')} **{c.name}** — {c.detail}")
    verdict = (
        "ALL OK" if result.ok else ("FAIL" if result.failures else "STILL PROPAGATING")
    )
    lines += ["", f"**{verdict}**"]
    return "\n".join(lines) + "\n"
