"""Phase 3 — verification-loop runner primitive unit tests.

Unlike the skill structural test, these exercise the runner against
actual sub-checks with monkeypatched fixtures for determinism.
Covers:

- aggregator: pass + soft_fail + hard_fail transitions
- severity enum: info / warn / fail / error / skipped semantics
- redaction: _redact() on nested dicts with sensitive keys
- policy wrapper: raises on hard_fail, returns on soft_fail
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from packages.policies.approvals import PolicyViolation
from packages.policies.verification_loop import run_verification_loop
from packages.tools.primitives import verification_loop_runner
from packages.tools.primitives.verification_loop_runner import (
    SubCheckResult,
    _aggregate,
    _redact,
    _stale_doc_check,
    run,
)


def test_aggregate_all_info_is_pass() -> None:
    checks = (
        SubCheckResult(name="a", severity="info", summary=""),
        SubCheckResult(name="b", severity="info", summary=""),
    )
    verdict, infra = _aggregate(checks)
    assert verdict == "pass"
    assert infra == ()


def test_aggregate_warn_is_soft_fail() -> None:
    checks = (
        SubCheckResult(name="a", severity="info", summary=""),
        SubCheckResult(name="b", severity="warn", summary=""),
    )
    verdict, _ = _aggregate(checks)
    assert verdict == "soft_fail"


def test_aggregate_error_is_soft_fail_not_hard() -> None:
    checks = (
        SubCheckResult(name="a", severity="info", summary=""),
        SubCheckResult(name="b", severity="error", summary=""),
    )
    verdict, infra = _aggregate(checks)
    assert verdict == "soft_fail"
    assert infra == ("b",)


def test_aggregate_fail_is_hard_fail() -> None:
    checks = (
        SubCheckResult(name="a", severity="warn", summary=""),
        SubCheckResult(name="b", severity="fail", summary=""),
    )
    verdict, _ = _aggregate(checks)
    assert verdict == "hard_fail"


def test_aggregate_skipped_never_affects_verdict() -> None:
    checks = (
        SubCheckResult(name="a", severity="info", summary=""),
        SubCheckResult(name="b", severity="skipped", summary=""),
    )
    verdict, _ = _aggregate(checks)
    assert verdict == "pass"


def test_redact_strips_sensitive_fields() -> None:
    payload: dict[str, Any] = {
        "ok_field": "visible",
        "api_key": "sk-fake",
        "nested": {
            "password": "nope",
            "token": "also-nope",
            "safe": "visible",
        },
    }
    redacted = _redact(payload)
    assert redacted["ok_field"] == "visible"
    assert redacted["api_key"] == "<REDACTED>"
    assert redacted["nested"]["password"] == "<REDACTED>"
    assert redacted["nested"]["token"] == "<REDACTED>"
    assert redacted["nested"]["safe"] == "visible"
    # Serialized output must not leak the substring.
    import json
    assert "sk-fake" not in json.dumps(redacted)


def test_redact_is_idempotent() -> None:
    payload = {"token": "secret", "ok": "visible"}
    once = _redact(payload)
    twice = _redact(once)
    assert once == twice


def test_run_pass_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Runner returns a pass verdict when all sub-checks are info."""
    monkeypatch.setattr(
        verification_loop_runner,
        "_reconciliation_check",
        lambda: SubCheckResult(
            name="reconciliation", severity="info", summary="clean"
        ),
    )
    monkeypatch.setattr(
        verification_loop_runner,
        "_stocktake_check",
        lambda _k: SubCheckResult(
            name="skill_stocktake", severity="info", summary="clean"
        ),
    )
    monkeypatch.setattr(
        verification_loop_runner,
        "_changed_surface_check",
        lambda _r: SubCheckResult(
            name="changed_surface", severity="info", summary="clean"
        ),
    )
    monkeypatch.setattr(
        verification_loop_runner,
        "_stale_doc_check",
        lambda: SubCheckResult(
            name="stale_doc", severity="info", summary="clean"
        ),
    )
    report = run(since_ref="main")
    assert report.verdict == "pass"
    assert len(report.sub_checks) == 4
    assert report.infra_errors == ()


def test_run_hard_fail_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        verification_loop_runner,
        "_reconciliation_check",
        lambda: SubCheckResult(
            name="reconciliation", severity="info", summary="clean"
        ),
    )
    monkeypatch.setattr(
        verification_loop_runner,
        "_stocktake_check",
        lambda _k: SubCheckResult(
            name="skill_stocktake", severity="info", summary="clean"
        ),
    )
    monkeypatch.setattr(
        verification_loop_runner,
        "_changed_surface_check",
        lambda _r: SubCheckResult(
            name="changed_surface",
            severity="fail",
            summary="missing tests",
            detail={"logic_files": ["packages/x.py"]},
        ),
    )
    monkeypatch.setattr(
        verification_loop_runner,
        "_stale_doc_check",
        lambda: SubCheckResult(
            name="stale_doc", severity="info", summary="clean"
        ),
    )
    report = run(since_ref="main")
    assert report.verdict == "hard_fail"


def test_run_error_maps_to_soft_not_hard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def crasher() -> SubCheckResult:
        raise RuntimeError("simulated platform bug")

    monkeypatch.setattr(
        verification_loop_runner, "_reconciliation_check", crasher
    )
    monkeypatch.setattr(
        verification_loop_runner,
        "_stocktake_check",
        lambda _k: SubCheckResult(
            name="skill_stocktake", severity="info", summary="clean"
        ),
    )
    monkeypatch.setattr(
        verification_loop_runner,
        "_changed_surface_check",
        lambda _r: SubCheckResult(
            name="changed_surface", severity="info", summary="clean"
        ),
    )
    monkeypatch.setattr(
        verification_loop_runner,
        "_stale_doc_check",
        lambda: SubCheckResult(
            name="stale_doc", severity="info", summary="clean"
        ),
    )
    report = run()
    assert report.verdict == "soft_fail"
    assert "reconciliation" in report.infra_errors


def test_policy_wrapper_raises_on_hard_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from packages.tools.primitives.verification_loop_runner import (
        VerificationLoopReport,
    )

    def fake_run(**_: Any) -> VerificationLoopReport:
        return VerificationLoopReport(
            schema_version="1",
            verdict="hard_fail",
            sub_checks=(
                SubCheckResult(
                    name="changed_surface",
                    severity="fail",
                    summary="missing tests",
                ),
            ),
            infra_errors=(),
            since_ref="main",
            lookback_task_runs=20,
        )

    from packages.policies import verification_loop as pol

    monkeypatch.setattr(pol, "_run", fake_run)
    with pytest.raises(PolicyViolation) as exc:
        run_verification_loop(since_ref="main")
    assert exc.value.code == "verification_loop_hard_fail"


def test_policy_wrapper_returns_on_soft_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from packages.tools.primitives.verification_loop_runner import (
        VerificationLoopReport,
    )

    def fake_run(**_: Any) -> VerificationLoopReport:
        return VerificationLoopReport(
            schema_version="1",
            verdict="soft_fail",
            sub_checks=(
                SubCheckResult(
                    name="skill_stocktake",
                    severity="warn",
                    summary="drift",
                ),
            ),
            infra_errors=(),
            since_ref="main",
            lookback_task_runs=20,
        )

    from packages.policies import verification_loop as pol

    monkeypatch.setattr(pol, "_run", fake_run)
    report = run_verification_loop(since_ref="main")
    assert report.verdict == "soft_fail"


def test_stale_doc_check_clean_exit_is_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """check_doc_paths.sh exit 0 → stale_doc sub-check is `info`."""
    monkeypatch.setattr(
        verification_loop_runner,
        "_run_doc_path_script",
        lambda: (0, "check_doc_paths: OK — all references resolve."),
    )
    result = _stale_doc_check()
    assert result.name == "stale_doc"
    assert result.severity == "info"
    assert result.detail["exit_code"] == 0


def test_stale_doc_check_broken_paths_is_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """check_doc_paths.sh exit 1 (broken refs) → stale_doc is `fail`."""
    monkeypatch.setattr(
        verification_loop_runner,
        "_run_doc_path_script",
        lambda: (1, "README.md -> missing/path.md"),
    )
    result = _stale_doc_check()
    assert result.name == "stale_doc"
    assert result.severity == "fail"
    assert result.detail["exit_code"] == 1


def test_stale_doc_check_unexpected_exit_is_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exit code the script never documents → `error` (platform bug)."""
    monkeypatch.setattr(
        verification_loop_runner,
        "_run_doc_path_script",
        lambda: (127, "bash: check_doc_paths.sh: not found"),
    )
    result = _stale_doc_check()
    assert result.name == "stale_doc"
    assert result.severity == "error"
    assert result.detail["exit_code"] == 127


def _info(name: str):
    return lambda *a, **k: SubCheckResult(
        name=name, severity="info", summary="clean"
    )


def test_run_composes_stale_doc_subcheck(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run() composes stale_doc as the 4th structural sub-check."""
    monkeypatch.setattr(
        verification_loop_runner, "_reconciliation_check", _info("reconciliation")
    )
    monkeypatch.setattr(
        verification_loop_runner, "_stocktake_check", _info("skill_stocktake")
    )
    monkeypatch.setattr(
        verification_loop_runner, "_changed_surface_check", _info("changed_surface")
    )
    monkeypatch.setattr(
        verification_loop_runner, "_stale_doc_check", _info("stale_doc")
    )
    report = run(since_ref="main")
    assert [sc.name for sc in report.sub_checks] == [
        "reconciliation",
        "skill_stocktake",
        "changed_surface",
        "stale_doc",
    ]
    assert report.verdict == "pass"


def test_run_stale_doc_fail_drives_hard_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale_doc `fail` (broken doc paths) hard-fails the verdict
    while the other three sub-checks are clean."""
    monkeypatch.setattr(
        verification_loop_runner, "_reconciliation_check", _info("reconciliation")
    )
    monkeypatch.setattr(
        verification_loop_runner, "_stocktake_check", _info("skill_stocktake")
    )
    monkeypatch.setattr(
        verification_loop_runner, "_changed_surface_check", _info("changed_surface")
    )
    monkeypatch.setattr(
        verification_loop_runner,
        "_stale_doc_check",
        lambda: SubCheckResult(
            name="stale_doc", severity="fail", summary="broken doc paths"
        ),
    )
    report = run(since_ref="main")
    assert report.verdict == "hard_fail"
