from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from packages.etsy.auth import (
    EtsyCredentials,
    EtsyOAuthToken,
    build_authorization_url,
    create_pkce_pair,
    credential_readiness,
    exchange_authorization_code,
    redact_secret,
    refresh_oauth_token,
    validate_callback_state,
)


def test_composite_api_credential_requires_keystring_and_shared_secret() -> None:
    assert EtsyCredentials.from_composite("abc123:def456").api_key == "abc123:def456"
    with pytest.raises(ValueError, match="keystring:shared_secret"):
        EtsyCredentials.from_composite("abc123")
    with pytest.raises(ValueError, match="keystring:shared_secret"):
        EtsyCredentials.from_composite("a:b:c")
    with pytest.raises(ValueError, match="keystring:shared_secret"):
        EtsyCredentials.from_composite("key:   ")


def test_secret_diagnostics_are_redacted() -> None:
    value = "real-shared-secret"
    assert value not in redact_secret(value)
    assert redact_secret(value) == "[redacted: 18 chars]"
    assert redact_secret("abc") == "***"


def test_missing_composite_does_not_try_legacy_sources() -> None:
    requested = []

    def loader(name, **kwargs):
        assert kwargs == {"source": "etsy_env"}
        requested.append(name)
        return None

    readiness = credential_readiness(loader)
    assert not readiness.ready
    assert "ETSY_API_KEY" not in requested
    assert ".etsy.env" in readiness.message


def test_readiness_reports_file_oauth_presence_and_safe_expiry_metadata() -> None:
    values = {
        "ETSY_API_CREDENTIAL": "key:secret",
        "ETSY_OAUTH_ACCESS_TOKEN": "access-token",
        "ETSY_OAUTH_REFRESH_TOKEN": "refresh-token",
        "ETSY_OAUTH_EXPIRES_AT": "2030-01-02T03:04:05+00:00",
    }

    def loader(name: str, **kwargs: object) -> str | None:
        assert kwargs == {"source": "etsy_env"}
        return values.get(name)

    readiness = credential_readiness(loader)
    assert readiness.ready
    assert readiness.diagnostics == {
        "api_credential": ".etsy.env: present",
        "access_token": ".etsy.env: present",
        "refresh_token": ".etsy.env: present",
        "expires_at": ".etsy.env: valid (2030-01-02T03:04:05+00:00)",
    }
    diagnostic_text = " ".join(readiness.diagnostics.values())
    assert "access-token" not in diagnostic_text
    assert "refresh-token" not in diagnostic_text
    assert "key:secret" not in diagnostic_text


@pytest.mark.parametrize("expiry", [None, "not-a-date"])
def test_missing_or_malformed_file_expiry_fails_readiness(expiry: str | None) -> None:
    values = {
        "ETSY_API_CREDENTIAL": "key:secret",
        "ETSY_OAUTH_ACCESS_TOKEN": "access-token",
        "ETSY_OAUTH_REFRESH_TOKEN": "refresh-token",
        "ETSY_OAUTH_EXPIRES_AT": expiry,
    }

    def loader(name: str, **_kwargs: object) -> str | None:
        return values.get(name)

    readiness = credential_readiness(loader)
    assert not readiness.ready
    assert readiness.diagnostics["expires_at"].startswith(".etsy.env:")
    assert "not-a-date" not in readiness.message


def test_pkce_authorization_url_has_only_read_scopes() -> None:
    verifier, challenge = create_pkce_pair()
    assert len(verifier) >= 43
    assert challenge != verifier
    url = build_authorization_url(
        client_id="client-key", redirect_uri="https://localhost/callback", state="state-1", code_challenge=challenge
    )
    query = parse_qs(urlparse(url).query)
    assert query["scope"] == ["shops_r listings_r"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["client_id"] == ["client-key"]
    assert verifier not in url


def test_callback_state_requires_exact_match() -> None:
    validate_callback_state("expected", "expected")
    with pytest.raises(ValueError, match="state"):
        validate_callback_state("expected", "wrong")


def test_token_expiry_and_refresh_payload() -> None:
    expired = EtsyOAuthToken(
        access_token="access", refresh_token="refresh", expires_at=datetime.now(UTC) - timedelta(seconds=1)
    )
    assert expired.is_expired()
    assert expired.refresh_payload("client-key") == {
        "grant_type": "refresh_token",
        "client_id": "client-key",
        "refresh_token": "refresh",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"access_token": "", "refresh_token": "refresh", "expires_in": 3600},
        {"access_token": "access", "refresh_token": "", "expires_in": 3600},
        {"access_token": "access", "refresh_token": "refresh", "expires_in": 0},
        {"access_token": "access", "refresh_token": "refresh", "expires_in": True},
    ],
)
def test_token_response_rejects_blank_tokens_and_invalid_expiry(payload) -> None:
    with pytest.raises(ValueError, match="token fields"):
        EtsyOAuthToken.from_token_response(payload)


def test_code_exchange_is_in_memory_and_uses_pkce_payload() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={"access_token": "access", "refresh_token": "refresh", "expires_in": 3600},
            request=request,
        )

    token = exchange_authorization_code(
        client_id="client-key",
        redirect_uri="https://localhost/callback",
        code="authorization-code",
        code_verifier="verifier",
        transport=httpx.MockTransport(handler),
    )
    assert token.access_token == "access"
    assert seen[0].method == "POST"
    assert str(seen[0].url) == "https://openapi.etsy.com/v3/public/oauth/token"
    assert parse_qs(seen[0].content.decode())["code_verifier"] == ["verifier"]


def test_refresh_exchange_uses_refresh_grant_without_logging_token() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={"access_token": "next-access", "refresh_token": "next-refresh", "expires_in": 3600},
            request=request,
        )

    token = refresh_oauth_token(
        client_id="client-key", refresh_token="refresh", transport=httpx.MockTransport(handler)
    )
    assert token.refresh_token == "next-refresh"
    body = parse_qs(seen[0].content.decode())
    assert body["grant_type"] == ["refresh_token"]
    assert body["refresh_token"] == ["refresh"]
