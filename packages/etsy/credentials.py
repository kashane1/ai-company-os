"""Validated persistence helpers for Etsy OAuth credentials in ``.etsy.env``."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from packages.config import etsy_env
from packages.etsy.auth import EtsyCredentials

ETSY_API_CREDENTIAL = "ETSY_API_CREDENTIAL"
ETSY_OAUTH_ACCESS_TOKEN = "ETSY_OAUTH_ACCESS_TOKEN"
ETSY_OAUTH_REFRESH_TOKEN = "ETSY_OAUTH_REFRESH_TOKEN"
ETSY_OAUTH_EXPIRES_AT = "ETSY_OAUTH_EXPIRES_AT"


def _require_token(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Etsy {field} must not be blank")


def _validate_material(
    *, composite_credential: str, access_token: str, refresh_token: str, expires_at: str
) -> None:
    EtsyCredentials.from_composite(composite_credential)
    _require_token(access_token, "OAuth access token")
    _require_token(refresh_token, "OAuth refresh token")
    _require_token(expires_at, "OAuth expiry")
    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Etsy OAuth expiry must be an ISO-8601 timestamp") from None
    if expiry.tzinfo is None:
        raise ValueError("Etsy OAuth expiry must include a timezone")


def store_etsy_api_credential(
    composite_credential: str, *, env_path: Path | None = None
) -> None:
    """Persist one validated API credential without reading another secret source."""
    EtsyCredentials.from_composite(composite_credential)
    etsy_env.write_etsy_env_values(
        {ETSY_API_CREDENTIAL: composite_credential}, env_path=env_path
    )


def store_etsy_oauth_material(
    *,
    composite_credential: str,
    access_token: str,
    refresh_token: str,
    expires_at: str,
    env_path: Path | None = None,
) -> None:
    """Atomically persist a complete, validated Etsy OAuth token bundle."""
    _validate_material(
        composite_credential=composite_credential,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    etsy_env.write_etsy_env_values(
        {
            ETSY_API_CREDENTIAL: composite_credential,
            ETSY_OAUTH_ACCESS_TOKEN: access_token,
            ETSY_OAUTH_REFRESH_TOKEN: refresh_token,
            ETSY_OAUTH_EXPIRES_AT: expires_at,
        },
        env_path=env_path,
    )
