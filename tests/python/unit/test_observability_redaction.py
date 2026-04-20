"""Focused unit tests for observability redaction helpers."""

from __future__ import annotations

import pytest

from packages.tools.observability.redaction import (
    PATTERNS,
    REDACTED,
    redact,
    redact_lines,
)


PATTERN_CASES = [
    ("openai_or_anthropic_key", "sk-abcDEF1234567890abcdXYZ", "prefix sk-abcDEF1234567890abcdXYZ more text"),
    ("github_personal_access_token", "ghp_AbCdEfGhIjKlMnOpQrStUvWx", "prefix ghp_AbCdEfGhIjKlMnOpQrStUvWx suffix"),
    ("github_app_token", "ghs_AbCdEfGhIjKlMnOpQrStUvWx", "prefix ghs_AbCdEfGhIjKlMnOpQrStUvWx suffix"),
    ("github_fine_grained_pat", "github_pat_AbCdEfGhIjKlMnOpQrStUvWx", "prefix github_pat_AbCdEfGhIjKlMnOpQrStUvWx suffix"),
    ("aws_access_key_id", "AKIAABCDEFGHIJKLMNOP", "prefix AKIAABCDEFGHIJKLMNOP suffix"),
    ("aws_temp_access_key_id", "ASIAABCDEFGHIJKLMNOP", "prefix ASIAABCDEFGHIJKLMNOP suffix"),
    (
        "jwt",
        "eyJabcDEF12.abcDEF123456.abcDEF123456",
        "prefix eyJabcDEF12.abcDEF123456.abcDEF123456 more text",
    ),
    ("bearer_token", "Bearer abcdef0123456789deadbeef==", "prefix Bearer abcdef0123456789deadbeef== suffix"),
    ("inline_secret_assignment", "api_key=supersecret12345", "context api_key=supersecret12345 trailing"),
    ("gtm_env_key", "POSTIZ_API_KEY=topsecret", "context POSTIZ_API_KEY=topsecret trailing"),
]


@pytest.mark.parametrize(("expected_label", "secret", "line"), PATTERN_CASES)
def test_redact_covers_each_required_pattern(expected_label: str, secret: str, line: str):
    result = redact(line)

    assert REDACTED in result.text
    assert secret not in result.text
    assert expected_label in result.hits


def test_redact_no_matches_returns_original_text_and_empty_hits():
    line = "2026-04-10 INFO no credentials here, just ordinary text"
    result = redact(line)

    assert result.text == line
    assert result.hits == ()


def test_redact_lines_processes_each_line_independently_and_preserves_length():
    lines = [
        "safe line",
        "Bearer abcdef0123456789deadbeef==",
        "api_key=supersecret12345",
    ]

    redacted_lines = redact_lines(lines)

    assert len(redacted_lines) == len(lines)
    assert redacted_lines[0] == lines[0]
    assert REDACTED in redacted_lines[1]
    assert REDACTED in redacted_lines[2]


def test_redact_multiple_secrets_reports_all_labels():
    line = (
        "before sk-abcDEF1234567890abcdXYZ "
        "AKIAABCDEFGHIJKLMNOP "
        "Bearer abcdef0123456789deadbeef== "
        "api_key=supersecret12345 "
        "POSTIZ_API_KEY=topsecret after"
    )

    result = redact(line)

    assert REDACTED in result.text
    assert "sk-abcDEF1234567890abcdXYZ" not in result.text
    assert "AKIAABCDEFGHIJKLMNOP" not in result.text
    assert "Bearer abcdef0123456789deadbeef==" not in result.text
    assert "api_key=supersecret12345" not in result.text
    assert "POSTIZ_API_KEY=topsecret" not in result.text
    assert {
        "openai_or_anthropic_key",
        "aws_access_key_id",
        "bearer_token",
        "inline_secret_assignment",
        "gtm_env_key",
    }.issubset(set(result.hits))


def test_pattern_labels_include_all_required_coverage_targets():
    labels = {label for _, label in PATTERNS}

    assert {
        "openai_or_anthropic_key",
        "github_personal_access_token",
        "github_app_token",
        "github_fine_grained_pat",
        "aws_access_key_id",
        "aws_temp_access_key_id",
        "jwt",
        "bearer_token",
        "inline_secret_assignment",
        "gtm_env_key",
    }.issubset(labels)
