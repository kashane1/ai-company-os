"""Secret loading helper (Phase 0.4).

All new daemons and scripts must go through this module rather than calling
``os.environ.get`` directly. The macOS Keychain path is the only acceptable
source for credentials that touch approval-gated actions (App Store Connect,
protected-branch merges, billing, DNS).

Rationale: centralising the secret-access surface gives us one place to audit,
one place to swap in a vault later, and one place to enforce the "P0 secrets
must come from Keychain" rule.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Literal

SecretSource = Literal["env", "keychain"]

KEYCHAIN_SERVICE_DEFAULT = "ai-company-os"

_DOT_ENV_CACHE: dict[str, str] | None = None


class SecretNotFoundError(KeyError):
    """Raised when a required secret is not resolvable."""


def _load_dotenv(repo_root: Path) -> dict[str, str]:
    global _DOT_ENV_CACHE
    if _DOT_ENV_CACHE is not None:
        return _DOT_ENV_CACHE
    env_file = repo_root / ".env"
    values: dict[str, str] = {}
    if env_file.exists():
        for raw in env_file.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    _DOT_ENV_CACHE = values
    return values


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_keychain(
    name: str,
    *,
    service: str,
    account: str | None,
    runner=subprocess.run,
) -> str | None:
    args = ["security", "find-generic-password", "-s", service, "-w"]
    if account is not None:
        args.extend(["-a", account])
    else:
        args.extend(["-a", name])
    try:
        result = runner(args, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    value = (result.stdout or "").rstrip("\n")
    return value or None


def get_secret(
    name: str,
    *,
    source: SecretSource = "env",
    service: str = KEYCHAIN_SERVICE_DEFAULT,
    account: str | None = None,
    runner=subprocess.run,
) -> str | None:
    """Return the secret value, or None if missing.

    ``source="env"`` reads process env first, then the repo ``.env`` file.
    ``source="keychain"`` uses ``security find-generic-password``.
    """
    if source == "env":
        value = os.environ.get(name)
        if value:
            return value
        dotenv = _load_dotenv(_repo_root())
        return dotenv.get(name) or None
    if source == "keychain":
        return _read_keychain(name, service=service, account=account, runner=runner)
    raise ValueError(f"unknown secret source: {source}")


def require_secret(
    name: str,
    *,
    source: SecretSource = "env",
    service: str = KEYCHAIN_SERVICE_DEFAULT,
    account: str | None = None,
    runner=subprocess.run,
) -> str:
    value = get_secret(
        name, source=source, service=service, account=account, runner=runner
    )
    if not value:
        raise SecretNotFoundError(
            f"required secret {name!r} not found in source={source}"
        )
    return value


# Secrets that must come from Keychain (never .env). Enforced by
# ``require_p0_secret``.
P0_SECRET_NAMES = frozenset(
    {
        "APP_STORE_CONNECT_API_KEY",
        "APP_STORE_CONNECT_KEY_ID",
        "APP_STORE_CONNECT_ISSUER_ID",
        "GITHUB_PROTECTED_BRANCH_TOKEN",
        "BILLING_ADMIN_TOKEN",
        "DNS_ADMIN_TOKEN",
    }
)


def require_p0_secret(
    name: str,
    *,
    service: str = KEYCHAIN_SERVICE_DEFAULT,
    account: str | None = None,
    runner=subprocess.run,
) -> str:
    """P0 secrets are Keychain-only. Refuses ``.env`` fallback."""
    if name not in P0_SECRET_NAMES:
        raise ValueError(
            f"{name!r} is not registered as a P0 secret; "
            "add it to P0_SECRET_NAMES if it should be Keychain-only"
        )
    return require_secret(
        name,
        source="keychain",
        service=service,
        account=account,
        runner=runner,
    )


def _reset_cache_for_tests() -> None:
    global _DOT_ENV_CACHE
    _DOT_ENV_CACHE = None
