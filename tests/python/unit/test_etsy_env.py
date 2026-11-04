from __future__ import annotations

import traceback
from pathlib import Path

import pytest

from packages.config import etsy_env
from packages.config.etsy_env import load_etsy_env
from packages.etsy.credentials import store_etsy_oauth_material


def test_load_etsy_env_parses_export_quotes_and_comments_literally(tmp_path: Path) -> None:
    env_path = tmp_path / ".etsy.env"
    env_path.write_text(
        "# Etsy credentials\n"
        "export ETSY_API_CREDENTIAL='key:shared#secret' # trailing comment\n"
        'ETSY_OAUTH_ACCESS_TOKEN="access token # literal" # trailing comment\n'
        "ETSY_OAUTH_REFRESH_TOKEN=refresh-token # comment\n"
        "IGNORED_LINE\n"
    )

    assert load_etsy_env(env_path) == {
        "ETSY_API_CREDENTIAL": "key:shared#secret",
        "ETSY_OAUTH_ACCESS_TOKEN": "access token # literal",
        "ETSY_OAUTH_REFRESH_TOKEN": "refresh-token",
    }


def test_load_etsy_env_rereads_the_file_without_a_stale_cache(tmp_path: Path) -> None:
    env_path = tmp_path / ".etsy.env"
    env_path.write_text("ETSY_OAUTH_ACCESS_TOKEN=first\n")
    assert load_etsy_env(env_path)["ETSY_OAUTH_ACCESS_TOKEN"] == "first"

    env_path.write_text("ETSY_OAUTH_ACCESS_TOKEN=second\n")
    assert load_etsy_env(env_path)["ETSY_OAUTH_ACCESS_TOKEN"] == "second"


def test_load_etsy_env_keeps_shell_syntax_literal(tmp_path: Path) -> None:
    env_path = tmp_path / ".etsy.env"
    literal = "token$(this-must-not-run)${NOR_EXPAND}"
    env_path.write_text(f"ETSY_OAUTH_ACCESS_TOKEN={literal}\n")

    assert load_etsy_env(env_path)["ETSY_OAUTH_ACCESS_TOKEN"] == literal


def test_store_replaces_etsy_values_preserving_unrelated_lines_and_comments(tmp_path: Path) -> None:
    env_path = tmp_path / ".etsy.env"
    env_path.write_text("# keep me\nUNRELATED=preserved\nETSY_OAUTH_ACCESS_TOKEN=old\n")

    store_etsy_oauth_material(
        composite_credential="key:secret",
        access_token="new-access",
        refresh_token="new-refresh",
        expires_at="2030-01-02T03:04:05+00:00",
        env_path=env_path,
    )

    output = env_path.read_text()
    assert "# keep me\nUNRELATED=preserved\n" in output
    assert "ETSY_OAUTH_ACCESS_TOKEN=new-access\n" in output
    assert "ETSY_OAUTH_ACCESS_TOKEN=old" not in output
    assert load_etsy_env(env_path)["ETSY_OAUTH_REFRESH_TOKEN"] == "new-refresh"
    assert not list(tmp_path.glob(".*.tmp"))


def test_failed_atomic_replace_preserves_original_and_removes_temp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_path = tmp_path / ".etsy.env"
    original = "UNRELATED=preserved\n"
    env_path.write_text(original)

    def reject_replace(_source: Path, _destination: Path) -> None:
        raise OSError("replace denied")

    monkeypatch.setattr(etsy_env.os, "replace", reject_replace)
    with pytest.raises(OSError, match="replace denied"):
        store_etsy_oauth_material(
            composite_credential="key:secret",
            access_token="access",
            refresh_token="refresh",
            expires_at="2030-01-02T03:04:05+00:00",
            env_path=env_path,
        )

    assert env_path.read_text() == original
    assert not list(tmp_path.glob(".etsy.env.*.tmp"))


@pytest.mark.parametrize(
    ("line", "secret_fragment"),
    [
        ('ETSY_OAUTH_ACCESS_TOKEN="unterminated-secret', "unterminated-secret"),
        ('ETSY_OAUTH_ACCESS_TOKEN="value" trailing-secret', "trailing-secret"),
    ],
)
def test_malformed_quoted_value_has_a_generic_non_secret_error(
    tmp_path: Path, line: str, secret_fragment: str
) -> None:
    env_path = tmp_path / ".etsy.env"
    env_path.write_text(line + "\n")

    with pytest.raises(ValueError, match="invalid .etsy.env format") as error:
        load_etsy_env(env_path)

    rendered = "".join(traceback.format_exception(error.type, error.value, error.tb))
    assert secret_fragment not in rendered


def test_invalid_expiry_does_not_appear_in_the_exception_chain(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as error:
        store_etsy_oauth_material(
            composite_credential="key:secret",
            access_token="access",
            refresh_token="refresh",
            expires_at="malformed-expiry-secret",
            env_path=tmp_path / ".etsy.env",
        )

    rendered = "".join(traceback.format_exception(error.type, error.value, error.tb))
    assert "malformed-expiry-secret" not in rendered
