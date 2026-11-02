"""Tests for credential loading.

No real credentials here — every test writes its own file into tmp_path.
"""

from __future__ import annotations

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
