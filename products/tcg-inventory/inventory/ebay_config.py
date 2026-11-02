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

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / ".ebay.env"


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
