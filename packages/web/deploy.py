"""Web deploy seam — publish a built site behind a pluggable target (F4).

Building a site (WEB lane) and *publishing* it (WEBDEPLOY lane) are separate
concerns, so deployment lives behind a ``DeployTarget`` seam — exactly like the
connector/store seams elsewhere in the repo. The first adapter is **Netlify**
(its free tier permits commercial use, unlike Vercel Hobby), but nothing above
this interface knows that.

Design choices that matter:

* **Account is explicit.** Every site belongs to a :class:`DeployAccount`. That
  abstraction is what makes the later *client-handoff* mode possible —
  :meth:`DeployTarget.transfer_ownership` moves a site to a client's account
  without the rest of the platform changing.
* **Production vs preview is a parameter.** Preview deploys are cheap and
  ungated; a production deploy is the gated action (see
  ``packages/policies/deploy_readiness.py``). This module performs deploys; it
  does **not** decide whether one is allowed — that's policy, enforced by the
  WEBDEPLOY worker before it calls :meth:`deploy`.
* **Custom domain / DNS is its own method** so the gate can require approval for
  it specifically.

The HTTP client is injectable, so the Netlify adapter is fully unit-testable
with ``httpx.MockTransport`` — no network, no token.
"""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import httpx

from packages.config.settings import NETLIFY_AUTH_TOKEN_ENV_VAR, get_api_key

NETLIFY_API = "https://api.netlify.com/api/v1"


class DeployError(RuntimeError):
    """Raised when a deploy target call fails or is misconfigured."""


class SecretLeakError(DeployError):
    """Raised when a build artifact would ship a credential to the public web."""


# Credential-shaped patterns that must never reach a published ``dist/`` (todo
# 075). The file-digest deploy uploads everything under ``dist/`` wholesale, so a
# secret inlined into a built page/function/JSON ships publicly. We scan first
# and fail closed. Patterns are deliberately specific (length/word-boundaries) to
# avoid blocking a legitimate deploy on a coincidental match. NOTE: Google API
# keys (``AIza…``) are intentionally NOT listed — the demo Maps key is meant to
# be HTTP-referrer-restricted and embedded in client markup (see demo_maps.py).
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("stripe_secret_key", re.compile(r"\b[sr]k_(?:live|test)_[0-9A-Za-z]{8,}")),
    ("stripe_webhook_secret", re.compile(r"\bwhsec_[0-9A-Za-z]{8,}")),
    ("resend_api_key", re.compile(r"\bre_[0-9A-Za-z]{16,}")),
    ("twilio_sid_or_key", re.compile(r"\b(?:AC|SK)[0-9a-f]{32}\b")),
    ("slack_webhook", re.compile(r"hooks\.slack\.com/services/")),
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{20,}")),
    ("forward_secret_literal", re.compile(r"FORWARD_SECRET[\"'\s]*[:=][\"'\s]*\S{8,}")),
)

# Binary asset suffixes that can't carry a text secret — skip to keep the scan
# fast and avoid spurious matches on packed bytes.
_BINARY_SUFFIXES = frozenset(
    {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico", ".bmp",
        ".woff", ".woff2", ".ttf", ".otf", ".eot",
        ".mp4", ".webm", ".mov", ".mp3", ".wav", ".pdf", ".zip", ".gz", ".br",
    }
)

# Cap per-file read so a giant artifact can't stall the scan.
_SCAN_MAX_BYTES = 5_000_000


def scan_dist_for_secrets(dist_dir: Path) -> list[str]:
    """Return human-readable findings for any credential-shaped string in ``dist``.

    Recursive over every text-readable file. Empty list == clean.
    """
    findings: list[str] = []
    for path in sorted(dist_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() in _BINARY_SUFFIXES:
            continue
        try:
            text = path.read_bytes()[:_SCAN_MAX_BYTES].decode("utf-8", "ignore")
        except OSError:
            continue
        rel = path.relative_to(dist_dir).as_posix()
        for label, pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(f"{rel}: looks like a {label}")
    return findings


def assert_no_secret_leak(dist_dir: Path) -> None:
    """Fail closed if ``dist`` contains a credential-shaped string (todo 075)."""
    findings = scan_dist_for_secrets(dist_dir)
    if findings:
        raise SecretLeakError(
            "refusing to deploy — build artifacts may leak secrets:\n  "
            + "\n  ".join(findings)
        )


@dataclass(frozen=True)
class DeployAccount:
    """An account/team that can own sites. ``id`` is the host's account slug."""

    id: str
    name: str = ""


@dataclass(frozen=True)
class SiteRef:
    site_id: str
    name: str
    url: str = ""
    account_id: str = ""


@dataclass(frozen=True)
class DeployResult:
    site: SiteRef
    deploy_id: str
    url: str
    production: bool
    state: str = ""


@runtime_checkable
class DeployTarget(Protocol):
    """Publish a built ``dist`` directory and manage its hosting."""

    name: str

    def ensure_site(self, name: str, *, account: DeployAccount | None = None) -> SiteRef:
        ...

    def deploy(self, site: SiteRef, dist_dir: Path, *, production: bool = False) -> DeployResult:
        ...

    def set_custom_domain(self, site: SiteRef, domain: str) -> SiteRef:
        ...

    def transfer_ownership(self, site: SiteRef, to_account: DeployAccount) -> SiteRef:
        ...


def zip_dist(dist_dir: Path) -> bytes:
    """Zip a built site directory into bytes (the Netlify zip-deploy payload)."""
    if not dist_dir.is_dir():
        raise DeployError(f"dist directory not found: {dist_dir}")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(dist_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(dist_dir).as_posix())
    return buffer.getvalue()


class NetlifyDeployTarget:
    """``DeployTarget`` backed by the Netlify API.

    The token is read from ``$NETLIFY_AUTH_TOKEN`` (a gated secret) unless passed
    explicitly. The ``httpx.Client`` is injectable for tests.
    """

    name = "netlify"

    def __init__(
        self,
        *,
        token: str | None = None,
        account: DeployAccount | None = None,
        client: httpx.Client | None = None,
        base_url: str = NETLIFY_API,
        timeout: float = 60.0,
    ) -> None:
        self._token = token if token is not None else get_api_key(NETLIFY_AUTH_TOKEN_ENV_VAR)
        self._account = account
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)

    def _headers(self, content_type: str = "application/json") -> dict[str, str]:
        if not self._token:
            raise DeployError(
                f"no Netlify token — set ${NETLIFY_AUTH_TOKEN_ENV_VAR} or pass token"
            )
        return {"Authorization": f"Bearer {self._token}", "Content-Type": content_type}

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            resp = self._client.request(method, f"{self._base_url}{path}", **kwargs)
        except httpx.HTTPError as exc:  # transport error
            raise DeployError(f"netlify request failed: {exc}") from exc
        if resp.status_code >= 300:
            raise DeployError(f"netlify HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            return resp.json()
        except ValueError as exc:
            raise DeployError(f"netlify returned non-JSON: {exc}") from exc

    def ensure_site(self, name: str, *, account: DeployAccount | None = None) -> SiteRef:
        """Find a site by name, or create it under the given/default account."""
        acct = account or self._account
        existing = self._request("GET", "/sites", headers=self._headers(), params={"name": name})
        for site in existing if isinstance(existing, list) else []:
            if site.get("name") == name:
                return _site_ref(site)
        body: dict[str, object] = {"name": name}
        path = "/sites"
        if acct is not None:
            path = f"/{acct.id}/sites"
        created = self._request("POST", path, headers=self._headers(), json=body)
        return _site_ref(created)

    def deploy(self, site: SiteRef, dist_dir: Path, *, production: bool = False) -> DeployResult:
        """Deploy ``dist`` to the site via Netlify's **file-digest** method.

        We declare each file's path + SHA1, then upload only the files Netlify
        still needs. This is used instead of a raw zip upload on purpose: a zip
        deploy collapses the publish dir to a single ``/`` entry served as
        ``text/plain`` (the page renders as raw source). The digest method keeps
        per-file paths, so Netlify assigns the correct content-type from each
        extension (``.html`` → ``text/html``).

        ``production=False`` creates a draft deploy (viewable at the
        deploy-specific ``deploy_ssl_url``, not the site's production domain).
        """
        if not dist_dir.is_dir():
            raise DeployError(f"dist directory not found: {dist_dir}")
        # Fail closed before uploading if a credential-shaped string is in dist/
        # (the digest deploy ships every file wholesale — todo 075).
        assert_no_secret_leak(dist_dir)
        files: dict[str, tuple[str, bytes]] = {}
        for path in sorted(dist_dir.rglob("*")):
            if path.is_file():
                data = path.read_bytes()
                rel = "/" + path.relative_to(dist_dir).as_posix()
                files[rel] = (hashlib.sha1(data).hexdigest(), data)
        if not files:
            raise DeployError(f"no files to deploy in {dist_dir}")

        body: dict[str, object] = {"files": {p: sha for p, (sha, _) in files.items()}}
        if not production:
            body["draft"] = True
        result = self._request(
            "POST", f"/sites/{site.site_id}/deploys", headers=self._headers(), json=body
        )
        deploy_id = str(result.get("id", ""))
        required = set(result.get("required", []) or [])
        for rel, (sha, data) in files.items():
            if sha in required:
                self._upload_file(deploy_id, rel, data)

        # A draft deploy is NOT promoted to the site's production URL, so
        # ``ssl_url`` 404s until a production deploy exists; its viewable
        # permalink is ``deploy_ssl_url``. Production deploys use the site URL.
        if production:
            url = result.get("ssl_url") or result.get("url") or site.url
        else:
            url = (
                result.get("deploy_ssl_url")
                or result.get("deploy_url")
                or result.get("ssl_url")
                or site.url
            )
        return DeployResult(
            site=site,
            deploy_id=deploy_id,
            url=str(url),
            production=production,
            state=str(result.get("state", "")),
        )

    def _upload_file(self, deploy_id: str, rel_path: str, data: bytes) -> None:
        """Upload one file's bytes to an open deploy (digest method step 2)."""
        try:
            resp = self._client.put(
                f"{self._base_url}/deploys/{deploy_id}/files{rel_path}",
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/octet-stream",
                },
                content=data,
            )
        except httpx.HTTPError as exc:
            raise DeployError(f"netlify file upload failed: {exc}") from exc
        if resp.status_code >= 300:
            raise DeployError(f"netlify upload HTTP {resp.status_code}: {resp.text[:200]}")

    def set_custom_domain(self, site: SiteRef, domain: str) -> SiteRef:
        """Attach a custom domain (a gated action — DNS/domain change)."""
        updated = self._request(
            "PATCH",
            f"/sites/{site.site_id}",
            headers=self._headers(),
            json={"custom_domain": domain},
        )
        return _site_ref(updated)

    def transfer_ownership(self, site: SiteRef, to_account: DeployAccount) -> SiteRef:
        """Move the site to another account — the hook for client handoff."""
        updated = self._request(
            "PATCH",
            f"/sites/{site.site_id}",
            headers=self._headers(),
            json={"account_slug": to_account.id},
        )
        return _site_ref(updated)


def _site_ref(payload: dict) -> SiteRef:
    return SiteRef(
        site_id=str(payload.get("id") or payload.get("site_id") or ""),
        name=str(payload.get("name", "")),
        url=str(payload.get("ssl_url") or payload.get("url") or ""),
        account_id=str(payload.get("account_slug") or payload.get("account_id") or ""),
    )
