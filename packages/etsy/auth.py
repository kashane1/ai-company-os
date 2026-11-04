"""Secret-safe Etsy OAuth PKCE helpers.

This module deliberately does not persist credentials. Callers use the Etsy
credential store to save token rotations to the repository-root .etsy.env file.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable, Mapping
from urllib.parse import urlencode

import httpx

from packages.config.secrets import get_secret

AUTHORIZATION_URL = "https://www.etsy.com/oauth/connect"
TOKEN_URL = "https://openapi.etsy.com/v3/public/oauth/token"
READ_SCOPES = ("shops_r", "listings_r")
API_CREDENTIAL_NAME = "ETSY_API_CREDENTIAL"
ACCESS_TOKEN_NAME = "ETSY_OAUTH_ACCESS_TOKEN"
REFRESH_TOKEN_NAME = "ETSY_OAUTH_REFRESH_TOKEN"
EXPIRES_AT_NAME = "ETSY_OAUTH_EXPIRES_AT"


def redact_secret(value: str | None) -> str:
    """Return a small diagnostic label without exposing credential material."""
    if not value:
        return "missing"
    if len(value) <= 4:
        return "***"
    return f"[redacted: {len(value)} chars]"


@dataclass(frozen=True)
class EtsyCredentials:
    keystring: str
    shared_secret: str

    @property
    def api_key(self) -> str:
        return f"{self.keystring}:{self.shared_secret}"

    @classmethod
    def from_composite(cls, value: str) -> "EtsyCredentials":
        pieces = [piece.strip() for piece in value.split(":")]
        if len(pieces) != 2 or not all(pieces):
            raise ValueError("Etsy API credential must be keystring:shared_secret")
        return cls(keystring=pieces[0], shared_secret=pieces[1])


@dataclass(frozen=True)
class CredentialReadiness:
    ready: bool
    message: str
    credentials: EtsyCredentials | None = None
    diagnostics: Mapping[str, str] | None = None


def credential_readiness(
    secret_loader: Callable[..., str | None] = get_secret,
) -> CredentialReadiness:
    """Read .etsy.env-only Etsy material without revealing credential values."""
    composite = secret_loader(
        API_CREDENTIAL_NAME,
        source="etsy_env",
    )
    diagnostics: dict[str, str] = {}
    credentials: EtsyCredentials | None = None
    credential_error = False
    if composite:
        try:
            credentials = EtsyCredentials.from_composite(composite)
            diagnostics["api_credential"] = ".etsy.env: present"
        except ValueError:
            credential_error = True
            diagnostics["api_credential"] = ".etsy.env: malformed"
    else:
        diagnostics["api_credential"] = ".etsy.env: missing"

    access_token = secret_loader(
        ACCESS_TOKEN_NAME,
        source="etsy_env",
    )
    refresh_token = secret_loader(
        REFRESH_TOKEN_NAME,
        source="etsy_env",
    )
    expires_at_raw = secret_loader(
        EXPIRES_AT_NAME,
        source="etsy_env",
    )
    diagnostics["access_token"] = ".etsy.env: present" if access_token else ".etsy.env: missing"
    diagnostics["refresh_token"] = ".etsy.env: present" if refresh_token else ".etsy.env: missing"

    expiry_valid = False
    if not expires_at_raw:
        diagnostics["expires_at"] = ".etsy.env: missing"
    else:
        try:
            parsed_expiry = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
            if parsed_expiry.tzinfo is None:
                raise ValueError("expiry is not timezone-aware")
            normalized_expiry = parsed_expiry.astimezone(UTC)
            if normalized_expiry <= datetime.now(UTC):
                diagnostics["expires_at"] = ".etsy.env: expired"
            else:
                expiry_valid = True
                diagnostics["expires_at"] = f".etsy.env: valid ({normalized_expiry.isoformat()})"
        except ValueError:
            diagnostics["expires_at"] = ".etsy.env: malformed"

    ready = bool(credentials and access_token and refresh_token and expiry_valid)
    if ready:
        return CredentialReadiness(True, "Etsy .etsy.env read-only credentials are ready.", credentials, diagnostics)
    if credential_error:
        message = "Etsy .etsy.env API credential is malformed; expected keystring:shared_secret."
    else:
        message = "Etsy .etsy.env read-only credentials are incomplete or expired."
    return CredentialReadiness(False, message, credentials, diagnostics)


def create_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64).rstrip("=")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def build_authorization_url(*, client_id: str, redirect_uri: str, state: str, code_challenge: str) -> str:
    if not all((client_id, redirect_uri, state, code_challenge)):
        raise ValueError("client_id, redirect_uri, state, and code_challenge are required")
    query = urlencode(
        {
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(READ_SCOPES),
            "client_id": client_id,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{AUTHORIZATION_URL}?{query}"


def validate_callback_state(expected: str, received: str) -> None:
    if not expected or not received or not hmac.compare_digest(expected, received):
        raise ValueError("OAuth callback state does not match")


@dataclass(frozen=True)
class EtsyOAuthToken:
    access_token: str
    refresh_token: str
    expires_at: datetime

    def is_expired(self, *, now: datetime | None = None, leeway_seconds: int = 60) -> bool:
        current = now or datetime.now(UTC)
        expiry = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=UTC)
        return expiry <= current + timedelta(seconds=leeway_seconds)

    def refresh_payload(self, client_id: str) -> dict[str, str]:
        return {"grant_type": "refresh_token", "client_id": client_id, "refresh_token": self.refresh_token}

    @classmethod
    def from_token_response(cls, payload: Mapping[str, object], *, now: datetime | None = None) -> "EtsyOAuthToken":
        access = payload.get("access_token")
        refresh = payload.get("refresh_token")
        expires_in = payload.get("expires_in")
        if (
            not isinstance(access, str)
            or not access.strip()
            or not isinstance(refresh, str)
            or not refresh.strip()
            or isinstance(expires_in, bool)
            or not isinstance(expires_in, int)
            or expires_in <= 0
        ):
            raise ValueError("Etsy token response is missing required token fields")
        return cls(access, refresh, (now or datetime.now(UTC)) + timedelta(seconds=expires_in))


def exchange_authorization_code(
    *, client_id: str, redirect_uri: str, code: str, code_verifier: str, transport: httpx.BaseTransport | None = None
) -> EtsyOAuthToken:
    """Exchange a callback code in memory; callers decide whether to store it."""
    return _post_token(
        {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code": code,
            "code_verifier": code_verifier,
        },
        transport=transport,
    )


def refresh_oauth_token(
    *, client_id: str, refresh_token: str, transport: httpx.BaseTransport | None = None
) -> EtsyOAuthToken:
    """Refresh a token in memory; callers decide whether to persist the rotation."""
    return _post_token(
        {"grant_type": "refresh_token", "client_id": client_id, "refresh_token": refresh_token},
        transport=transport,
    )


def _post_token(payload: dict[str, str], *, transport: httpx.BaseTransport | None) -> EtsyOAuthToken:
    with httpx.Client(transport=transport, timeout=20.0) as client:
        response = client.post(TOKEN_URL, data=payload)
    response.raise_for_status()
    return EtsyOAuthToken.from_token_response(response.json())
