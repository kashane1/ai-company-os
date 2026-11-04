"""Where the eBay credentials come from, and nowhere else.

Credentials live in `.ebay.env` at the project root, which is gitignored. They
are not read from the process environment and not read from the macOS keychain:
one file, one place to look, one place to revoke.

Sandbox and production are separate keysets and the distinction is load-bearing.
Sandbox cannot see the real shelf, so a sandbox client that appears to work
proves only that the request was well formed. Production can delist a card for
real. `EBAY_ENV` picks which set loads, and asking for production credentials
that are not present raises rather than quietly falling back to sandbox — a
silent fallback would mean a delist that reports success and changes nothing.
"""

from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / ".ebay.env"

TOKEN_PATH = "/identity/v1/oauth2/token"

# The scope every application token carries. Asking for nothing narrower keeps
# this a pure credential check rather than a probe of what the keyset can do.
CLIENT_CREDENTIALS_SCOPE = "https://api.ebay.com/oauth/api_scope"


class CredentialsUnavailable(RuntimeError):
    """The credentials file is missing, or missing the keys that were asked for."""


@dataclass(frozen=True)
class EbayCredentials:
    environment: str
    app_id: str
    dev_id: str
    cert_id: str

    @property
    def is_sandbox(self) -> bool:
        return self.environment == "sandbox"

    @property
    def api_base(self) -> str:
        return (
            "https://api.sandbox.ebay.com"
            if self.is_sandbox
            else "https://api.ebay.com"
        )

    def __repr__(self) -> str:
        """Never let the secret reach a log line or a traceback."""
        return f"EbayCredentials(environment={self.environment!r}, app_id={self.app_id!r})"


def _read_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise CredentialsUnavailable(
            f"No credentials at {path}. Copy the keyset from developer.ebay.com into it."
        )
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def load(environment: str | None = None, path: Path | None = None) -> EbayCredentials:
    """Load one environment's keyset. Raises if any part of it is missing."""
    values = _read_file(path or CREDENTIALS_FILE)
    environment = environment or values.get("EBAY_ENV", "sandbox")

    if environment not in ("sandbox", "production"):
        raise CredentialsUnavailable(
            f"EBAY_ENV must be 'sandbox' or 'production', not {environment!r}"
        )

    prefix = "EBAY_SANDBOX_" if environment == "sandbox" else "EBAY_PROD_"
    keys = {name: f"{prefix}{name.upper()}" for name in ("app_id", "dev_id", "cert_id")}
    missing = [key for key in keys.values() if not values.get(key)]
    if missing:
        raise CredentialsUnavailable(
            f"{CREDENTIALS_FILE} is missing {', '.join(missing)} for {environment}"
        )

    return EbayCredentials(
        environment=environment,
        app_id=values[keys["app_id"]],
        dev_id=values[keys["dev_id"]],
        cert_id=values[keys["cert_id"]],
    )


def status(path: Path | None = None) -> dict[str, bool]:
    """Which environments are usable, without loading or exposing any secret."""
    try:
        values = _read_file(path or CREDENTIALS_FILE)
    except CredentialsUnavailable:
        return {"sandbox": False, "production": False}

    return {
        env: all(
            values.get(f"{prefix}{name}")
            for name in ("APP_ID", "DEV_ID", "CERT_ID")
        )
        for env, prefix in (("sandbox", "EBAY_SANDBOX_"), ("production", "EBAY_PROD_"))
    }


@dataclass(frozen=True)
class VerificationResult:
    """What eBay said when asked for a token. Never carries the token itself."""

    environment: str
    is_authenticated: bool
    detail: str

    def __str__(self) -> str:
        mark = "ok" if self.is_authenticated else "FAILED"
        return f"{self.environment:<11} {mark:<7} {self.detail}"


def _ssl_context() -> ssl.SSLContext:
    """A verifying context, with a bundle that actually exists.

    Pythons installed from python.org ship without a CA bundle until someone
    runs `Install Certificates.command`, and until then every HTTPS call dies
    with an error that reads like an intercepted connection rather than a
    missing trust store. Falling back to `certifi` when it is importable turns
    that confusing failure into a working call. Verification is never disabled:
    these requests carry the credential that can delist real cards.
    """
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _post_token_request(url: str, basic_auth: str, timeout_seconds: int) -> dict:
    """One client-credentials call. Separated out so tests can stand in for it."""
    body = f"grant_type=client_credentials&scope={CLIENT_CREDENTIALS_SCOPE}".encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic_auth}",
        },
    )
    with urllib.request.urlopen(
        request, timeout=timeout_seconds, context=_ssl_context()
    ) as response:
        return json.load(response)


def verify(
    environment: str | None = None,
    path: Path | None = None,
    timeout_seconds: int = 30,
) -> VerificationResult:
    """Ask eBay whether a keyset actually works.

    `status` only reports that the three keys are present in the file, which is
    a weaker claim than it looks. A production keyset stays inert until the
    business details are filled in and the agreements accepted, and an inert
    keyset is indistinguishable from a working one on disk — it has the right
    shape, the right prefix and the right length, and eBay rejects it with
    `401 invalid_client`. The only way to tell the two apart is to ask, so this
    asks.

    A client-credentials request reads nothing and changes nothing on the
    account; it is the cheapest call that still proves the keyset is live.
    """
    credentials = load(environment, path)
    basic_auth = base64.b64encode(
        f"{credentials.app_id}:{credentials.cert_id}".encode()
    ).decode()

    try:
        payload = _post_token_request(
            credentials.api_base + TOKEN_PATH, basic_auth, timeout_seconds
        )
    except urllib.error.HTTPError as error:
        return VerificationResult(
            credentials.environment,
            is_authenticated=False,
            detail=_explain_rejection(error, credentials),
        )
    except urllib.error.URLError as error:
        return VerificationResult(
            credentials.environment,
            is_authenticated=False,
            detail=f"could not reach {credentials.api_base}: {error.reason}",
        )

    # The token is deliberately dropped. Nothing here needs it, and a value that
    # is never held cannot be logged by accident.
    expires_in = payload.get("expires_in", "?")
    return VerificationResult(
        credentials.environment,
        is_authenticated=True,
        detail=f"eBay issued a token, valid {expires_in}s",
    )


def _explain_rejection(
    error: urllib.error.HTTPError, credentials: EbayCredentials
) -> str:
    """Turn eBay's terse OAuth error into the thing to go and check."""
    if error.code != 401:
        return f"HTTP {error.code} from {credentials.api_base}"

    if credentials.is_sandbox:
        hint = "regenerate the sandbox Cert ID and paste the new value in"
    else:
        hint = (
            "the keyset is probably not activated yet — finish the business and "
            "contact details in the developer portal, or regenerate the "
            "production Cert ID if you copied it before regenerating"
        )
    return f"HTTP 401, eBay rejected the keyset: {hint}"
