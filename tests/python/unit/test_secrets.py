"""Phase 0.4 — tests for packages/config/secrets.py."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from packages.config import secrets as secrets_mod


@pytest.fixture(autouse=True)
def _reset_cache():
    secrets_mod._reset_cache_for_tests()
    yield
    secrets_mod._reset_cache_for_tests()


def test_get_secret_env_source_prefers_environ(monkeypatch):
    monkeypatch.setenv("MY_TOKEN", "from-environ")
    assert secrets_mod.get_secret("MY_TOKEN", source="env") == "from-environ"


def test_etsy_names_always_resolve_from_etsy_env_for_legacy_keychain_calls(monkeypatch, tmp_path):
    env_path = tmp_path / ".etsy.env"
    env_path.write_text("ETSY_API_CREDENTIAL=from-etsy-file\n")
    monkeypatch.setattr(secrets_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setenv("ETSY_API_CREDENTIAL", "from-process-env")

    def forbidden_runner(*_args, **_kwargs):
        raise AssertionError("Etsy secret lookups must not invoke Keychain")

    assert secrets_mod.get_secret(
        "ETSY_API_CREDENTIAL",
        source="keychain",
        service="ignored",
        account="ETSY_API_CREDENTIAL",
        runner=forbidden_runner,
    ) == "from-etsy-file"
    assert secrets_mod.get_secret("ETSY_API_CREDENTIAL", source="env") == "from-etsy-file"
    assert secrets_mod.get_secret("ETSY_API_CREDENTIAL", source="etsy_env") == "from-etsy-file"


def test_missing_etsy_name_never_falls_back_to_env_dotenv_or_keychain(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("ETSY_API_CREDENTIAL=from-dotenv\n")
    monkeypatch.setattr(secrets_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setenv("ETSY_API_CREDENTIAL", "from-process-env")

    def forbidden_runner(*_args, **_kwargs):
        raise AssertionError("Etsy secret lookups must not invoke Keychain")

    assert secrets_mod.get_secret("ETSY_API_CREDENTIAL", source="env") is None
    assert secrets_mod.get_secret(
        "legacy-name",
        source="keychain",
        account="ETSY_API_CREDENTIAL",
        runner=forbidden_runner,
    ) is None
    with pytest.raises(secrets_mod.SecretNotFoundError, match=r"source=\.etsy\.env"):
        secrets_mod.require_secret(
            "legacy-name", source="keychain", account="ETSY_API_CREDENTIAL", runner=forbidden_runner
        )


def test_get_secret_env_source_falls_back_to_dotenv(monkeypatch, tmp_path):
    monkeypatch.delenv("MY_TOKEN", raising=False)
    dotenv = tmp_path / ".env"
    dotenv.write_text('MY_TOKEN="from-dotenv"\nOTHER=value\n')
    monkeypatch.setattr(secrets_mod, "_repo_root", lambda: tmp_path)
    assert secrets_mod.get_secret("MY_TOKEN", source="env") == "from-dotenv"


def test_get_secret_returns_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("MY_TOKEN", raising=False)
    monkeypatch.setattr(secrets_mod, "_repo_root", lambda: tmp_path)
    assert secrets_mod.get_secret("MY_TOKEN", source="env") is None


def test_require_secret_raises_when_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("MY_TOKEN", raising=False)
    monkeypatch.setattr(secrets_mod, "_repo_root", lambda: tmp_path)
    with pytest.raises(secrets_mod.SecretNotFoundError):
        secrets_mod.require_secret("MY_TOKEN", source="env")


def test_keychain_read_success(monkeypatch):
    calls = {}

    def fake_runner(args, capture_output, text, check):
        calls["args"] = args
        return SimpleNamespace(returncode=0, stdout="sekret\n", stderr="")

    value = secrets_mod.get_secret(
        "APP_STORE_CONNECT_API_KEY",
        source="keychain",
        service="ai-company-os",
        runner=fake_runner,
    )
    assert value == "sekret"
    assert calls["args"][0] == "security"
    assert "APP_STORE_CONNECT_API_KEY" in calls["args"]


def test_keychain_read_missing_returns_none():
    def fake_runner(args, capture_output, text, check):
        return SimpleNamespace(returncode=44, stdout="", stderr="not found")

    assert (
        secrets_mod.get_secret(
            "NOT_THERE", source="keychain", runner=fake_runner
        )
        is None
    )


def test_require_p0_secret_refuses_unregistered_name():
    with pytest.raises(ValueError):
        secrets_mod.require_p0_secret("RANDOM_KEY")


def test_require_p0_secret_uses_keychain_only():
    # If this called env fallback, absence would still resolve from os.environ.
    os.environ["APP_STORE_CONNECT_API_KEY"] = "should-be-ignored"
    try:
        def fake_runner(args, capture_output, text, check):
            return SimpleNamespace(returncode=0, stdout="from-keychain\n", stderr="")

        value = secrets_mod.require_p0_secret(
            "APP_STORE_CONNECT_API_KEY", runner=fake_runner
        )
        assert value == "from-keychain"
    finally:
        os.environ.pop("APP_STORE_CONNECT_API_KEY", None)


def test_unknown_source_raises():
    with pytest.raises(ValueError):
        secrets_mod.get_secret("X", source="vault")  # type: ignore[arg-type]
