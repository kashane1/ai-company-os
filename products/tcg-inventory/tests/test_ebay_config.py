"""Tests for credential loading.

No real credentials here — every test writes its own file into tmp_path.
"""

from __future__ import annotations

import base64
import ssl
import urllib.error

import pytest
from inventory import ebay_config
from inventory.ebay_config import CredentialsUnavailable

COMPLETE = """\
EBAY_ENV=sandbox
EBAY_SANDBOX_APP_ID=app-123
EBAY_SANDBOX_DEV_ID=dev-123
EBAY_SANDBOX_CERT_ID=secret-123
EBAY_PROD_APP_ID=
EBAY_PROD_CERT_ID=
"""


def write(tmp_path, text):
    path = tmp_path / ".ebay.env"
    path.write_text(text)
    return path


def test_loads_the_environment_the_file_names(tmp_path):
    creds = ebay_config.load(path=write(tmp_path, COMPLETE))

    assert creds.environment == "sandbox"
    assert creds.app_id == "app-123"
    assert creds.api_base == "https://api.sandbox.ebay.com"


def test_asking_for_production_when_it_is_blank_raises(tmp_path):
    """A silent fall back to sandbox would delist nothing and report success."""
    with pytest.raises(CredentialsUnavailable) as err:
        ebay_config.load("production", path=write(tmp_path, COMPLETE))

    assert "EBAY_PROD_APP_ID" in str(err.value)


def test_a_missing_file_names_the_path_it_wanted(tmp_path):
    with pytest.raises(CredentialsUnavailable) as err:
        ebay_config.load(path=tmp_path / "absent.env")

    assert "absent.env" in str(err.value)


def test_the_secret_never_appears_in_a_repr(tmp_path):
    """Tracebacks and log lines print reprs."""
    creds = ebay_config.load(path=write(tmp_path, COMPLETE))

    assert "secret-123" not in repr(creds)
    assert creds.cert_id == "secret-123"


def test_status_reports_readiness_without_reading_secrets(tmp_path):
    ready = ebay_config.status(path=write(tmp_path, COMPLETE))

    assert ready == {"sandbox": True, "production": False}


def test_status_on_a_missing_file_is_not_an_error(tmp_path):
    assert ebay_config.status(path=tmp_path / "absent.env") == {
        "sandbox": False, "production": False,
    }


def test_comments_and_blank_lines_are_ignored(tmp_path):
    path = write(tmp_path, "# a comment\n\nEBAY_ENV=sandbox\n" + COMPLETE)

    assert ebay_config.load(path=path).app_id == "app-123"


# ─── Verifying a keyset against eBay ─────────────────────────────────────────
# These never reach the network: each one stands in for the token request, so
# the suite stays runnable offline and cannot be broken by eBay being down.

def fake_token_response(captured=None):
    def _post(url, basic_auth, timeout_seconds):
        if captured is not None:
            captured.update(url=url, basic_auth=basic_auth)
        return {"access_token": "t-abc", "expires_in": 7200}
    return _post


def rejects_with(code):
    def _post(url, basic_auth, timeout_seconds):
        raise urllib.error.HTTPError(url, code, "nope", {}, None)
    return _post


def test_a_working_keyset_verifies(tmp_path, monkeypatch):
    monkeypatch.setattr(ebay_config, "_post_token_request", fake_token_response())

    result = ebay_config.verify(path=write(tmp_path, COMPLETE))

    assert result.is_authenticated
    assert result.environment == "sandbox"
    assert "7200" in result.detail


def test_the_token_never_reaches_the_result(tmp_path, monkeypatch):
    """Nothing downstream needs it, and a value never held cannot be logged."""
    monkeypatch.setattr(ebay_config, "_post_token_request", fake_token_response())

    result = ebay_config.verify(path=write(tmp_path, COMPLETE))

    assert "t-abc" not in str(result)
    assert "t-abc" not in repr(result)


def test_it_calls_the_sandbox_host_with_basic_auth(tmp_path, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        ebay_config, "_post_token_request", fake_token_response(captured)
    )

    ebay_config.verify(path=write(tmp_path, COMPLETE))

    assert captured["url"] == "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    decoded = base64.b64decode(captured["basic_auth"]).decode()
    assert decoded == "app-123:secret-123"


def test_a_401_is_reported_not_raised(tmp_path, monkeypatch):
    """A rejected keyset is an answer, not a crash — the CLI prints it."""
    monkeypatch.setattr(ebay_config, "_post_token_request", rejects_with(401))

    result = ebay_config.verify(path=write(tmp_path, COMPLETE))

    assert not result.is_authenticated
    assert "401" in result.detail


def test_a_production_401_points_at_activation(tmp_path, monkeypatch):
    """The real failure mode: a keyset that is well formed but not yet live."""
    monkeypatch.setattr(ebay_config, "_post_token_request", rejects_with(401))
    complete_prod = COMPLETE.replace(
        "EBAY_PROD_APP_ID=\nEBAY_PROD_CERT_ID=",
        "EBAY_PROD_APP_ID=app-p\nEBAY_PROD_DEV_ID=dev-p\nEBAY_PROD_CERT_ID=secret-p",
    )

    result = ebay_config.verify("production", path=write(tmp_path, complete_prod))

    assert not result.is_authenticated
    assert "activated" in result.detail


def test_a_sandbox_401_points_at_the_cert_instead(tmp_path, monkeypatch):
    monkeypatch.setattr(ebay_config, "_post_token_request", rejects_with(401))

    result = ebay_config.verify(path=write(tmp_path, COMPLETE))

    assert "Cert ID" in result.detail
    assert "activated" not in result.detail


def test_an_unreachable_host_is_reported_not_raised(tmp_path, monkeypatch):
    def _unreachable(url, basic_auth, timeout_seconds):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(ebay_config, "_post_token_request", _unreachable)

    result = ebay_config.verify(path=write(tmp_path, COMPLETE))

    assert not result.is_authenticated
    assert "api.sandbox.ebay.com" in result.detail


def test_verification_never_disables_certificate_checking(tmp_path):
    """These requests carry the key that can delist real cards."""
    context = ebay_config._ssl_context()

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname
