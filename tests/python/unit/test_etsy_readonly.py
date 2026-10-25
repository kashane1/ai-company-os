from __future__ import annotations

import json
import sys

import pytest

from packages.etsy.auth import CredentialReadiness, EtsyCredentials
from scripts import etsy_readonly


def test_diagnostics_report_file_source_without_credentials(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["etsy_readonly.py"])
    monkeypatch.setattr(
        etsy_readonly,
        "credential_readiness",
        lambda: CredentialReadiness(
            True, "Etsy .etsy.env read-only credentials are ready.",
            EtsyCredentials("private-key", "private-secret"),
            {"api_credential": ".etsy.env: present"},
        ),
    )
    assert etsy_readonly.main() == 0
    output = capsys.readouterr().out
    assert json.loads(output)["diagnostics"]["api_credential"] == ".etsy.env: present"
    assert "private-key" not in output
    assert "private-secret" not in output


def test_authorization_requires_composite_in_etsy_env(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "etsy_readonly.py", "--authorization-url", "--redirect-uri",
        "http://localhost/callback", "--state", "state", "--code-challenge", "challenge",
    ])
    monkeypatch.setenv("ETSY_API_KEY", "legacy-process-key")
    monkeypatch.setattr(
        etsy_readonly, "credential_readiness",
        lambda: CredentialReadiness(False, "missing", None),
    )
    with pytest.raises(SystemExit) as error:
        etsy_readonly.main()
    assert error.value.code == 2
    output = capsys.readouterr().err
    assert "ETSY_API_CREDENTIAL in .etsy.env" in output
    assert "legacy-process-key" not in output
