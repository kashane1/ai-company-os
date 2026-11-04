from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

from packages.config import etsy_env
from packages.etsy.auth import CredentialReadiness, EtsyCredentials, EtsyOAuthToken

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/etsy_oauth_setup.py"
SPEC = importlib.util.spec_from_file_location("etsy_oauth_setup", SCRIPT)
assert SPEC and SPEC.loader
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


def test_callback_persists_tokens_to_default_etsy_file(monkeypatch, tmp_path):
    path = tmp_path / ".etsy.env"
    monkeypatch.setattr(etsy_env, "etsy_env_path", lambda: path)
    token = EtsyOAuthToken("next-access", "next-refresh", datetime(2030, 1, 1, tzinfo=UTC))
    monkeypatch.setattr(setup, "exchange_authorization_code", lambda **kwargs: token)
    flow = setup.OAuthSetupFlow(EtsyCredentials("key", "secret"))
    flow.complete_callback(code="code", state=flow.state)
    assert flow.succeeded
    stored = etsy_env.load_etsy_env(path)
    assert stored["ETSY_OAUTH_ACCESS_TOKEN"] == "next-access"
    assert stored["ETSY_OAUTH_REFRESH_TOKEN"] == "next-refresh"
    assert stored["ETSY_API_CREDENTIAL"] == "key:secret"
    assert path.stat().st_mode & 0o777 == 0o600


def test_success_reports_env_file_storage(capsys) -> None:
    readiness = CredentialReadiness(True, "ready", EtsyCredentials("key", "secret"))
    result = setup.main(
        ["--confirmed-persistent-access"],
        readiness_provider=lambda: readiness,
        server_runner=lambda _flow, _timeout: True,
    )
    output = capsys.readouterr().out
    assert result == 0
    assert ".etsy.env" in output
    assert "Keychain" not in output


def test_start_url_keeps_pkce_verifier_out_of_redirect() -> None:
    flow = setup.OAuthSetupFlow(EtsyCredentials("keystring", "shared"))
    location = flow.authorization_url()
    assert "keystring" in location
    assert flow.verifier not in location
    assert "shops_r" in location and "listings_r" in location


def test_cli_refuses_to_launch_without_persistent_access_confirmation(capsys) -> None:
    called = False

    def serve(_flow, _timeout):
        nonlocal called
        called = True

    readiness = CredentialReadiness(True, "ready", EtsyCredentials("key", "secret"))
    result = setup.main([], readiness_provider=lambda: readiness, server_runner=serve)
    output = capsys.readouterr().out
    assert result == 2
    assert not called
    assert "secret" not in output
    assert "confirmation" in output.lower()


def test_cli_requires_composite_credential_before_launch(capsys) -> None:
    result = setup.main(
        ["--confirmed-persistent-access"],
        readiness_provider=lambda: CredentialReadiness(False, "credential missing", None),
        server_runner=lambda _flow, _timeout: None,
    )
    assert result == 2
    assert "credential missing" in capsys.readouterr().out


def test_cli_bootstraps_when_composite_exists_but_tokens_are_not_ready(capsys) -> None:
    called = False

    def serve(_flow, _timeout):
        nonlocal called
        called = True
        return False

    readiness = CredentialReadiness(False, "tokens missing", EtsyCredentials("key", "secret"))
    result = setup.main(
        ["--confirmed-persistent-access"], readiness_provider=lambda: readiness, server_runner=serve
    )
    assert result == 1
    assert called
    assert "secret" not in capsys.readouterr().out


def test_callback_without_code_finishes_the_one_callback_flow() -> None:
    flow = setup.OAuthSetupFlow(EtsyCredentials("key", "secret"))
    handler_type = setup._handler_for(flow)
    handler = handler_type.__new__(handler_type)
    handler.path = f"/oauth/redirect?error=access_denied&state={flow.state}"
    pages = []
    handler._page = lambda status, message: pages.append((status, message))

    handler.do_GET()

    assert flow.completed
    assert not flow.succeeded
    assert pages[0][0] == 400
