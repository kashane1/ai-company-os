"""Phase 4.3 — observability rollup + redaction tests.

Seeds a fake logs root with planted credentials and asserts none of them
survive through ``build_rollup().to_markdown()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from packages.tools.observability.redaction import REDACTED, redact
from packages.tools.observability.rollup import (
    LANE_LOG_DIRS,
    _extract_failure_codes,
    build_rollup,
)


PLANTED_SECRETS = {
    "openai": "sk-abcdefghij0123456789ABCDEF",
    "github_pat": "ghp_" + "A" * 24,
    "github_app": "ghs_" + "B" * 24,
    "github_fine": "github_pat_" + "C" * 24,
    "aws": "AKIAABCDEFGHIJKLMNOP",
    "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signaturepart1",
    "bearer": "Bearer abcdef0123456789deadbeef==",
    "inline": "api_key=super_secret_value_12345",
    "gtm_env": "POSTIZ_API_KEY=topsecretvalue",
}


def test_redact_catches_each_pattern():
    for label, value in PLANTED_SECRETS.items():
        line = f"2026-04-10 12:00:00 INFO something happened {value} tail"
        result = redact(line)
        assert value not in result.text, f"{label} survived redaction"
        assert REDACTED in result.text
        assert result.hits, f"{label} did not produce a hit"


def test_extract_failure_codes_parses_tokens():
    lines = [
        "ERROR failure_code=missing_checklist product=catchbook",
        "ERROR failure_code=missing_checklist other=1",
        "ERROR failure_code=approval_not_granted",
        "INFO nothing to see",
    ]
    codes = _extract_failure_codes(lines)
    assert codes == {"missing_checklist": 2, "approval_not_granted": 1}


@dataclass(frozen=True)
class _FakeEvent:
    event_type: str
    payload: dict


def _seed_logs(root: Path) -> None:
    for lane in LANE_LOG_DIRS.values():
        (root / lane).mkdir(parents=True, exist_ok=True)
    # engineering: plant a couple of secrets and a failure_code
    (root / "engineering" / "run.log").write_text(
        "\n".join(
            [
                f"ERROR failure_code=lint_failed token={PLANTED_SECRETS['openai']}",
                f"ERROR failure_code=lint_failed Authorization: {PLANTED_SECRETS['bearer']}",
                f"ERROR failure_code=tests_failed {PLANTED_SECRETS['github_pat']}",
                "INFO heartbeat ok",
            ]
        )
        + "\n"
    )
    # gtm: env-style key
    (root / "gtm" / "daily.log").write_text(
        f"WARN failure_code=postiz_rate_limited {PLANTED_SECRETS['gtm_env']}\n"
    )
    # runtime-supervisor: preflight with one green, one blocked
    (root / "runtime-supervisor").mkdir(parents=True, exist_ok=True)
    (root / "runtime-supervisor" / "preflight.log").write_text(
        "\n".join(
            [
                "preflight lane=engineering status=green",
                "preflight lane=ios status=blocked reason=no-simulator",
                "preflight lane=gtm ok",
            ]
        )
        + "\n"
    )


def test_build_rollup_redacts_planted_credentials(tmp_path: Path):
    _seed_logs(tmp_path)
    events = [
        _FakeEvent("task_created", {"lane": "engineering"}),
        _FakeEvent("task_created", {"lane": "engineering"}),
        _FakeEvent("task_completed", {"lane": "engineering"}),
        _FakeEvent("task_failed", {"worker_lane": "gtm"}),
    ]
    rollup = build_rollup(events=events, logs_root=tmp_path, now="2026-04-10T12:00:00+00:00")
    md = rollup.to_markdown()

    # Credentials must NEVER appear in rollup output.
    for label, value in PLANTED_SECRETS.items():
        if label in {"github_app", "github_fine", "aws", "jwt", "inline"}:
            continue  # not planted in this seed
        assert value not in md, f"{label} leaked into rollup markdown"

    # Structural assertions.
    assert "Observability rollup" in md
    assert "engineering" in md
    assert "lint_failed" in md
    assert rollup.dispatched_by_lane["engineering"] == 2
    assert rollup.completed_by_lane["engineering"] == 1
    assert rollup.failed_by_lane["gtm"] == 1
    assert rollup.redaction_hits, "expected at least one redaction hit"

    eng_lane = next(l for l in rollup.lanes if l.lane == "engineering")
    assert eng_lane.preflight_status == "green"
    ios_lane = next(l for l in rollup.lanes if l.lane == "ios")
    assert ios_lane.preflight_status == "blocked"


def test_build_rollup_with_empty_logs(tmp_path: Path):
    rollup = build_rollup(events=[], logs_root=tmp_path, now="2026-04-10T12:00:00+00:00")
    md = rollup.to_markdown()
    assert "Observability rollup" in md
    assert rollup.redaction_hits == ()
