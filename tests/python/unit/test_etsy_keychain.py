from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import packages.etsy.keychain as keychain
from packages.etsy.keychain import (
    ETSY_API_CREDENTIAL,
    ETSY_OAUTH_ACCESS_TOKEN,
    ETSY_OAUTH_EXPIRES_AT,
    ETSY_OAUTH_REFRESH_TOKEN,
    store_etsy_api_credential,
    store_etsy_oauth_material,
)


def test_legacy_keychain_exports_write_the_etsy_env_bundle(tmp_path: Path) -> None:
    env_path = tmp_path / ".etsy.env"

    store_etsy_oauth_material(
        composite_credential="key:secret",
        access_token="access-token",
        refresh_token="refresh-token",
        expires_at="2030-01-02T03:04:05+00:00",
        env_path=env_path,
    )

    values = dict(
        line.split("=", 1)
        for line in env_path.read_text().splitlines()
        if line and not line.startswith("#")
    )
    assert values == {
        ETSY_API_CREDENTIAL: "key:secret",
        ETSY_OAUTH_ACCESS_TOKEN: "access-token",
        ETSY_OAUTH_REFRESH_TOKEN: "refresh-token",
        ETSY_OAUTH_EXPIRES_AT: "2030-01-02T03:04:05+00:00",
    }
    assert env_path.stat().st_mode & 0o777 == 0o600


def test_credential_store_validates_before_overwriting(tmp_path: Path) -> None:
    env_path = tmp_path / ".etsy.env"
    original = "# retain this comment\nUNRELATED=value\n"
    env_path.write_text(original)

    with pytest.raises(ValueError, match="keystring:shared_secret"):
        store_etsy_api_credential("keystring-only", env_path=env_path)

    assert env_path.read_text() == original
    assert not list(tmp_path.glob(".*.tmp"))


def test_legacy_keychain_module_has_no_macos_or_process_access() -> None:
    source = inspect.getsource(keychain)
    assert "Security.framework" not in source
    assert "import subprocess" not in source
    assert "from ctypes" not in source
    assert "CDLL(" not in source
